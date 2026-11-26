"""业务层：上传、截取、拉片、换人、报价、开拍、后台查进度、打分、导出。界面和接口都只调这里。"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import shutil
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote as urlquote

from . import analyze, faceswap, gpt, media, paths, pricing, prompt, scoring, store
from .errors import ApiError, NetError
from .minimax import MiniMax, mm, read_key
from .mock import MockMiniMax

log = logging.getLogger("h3dt")
POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="h3dt")
# 下载、锁脸、打分放单独一条队列（一次只做一条，免得抢 CPU），后台查进度的线程不被锁脸卡住
FINISH_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="h3dt-finish")
_FINISHING: set = set()
_FIN_LOCK = threading.Lock()
_ANALYZING: set = set()      # 这个进程里正在拉片的作品；不在里面却标着「拉片中」= 上次程序被关掉了
ACTIVE = ("submitting", "queued", "running", "downloading")
MAX_UPLOAD = 500 * 1024 * 1024


class UserError(Exception):
    """给用户看的错误（中文）。"""

    def __init__(self, title: str, action: str = "", code: str = "user"):
        self.info = {"code": code, "title": title, "action": action, "retryable": False}
        super().__init__(title)


# ---------------- 客户端 ----------------
def is_mock(p: dict | None = None) -> bool:
    return bool(store.settings().get("mock") or not read_key() or (p and p.get("sample")))


def client(p: dict | None = None):
    return MockMiniMax() if is_mock(p) else MiniMax()


def client_for(p: dict, t: dict | None = None):
    """以拍次开拍时定下的模拟/真拍为准（中途切换设置不能把模拟拍次变成真扣费）；老拍次没记就按现在的设置。"""
    if t is not None and "mock" in t:
        return MockMiniMax() if t["mock"] else MiniMax()
    return client(p)


def _photo_of(p: dict, t: dict | None, who: str) -> str:
    """这条拍次开拍时用的人物照片（之后换了照片，锁脸和打分也按当时那张）。"""
    rel = ((t or {}).get("photos") or {}).get(who)
    if rel and (store.pdir(p["id"]) / rel).exists():
        return rel
    return p["cast"][who]["photo"]


# ---------------- 展示 ----------------
def _url(pid: str, rel: str | None) -> str | None:
    if not rel:
        return None
    return f"/files/{pid}/" + urlquote(rel)


def spoken(lines: list[dict], dur: float | None = None) -> list[dict]:
    """要说出口的台词（去掉用户删掉的句子，可按时长截）。"""
    return [l for l in lines if l.get("new") != "" and (dur is None or l["start"] < dur - 0.3)]


def say(l: dict) -> str:
    return l.get("new") or l["text"]


def limit_chars(line: dict, rate: float) -> int:
    orig = len(scoring.norm(line.get("text", "")))
    dur = max(0.3, line["end"] - line["start"])
    return max(orig, int(dur * rate * 1.1 + 0.5), 2)


def stage(p: dict) -> str:
    if not p.get("source"):
        return "upload"
    if not p.get("window"):
        return "select"
    if p["jobs"]["analyze"]["status"] in ("running", "error") or not p.get("analysis"):
        return "analyzing"
    if not p.get("cast"):
        return "cast"
    takes = p.get("takes") or []
    if any(t["status"] in ACTIVE for t in takes):
        return "shooting"
    if any(not e.get("raw") for e in p.get("exports") or []):      # 只导出过换脸前原版不算「已导出」
        return "exported"
    if any(t["status"] == "succeeded" for t in takes):
        return "pick"
    return "ready"


def view(p: dict) -> dict:
    v = copy.deepcopy(p)
    pid = p["id"]
    for k in ("uploads", "nonces"):
        v.pop(k, None)
    if v.get("source"):
        v["source"]["file"] = _url(pid, v["source"]["file"])
    if v.get("window"):
        v["window"]["file"] = _url(pid, v["window"]["file"])
    a = v.get("analysis")
    warnings = []
    if a:
        for s in a.get("shots", []):
            s["thumb"] = _url(pid, s.get("thumb"))
            if s.get("hard"):
                warnings.append({"kind": "hard_shot", "text": f"第 {s['i']} 镜（{'、'.join(s['hard'])}）不好照抄，建议多拍一条挑"})
        a["strip"] = _url(pid, a.get("strip"))
        for l in a.get("lines", []):
            l["limit_chars"] = limit_chars(l, a.get("rate", 4.0))
        for k in ("action_en",):
            for s in a.get("shots", []):
                s.pop(k, None)
        if a.get("watermark"):
            warnings.append({"kind": "watermark", "text": "原片有水印或角标，新片可能把它也学过去"})
    for who, c in (v.get("cast") or {}).items():
        c["photo"] = _url(pid, c.get("photo"))
        for g in c.get("angles") or []:
            g["photo"] = _url(pid, g.get("photo"))
    if v.get("scene"):
        v["scene"]["photo"] = _url(pid, v["scene"].get("photo"))
    for t in v.get("takes", []):
        t["file"] = _url(pid, t.get("file"))
        t.pop("heard", None)
        t.pop("prompt", None)
        t.pop("analysis", None)
        t.pop("content_names", None)
        t.pop("photos", None)
        t["file_raw"] = _url(pid, t.get("file_raw"))           # 锁脸前的 H3 原版（挑片页对比用）
        if t["status"] == "submitting":      # 内部中间态，对外按排队中显示（接口约定只有 6 种）
            t["status"] = "queued"
    for e in v.get("exports", []):
        e["mp4"] = _url(pid, e.get("mp4"))
        e["srt"] = _url(pid, e.get("srt"))
    v["stage"] = stage(p)
    v["mode"] = mode_of(p)
    v["mode_suggest"] = suggest_mode(p.get("analysis"))
    v["swap"] = swap_of(p)
    v["swap_suggest"] = suggest_swap(p)
    v["audio"] = audio_of(p)
    v["audio_suggest"] = suggest_audio(p)
    v["has_orig_audio"] = has_orig_audio(p)
    v["budget"] = float(store.settings()["budget"])
    if not (p.get("prompt") or {}).get("custom") and p.get("analysis") and p.get("cast"):
        try:
            v["prompt"] = {"custom": False, "text": build_prompt(p, p["window"]["dur"])}
        except Exception:  # noqa: BLE001
            pass
    v["spent"] = store.spent(p)
    v["reserved"] = store.reserved(p)
    v["warnings"] = warnings
    v["mock"] = is_mock(p)
    v.pop("ledger", None)
    v["ledger"] = [{k: e.get(k) for k in ("time", "what", "quote", "actual")} for e in p.get("ledger", [])]
    return v


def summary(pid: str) -> dict:
    p = store.load(pid)
    thumb = None
    if p.get("analysis") and p["analysis"].get("shots"):
        thumb = _url(pid, p["analysis"]["shots"][0].get("thumb"))
    return {"id": pid, "name": p["name"], "created": p["created"], "thumb": thumb, "status": stage(p),
            "spent": store.spent(p), "sample": p.get("sample", False)}


# ---------------- 上传和截取 ----------------
def create_from_upload(filename: str, data_iter, name: str | None = None) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv"):
        raise UserError("这个文件不是视频", "请选 MP4 或 MOV 格式的视频。")
    p = store.create(name or Path(filename).stem[:30] or "未命名")
    pid = p["id"]
    dest = store.pdir(pid) / "原片" / f"source{ext}"
    size = 0
    with open(dest, "wb") as f:
        for chunk in data_iter:
            size += len(chunk)
            if size > MAX_UPLOAD:
                f.close()
                shutil.rmtree(store.pdir(pid), ignore_errors=True)
                raise UserError("视频太大（超过 500MB）", "先用剪映等工具截出要复刻的那一段再传。")
            f.write(chunk)
    try:
        info = media.probe(dest)
    except Exception:
        shutil.rmtree(store.pdir(pid), ignore_errors=True)
        raise UserError("读不出这个视频", "文件可能损坏或格式特殊，换一个导出的 MP4 试试。")
    if info["duration"] < 4:
        shutil.rmtree(store.pdir(pid), ignore_errors=True)
        raise UserError("原片太短", "至少要 4 秒。")
    r = info["width"] / max(1, info["height"])
    if not 0.4 <= r <= 2.5:
        shutil.rmtree(store.pdir(pid), ignore_errors=True)
        raise UserError("画面比例太特殊", "宽高比要在 0.4~2.5 之间（常见的竖屏、横屏、方形都可以）。")

    def fn(p):
        p["source"] = {"file": f"原片/source{ext}", **{k: info[k] for k in ("duration", "width", "height", "fps", "has_audio")}}
    p = store.update(pid, fn)
    if info["duration"] <= 15.5:
        set_window(pid, 0.0, min(15, int(info["duration"])))
    return store.load(pid)


def _no_active(p: dict) -> None:
    if any(t["status"] in ACTIVE for t in p.get("takes", [])):
        raise UserError("还有片子在拍或在处理", "等这几条拍完、存好，再改原片或重新拉片。")


def delete_project(pid: str) -> None:
    """在拍的作品不让删：删了就没人接着查进度、下载，云端照样扣费。"""
    p = store.load(pid)
    if any(t["status"] in ACTIVE for t in p.get("takes", [])):
        raise UserError("这个作品还有片子在拍或在处理",
                        "等拍完、存好再删。删掉不会取消 MiniMax 那边的任务，钱照样会扣，片子却没人接着下载。")
    store.trash(pid)


def set_window(pid: str, start: float, dur: int) -> dict:
    p = store.load(pid)
    _no_active(p)
    src = store.pdir(pid) / p["source"]["file"]
    total = p["source"]["duration"]
    dur = int(max(4, min(15, dur, int(total))))
    start = float(max(0.0, min(start, total - dur)))
    out = store.pdir(pid) / "原片" / "片段.mp4"
    media.trim(src, out, start, dur, keep_audio=True)
    # 同样长度换一段时，参考视频、原声、原片人物截图都要重做，不能接着用上一段的
    d = store.pdir(pid)
    shutil.rmtree(d / "参考", ignore_errors=True)
    for x in (d / "素材").glob("原片人物*.jpg"):
        x.unlink(missing_ok=True)

    def fn(p):
        p["uploads"] = {}
        p["window"] = {"start": round(start, 2), "dur": dur, "file": "原片/片段.mp4"}
        p["analysis"] = None
        p["prompt"] = {"custom": False, "text": ""}
        p["jobs"]["analyze"] = {"status": "idle", "step": "", "progress": 0, "error": None}
    p = store.update(pid, fn)
    if store.settings().get("auto_analyze", True):
        start_analyze(pid)
    return store.load(pid)


# ---------------- 拉片 ----------------
def start_analyze(pid: str) -> None:
    p = store.load(pid)
    _no_active(p)
    if not p.get("window"):
        raise UserError("还没选好要复刻的那一段")
    with _FIN_LOCK:
        if pid in _ANALYZING:
            return
        _ANALYZING.add(pid)

    def mark(status, step="", prog=0.0, err=None):
        def fn(p):
            p["jobs"]["analyze"] = {"status": status, "step": step, "progress": round(prog, 2), "error": err}
        store.update(pid, fn)

    mark("running", "准备", 0.02)

    def job():
        try:
            d = store.pdir(pid)
            c = client(p)
            g = gpt.GPT() if not is_mock(p) and store.settings()["vision"] == "gpt" and gpt.read_key() else None
            a = analyze.run(c, d / p["window"]["file"], d, d, on_step=lambda s, pr: mark("running", s, pr), gpt=g)

            def fn(p):
                p["analysis"] = a
                if a.get("cost"):
                    store.ledger_add(p, {"what": "拉片（识别台词 + AI 看片）", "quote": a["cost"], "actual": a["cost"]})
                u = a.get("gpt_usage")
                if u:   # GPT 用的是用户自己的 OpenAI 额度，不算进 MiniMax 花费，但用量要记下来
                    store.ledger_add(p, {"what": f"拉片 GPT 看片（{a.get('vision_by')}，{u.get('prompt_tokens', 0)} 入 / "
                                                 f"{u.get('completion_tokens', 0)} 出 tokens，走你的 OpenAI 额度）", "actual": 0})
            store.update(pid, fn)
            mark("done", "完成", 1.0)
        except ApiError as e:
            mark("error", "", 0, e.to_dict())
        except Exception as e:  # noqa: BLE001
            log.error("analyze failed: %s", traceback.format_exc())
            mark("error", "", 0, {"code": "local", "title": "拉片出错了", "action": f"再点一次「重新拉片」；还不行把「日志」文件夹发给作者。（{str(e)[:80]}）", "retryable": True})
        finally:
            with _FIN_LOCK:
                _ANALYZING.discard(pid)
    try:
        POOL.submit(job)
    except Exception:
        with _FIN_LOCK:
            _ANALYZING.discard(pid)
        raise


def edit_analysis(pid: str, patch: dict) -> dict:
    def fn(p):
        a = p.get("analysis")
        if not a:
            raise UserError("还没拉片")
        shots = {s["i"]: s for s in a["shots"]}
        for e in patch.get("shots") or []:
            s = shots.get(e.get("i"))
            if not s:
                continue
            for k in ("size", "action"):
                if k in e and e[k] != s.get(k):
                    s[k] = e[k]
                    s["edited"] = True
            if "camera" in e:
                s["camera"] = {**s["camera"], **e["camera"]}
                s["edited"] = True
            if "who" in e:
                s["who"] = e["who"]
        lines = {l["i"]: l for l in a["lines"]}
        for e in patch.get("lines") or []:
            l = lines.get(e.get("i"))
            if l is not None and "new" in e:
                # None = 照搬原台词；"" = 这句不说；其他 = 新台词
                if e["new"] is None:
                    l["new"] = None
                else:
                    txt = str(e["new"]).strip()
                    l["new"] = None if txt == l["text"] else txt
            if l is not None and "who" in e:
                l["who"] = e["who"]
        people = {x["id"]: x for x in a.get("people", [])}
        for e in patch.get("people") or []:
            if e.get("id") in people and "desc" in e:
                people[e["id"]]["desc"] = e["desc"]
                people[e["id"]]["edited"] = True
    return store.update(pid, fn)


# ---------------- 换人 ----------------
def _save_photo(pid: str, name: str, filename: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        raise UserError("这个文件不是图片", "请选 JPG 或 PNG 照片。")
    if len(data) > 30 * 1024 * 1024:
        raise UserError("照片太大（超过 30MB）", "换一张小一点的。")
    d = store.pdir(pid) / "素材"
    d.mkdir(parents=True, exist_ok=True)
    raw = d / f"_{name}{ext}"
    raw.write_bytes(data)
    out = d / f"{name}.jpg"
    try:
        media.ff("-i", str(raw), "-vf", "scale='min(2048,iw)':'min(2048,ih)':force_original_aspect_ratio=decrease",
                 "-q:v", "2", str(out))
        info = media.probe(out)
    except Exception:
        raise UserError("读不出这张照片", "换一张 JPG 或 PNG 试试。")
    finally:
        raw.unlink(missing_ok=True)
    w, h = info["width"], info["height"]
    if min(w, h) < 256:
        raise UserError("照片太小", "至少 256 像素，最好用清晰的正脸照。")
    if not 0.4 <= w / h <= 2.5:
        raise UserError("照片比例太特殊", "用普通的竖图或方图。")
    return f"素材/{name}.jpg"


def set_cast(pid: str, person: str, filename: str, data: bytes) -> dict:
    if not re.fullmatch(r"[A-Z]", person or ""):
        raise UserError("人物编号不对")
    _no_active(store.load(pid))           # 拍摄中换照片，AI 和锁脸会用成两个人
    rel = _save_photo(pid, f"人物{person}", filename, data)
    full = False
    warn: list[str] = []
    try:
        from . import faces
        f = store.pdir(pid) / rel
        info = media.probe(f)
        fr = faces._frame(f, info["width"], info["height"])
        found = faces.detect(fr) if fr is not None else []
        if not found:
            warn.append("照片里没认出人脸：换一张正脸清楚的，不然换人和锁脸都会失败")
        elif len(found) > 1:
            warn.append(f"照片里有 {len(found)} 张脸：最好只有你一个人，不然 AI 可能换成别人")
        if found and float(max(r[2] for r in found)) < 80:      # 实测脸宽 114 像素的全身照锁脸后像 0.81，80 以下才提示
            warn.append("照片里的脸太小：全身照也尽量拍近一点，或者再放一张大头照，不然像不像会差")
        if found:
            fh = max(r[3] for r in found)
            # 脸占画面高度不到 1/5 → 拍到了身子和衣服，算全身照。必须转成 Python bool：
            # fh 是 numpy 数，比较结果是 numpy.bool，存 project.json 会报 not JSON serializable（11-23 验收抓到）
            full = bool(float(fh) / info["height"] < 0.2)
    except Exception:  # noqa: BLE001
        log.error("full body check: %s", traceback.format_exc())

    def fn(p):
        p.setdefault("cast", {})[person] = {"photo": rel, "t": time.time(), "full_body": full, "warn": warn}
        p.setdefault("uploads", {}).pop(rel, None)
    return store.update(pid, fn)


def del_cast(pid: str, person: str) -> dict:
    _no_active(store.load(pid))
    return store.update(pid, lambda p: p.get("cast", {}).pop(person, None))


# ---------------- 角度照（11-24）----------------
# 动作照抄时 H3 会让换上的人转回来看镜头（侧脸.mp4 原片 20/40 帧侧脸 → 成片 0/45）。人物卡再放几张侧脸/转头照，
# 实测头会跟着原片转（半侧帧 9/45 → 26/45，开头也不再慢 1 秒）。照着拍不用：11-23 带角度照反而更不像（0.60 → 0.55）。
MAX_ANGLES = 3
SIDE_YAW = 0.3        # 转头超过它算侧脸照，自动镜像出另一边（脸基本左右对称；实测镜像的侧脸照能用）


def angle_photos(p: dict, who: str) -> list[str]:
    return [x["photo"] for x in (((p.get("cast") or {}).get(who) or {}).get("angles") or [])]


def _angle_pics(p: dict, mode: str | None = None) -> dict:
    """动作照抄时每个人的角度照图号：接在人物照、场景图后面（前面的编号都不变）。返回 {人物: [图号…]}。"""
    if (mode or mode_of(p)) != "video":
        return {}
    n = len(p.get("cast") or {}) + (1 if p.get("scene") else 0)
    out = {}
    for k in sorted(p.get("cast") or {}):
        nums = []
        for _ in angle_photos(p, k):
            n += 1
            nums.append(n)
        if nums:
            out[k] = nums
    return out


def add_angle(pid: str, person: str, filename: str, data: bytes) -> dict:
    p = store.load(pid)
    _no_active(p)
    c = (p.get("cast") or {}).get(person)
    if not c:
        raise UserError("先放这个人的主照片", "角度照是补充：先放一张正脸清楚的主照片，再加侧脸或转头的。")
    have = c.get("angles") or []
    if len(have) >= MAX_ANGLES:
        raise UserError(f"角度照最多 {MAX_ANGLES} 张", "先删掉一张再加。")
    k = 1
    while any(f"人物{person}_角度{k}" in x["photo"] for x in have):
        k += 1
    rel = _save_photo(pid, f"人物{person}_角度{k}", filename, data)
    d = store.pdir(pid)
    yaw, sim, warn = None, None, []
    try:
        from . import faces
        info = media.probe(d / rel)
        fr = faces._frame(d / rel, info["width"], info["height"])
        found = faces.detect(fr) if fr is not None else []
        if not found:
            warn.append("这张没认出人脸：换一张脸清楚的侧脸或转头照")
        else:
            f = max(found, key=lambda r: r[2] * r[3])
            yaw = round(faces._yaw(f), 2)
            ref = faces.photo_embedding(d / c["photo"])
            if ref is not None:
                sim = round(faces.similar(faces.embed(fr, f), ref), 2)
            # 侧脸时人脸识别本来就打分低（实测 GPT 生成的好侧脸照只有 0.39），只在接近正脸时提示不像
            if sim is not None and yaw < SIDE_YAW and sim < faces.SAME:
                warn.append("这张和主照片不太像，可能会把脸带偏：换一张同一个人的")
    except Exception:  # noqa: BLE001
        log.error("angle check: %s", traceback.format_exc())
    items = [{"photo": rel, "yaw": yaw, "sim": sim, "warn": warn}]
    if yaw is not None and yaw >= SIDE_YAW and len(have) + 1 < MAX_ANGLES:
        mrel = f"素材/人物{person}_角度{k}_镜像.jpg"
        try:
            media.ff("-i", str(d / rel), "-vf", "hflip", "-q:v", "2", str(d / mrel))
            items.append({"photo": mrel, "yaw": yaw, "sim": sim, "warn": [], "mirror_of": rel})
        except Exception:  # noqa: BLE001
            log.error("angle mirror: %s", traceback.format_exc())

    def fn(p):
        p["cast"][person].setdefault("angles", []).extend(items)
        for x in items:
            p.setdefault("uploads", {}).pop(x["photo"], None)
    return store.update(pid, fn)


def del_angle(pid: str, person: str, i: int) -> dict:
    p = store.load(pid)
    _no_active(p)
    have = ((p.get("cast") or {}).get(person) or {}).get("angles") or []
    if not 0 <= i < len(have):
        raise UserError("没有这张角度照")
    gone = have[i]["photo"]

    def fn(p):
        # 删原图时把它镜像出来的那张一起删；只删镜像就只删镜像
        p["cast"][person]["angles"] = [x for x in p["cast"][person].get("angles") or []
                                       if x["photo"] != gone and x.get("mirror_of") != gone]
    return store.update(pid, fn)


def set_scene(pid: str, filename: str, data: bytes) -> dict:
    _no_active(store.load(pid))
    rel = _save_photo(pid, "场景", filename, data)

    def fn(p):
        p["scene"] = {"photo": rel}
        p.setdefault("uploads", {}).pop(rel, None)
    return store.update(pid, fn)


def del_scene(pid: str) -> dict:
    _no_active(store.load(pid))
    return store.update(pid, lambda p: p.update({"scene": None}))


# ---------------- 拍法 ----------------
def suggest_mode(a: dict | None) -> dict:
    """11-22 实测：带参考视频时原片里脸清楚就换不掉人 → 有对白或有近景/特写时默认「照着拍」（不传原视频）；
    全是全景/远景、没对白（跳舞、动作）默认「动作照抄」。"""
    if not a:
        return {"mode": "text", "why": "默认照着拍：换人最稳，价钱减半"}
    close = any(s.get("size") in ("近景", "特写") for s in a.get("shots", []))
    if a.get("lines") or close:
        return {"mode": "text", "why": "原片有对白或近景，照着拍换人更稳，价钱也减半"}
    return {"mode": "video", "why": "原片是全身动作、没有对白，动作照抄能把动作和构图学得一模一样"}


def mode_of(p: dict) -> str:
    return p.get("mode") or suggest_mode(p.get("analysis"))["mode"]


def suggest_swap(p: dict) -> dict:
    """换整个人（脸、发型、身材、衣服都跟照片）还是只换脸和发型（衣服跟原片）：按照片是不是全身照推荐。"""
    a = (p.get("cast") or {}).get(main_of(p) or "A") or {}
    if a.get("full_body"):
        return {"swap": "full", "why": "你的照片拍到了全身，衣服和身材也一起换成照片里的"}
    return {"swap": "head", "why": "你的照片是大头照，看不到衣服，衣服先沿用原片的"}


def swap_of(p: dict) -> str:
    return p.get("swap") or suggest_swap(p)["swap"]


def set_swap(pid: str, swap: str) -> dict:
    if swap not in ("full", "head"):
        raise UserError("换人方式不对")
    return store.update(pid, lambda p: p.update({"swap": swap}))


def set_mode(pid: str, mode: str) -> dict:
    if mode not in ("text", "video"):
        raise UserError("拍法不对")
    return store.update(pid, lambda p: p.update({"mode": mode}))


# ---------------- 声音 ----------------
# orig = 用原片原声：原声当参考音频交给 H3 对口型，拍完把原声原样贴回成片；台词不能改。
# new  = H3 重新配：新的人用新的声音说（能改台词）。台词一句没改默认 orig，一改就自动 new。
def has_orig_audio(p: dict) -> bool:
    return bool((p.get("source") or {}).get("has_audio"))


def lines_edited(p: dict) -> bool:
    a = p.get("analysis") or {}
    return any(l.get("new") is not None and scoring.norm(l["new"]) != scoring.norm(l["text"]) for l in a.get("lines", []))


def suggest_audio(p: dict) -> dict:
    if not has_orig_audio(p):
        return {"audio": "new", "why": "原片没有声音，由 H3 配声音"}
    if lines_edited(p):
        return {"audio": "new", "why": "你改了台词，新台词只能由 H3 让新的人重新说"}
    return {"audio": "orig", "why": "台词没改，直接用原片原声：人声、背景音乐、节奏都和原片一样"}


def audio_of(p: dict) -> str:
    a = p.get("audio")
    if a == "orig" and (not has_orig_audio(p) or lines_edited(p)):
        return "new"
    return a or suggest_audio(p)["audio"]


def set_audio(pid: str, audio: str) -> dict:
    if audio not in ("orig", "new"):
        raise UserError("声音选项不对")
    p = store.load(pid)
    if audio == "orig":
        if not has_orig_audio(p):
            raise UserError("原片没有声音", "这条只能由 H3 配声音。")
        if lines_edited(p):
            raise UserError("台词改过了，用不了原声", "要用原声，先把改过的台词恢复成原句。")
    return store.update(pid, lambda p: p.update({"audio": audio}))


def _audio_ref(p: dict, dur: int) -> Path:
    out = store.pdir(p["id"]) / "参考" / f"原声_{dur}s.wav"
    if not out.exists():
        media.audio_ref(store.pdir(p["id"]) / p["window"]["file"], out, dur)
    return out


# ---------------- 报价 ----------------
def _cast_map(p: dict) -> dict:
    return {k: i + 1 for i, k in enumerate(sorted(p.get("cast") or {}))}


def keep_refs(p: dict) -> dict:
    """「照着拍」时不换的人：从原片截他的脸当参考图（素材/原片人物X.jpg），返回 {人物: 相对路径}。"""
    if mode_of(p) != "text" or not p.get("analysis"):
        return {}
    a = p["analysis"]
    d = store.pdir(p["id"])
    out = {}
    for x in a.get("people", []):
        pid = x["id"]
        if pid in (p.get("cast") or {}) or not any(pid in (s.get("who") or []) for s in a["shots"]):
            continue
        rel = f"素材/原片人物{pid}.jpg"
        f = d / rel
        if not f.exists():
            try:
                from . import faces
                if not faces.crop_person(d / p["window"]["file"], a["shots"], pid, f):
                    continue
            except Exception:  # noqa: BLE001
                log.error("crop person: %s", traceback.format_exc())
                continue
        out[pid] = rel
    return out


def _pic_numbers(p: dict) -> tuple[dict, dict]:
    """参考图顺序：换上的人物照（按 A、B…）→ 场景图 → 不换的人的截图。返回 (cast 编号, keep 编号)。"""
    cast = _cast_map(p)
    n = len(cast) + (1 if p.get("scene") else 0)
    keep = {}
    for pid in sorted(keep_refs(p)):
        n += 1
        keep[pid] = n
    return cast, keep


def build_prompt(p: dict, out_dur: int) -> str:
    if p.get("prompt", {}).get("custom") and p["prompt"].get("text"):
        return p["prompt"]["text"]
    s = store.settings()
    outfit = "photo" if swap_of(p) == "full" else "video"
    copy_audio = audio_of(p) == "orig"
    if mode_of(p) == "text":
        cast, keep = _pic_numbers(p)
        return prompt.build_novideo(p["analysis"], cast, out_dur, music=s.get("music", "auto"), keep_refs=keep,
                                    outfit_from=outfit, audio_copy=copy_audio)
    return prompt.build(p["analysis"], _cast_map(p), out_dur, scene_photo=bool(p.get("scene")),
                        music=s.get("music", "auto"), outfit_from=outfit, audio_copy=copy_audio,
                        angles=_angle_pics(p, "video"))


def trial_dur(p: dict) -> int:
    """先试前几秒：默认 5 秒；有一句台词跨过第 5 秒时延到那句说完（最多 8 秒），免得试拍时那句被删、原声和画面打架。"""
    n = 5
    for l in spoken(((p.get("analysis") or {}).get("lines")) or []):
        if l["start"] < 5 < l["end"]:
            n = max(n, min(8, int(l["end"] + 0.3 + 0.999)))
    return int(min(n, (p.get("window") or {}).get("dur", n)))


def quote(pid: str, tier: str, takes: int, trial: bool) -> dict:
    p = store.load(pid)
    if tier not in pricing.TIERS:
        tier = pricing.DEFAULT_TIER
    takes = int(max(1, min(4, takes)))
    blockers, notices = [], []
    a = p.get("analysis")
    if not p.get("window"):
        blockers.append({"kind": "no_window", "text": "先传原片"})
    if not a:
        blockers.append({"kind": "no_analysis", "text": "等拉片完成"})
    if not p.get("cast"):
        blockers.append({"kind": "no_cast", "text": "先放一张你的人物照片"})
    dur = trial_dur(p) if trial else (p["window"]["dur"] if p.get("window") else 5)
    if a:
        rate = a.get("rate", 4.0)
        for l in spoken(a["lines"]):
            if trial and l["start"] >= dur:
                continue
            if l.get("new"):
                n, lim = len(scoring.norm(l["new"])), limit_chars(l, rate)
                if n > lim:
                    blockers.append({"kind": "line_too_long", "i": l["i"],
                                     "text": f"第 {l['i']} 句台词多了 {n - lim} 个字（这句只有 {l['end'] - l['start']:.1f} 秒）"})
        sub = a.get("subtitle") or {}
        if sub.get("has") and mode_of(p) == "video":
            notices.append("原片带字幕：动作照抄时新片偶尔会把字幕学去，介意的话换「照着拍」")
        if a.get("watermark_boxes") and mode_of(p) == "video":
            notices.append("原片的水印、账号名已自动抹掉再给 AI 参考，成片不会带")
        if mode_of(p) == "video":
            notices.append("动作照抄会把原演员的脸自动涂掉再给 AI 参考，这样才换得成人（本机处理，不花钱）")
        if audio_of(p) == "orig":
            notices.append("用原片原声：人声和背景音乐原样保留，人物照着原声对口型；原声给 AI 参考不收费")
        elif a.get("lyrics"):
            notices.append("原片背景音乐里的歌词当作配乐处理，人物不会开口唱")
        if mode_of(p) == "video" and (spoken(a["lines"]) or any(s.get("size") in ("近景", "特写") for s in a["shots"])):
            # 11-23 实测（香水口播）：动作照抄把说话的脸画变形、不像照片，H3 还自己重念台词，嘴型比原声慢约 0.4 秒
            notices.append("原片有人说话或有近景：动作照抄容易把脸画变形、不像你的照片，嘴型也可能对不上；这类片子用「照着拍」更好")
        if any(s.get("hard") for s in a["shots"]):
            notices.append("有快切或复杂镜头，这类镜头不一定照抄得准，可以多拍一条挑")
    mode = mode_of(p)
    images = len(p.get("cast") or {}) + (1 if p.get("scene") else 0) + (len(keep_refs(p)) if mode == "text" else 0)
    images += sum(len(v) for v in _angle_pics(p, mode).values())
    q = pricing.takes_quote(tier, dur, dur if mode == "video" else 0, images, takes)
    q["mode"] = mode
    q["audio"] = audio_of(p)
    # 锁脸：拍完在本机再换一遍脸（不花钱）；没有 N 卡时走 CPU，先说清要多等多久
    q["face_lock"] = bool(store.settings().get("face_lock", True) and faceswap.available() and not p.get("sample"))
    if q["face_lock"] and a:
        if faceswap.has_nvidia():
            notices.append("拍完自动锁脸：用 N 卡把脸再换一遍，更像你的照片，约多等 1 分钟（本机处理，不花钱）")
        else:
            mins = max(1, round(faceswap.estimate_seconds(dur) / 60))
            notices.append(f"拍完自动锁脸：这台电脑没有 N 卡，用 CPU 处理，每条约多等 {mins} 分钟（不花钱）；"
                           "不想等可以在设置里关掉「锁脸」")
    mock = is_mock(p)
    budget = float(store.settings()["budget"])   # 预算跟设置走（每个作品的上限）
    used = store.spent(p) + store.reserved(p)
    q.update({"mock": mock, "trial": trial, "budget": budget, "budget_left": round(budget - used, 2),
              "over_budget": (not mock) and used + q["sum"] > budget + 1e-6,
              "blockers": blockers, "notices": notices})
    if q["over_budget"]:
        blockers.append({"kind": "over_budget", "text": f"超出这个作品的预算（剩 ¥{max(0, budget - used):.2f}），到设置里调高预算再拍"})
    try:
        q["prompt"] = build_prompt(p, dur) if a and p.get("cast") else ""
    except Exception as e:  # noqa: BLE001
        q["prompt"] = ""
        log.error("prompt build: %s", e)
    return q


def set_prompt(pid: str, text: str | None, reset: bool = False) -> dict:
    def fn(p):
        if reset:
            p["prompt"] = {"custom": False, "text": ""}
        else:
            p["prompt"] = {"custom": True, "text": text or ""}
    return store.update(pid, fn)


# ---------------- 失败原因----------------
_ASSET = {"image_url": "图片", "video_url": "视频", "audio_url": "声音"}


def _fail_info(code: str | None, raw: str, names: list | None, stage: str) -> dict:
    """MiniMax 报错 → 给用户看的标题、怎么办；原文进日志和小字。stage = create（提交就被拒，不扣费）/ run（中途失败）。"""
    log.error("minimax %s failed: code=%s raw=%s", stage, code, (raw or "")[:500])
    if code:
        info = ApiError(code, raw or "").to_dict()
    else:
        info = {"code": "none", "title": "MiniMax 没说明原因",
                "action": "可以先点「重拍这一条」再试一次；一直这样就换一下照片或原片。", "retryable": True}
    m = re.search(r"content\[(\d+)\]\.(image_url|video_url|audio_url)", raw or "")
    if m:
        i = int(m.group(1))
        what = (names[i] if names and i < len(names) else f"第 {i} 项素材（{_ASSET[m.group(2)]}）")
        info["title"] = f"{what}：MiniMax 没能处理"
        info["action"] = ("可能是平台临时出错，也可能被内容审核拦了：先点「重拍这一条」再试一次；"
                          "还不行就换一张（穿着普通、正脸清楚、画面里只有你一个人）。")
        info["retryable"] = True
    if stage == "run":
        a = re.sub(r"[；;]?\s*(这次)?没扣费。?", "", info["action"]).rstrip("。")
        info["action"] = a + "。中途失败一般不扣费，以 MiniMax 账单为准。"
    else:
        info["not_charged"] = True
        if "没扣费" not in info["action"]:
            info["action"] = info["action"].rstrip("。") + "。这次没扣费。"
    if raw:
        info["detail"] = raw[:300]
    return info


_RECON_LOCK = threading.Lock()
_CLAIMED: set = set()


def _known_tasks() -> set:
    out = set()
    for pid in store.all_ids():
        try:
            out |= {str(t["task_id"]) for t in store.load(pid).get("takes", []) if t.get("task_id")}
        except Exception:  # noqa: BLE001
            pass
    return out


def _reconcile(c, body: dict, t0: float) -> str | None:
    """提交时网络断了，任务可能已经提交、照常扣费。查一次任务列表（免费），找刚才这几十秒、参数相同的任务接上。"""
    time.sleep(5)
    try:
        items = (c.list_tasks(page_size=20) or {}).get("items") or []
    except Exception:  # noqa: BLE001
        return None
    with _RECON_LOCK:
        known = _known_tasks() | _CLAIMED
        cands = [x for x in items if str(x.get("id")) not in known and x.get("model") == body["model"]
                 and x.get("resolution") == body["resolution"] and int(x.get("duration") or 0) == int(body["duration"])
                 and x.get("ratio") == body["ratio"] and (x.get("created_at") or 0) >= t0 - 60]
        if len(cands) != 1:
            # 同规格的不止一条（或一条都没有）就不猜，让用户去平台核对，免得接错别人的任务
            if cands:
                log.error("reconcile: %d candidates, not guessing: %s", len(cands), [x.get("id") for x in cands])
            return None
        tid = str(cands[0]["id"])
        _CLAIMED.add(tid)
        return tid


def _snap_photos(p: dict, tid: str) -> dict:
    """开拍时把人物照片各存一份到拍次里。"""
    d = store.pdir(p["id"])
    out = {}
    for k, c in (p.get("cast") or {}).items():
        rel = f"拍次/{tid}_人物{k}.jpg"
        try:
            (d / "拍次").mkdir(parents=True, exist_ok=True)
            shutil.copy2(d / c["photo"], d / rel)
            out[k] = rel
        except OSError:
            log.error("snap photo: %s", traceback.format_exc())
    return out


# ---------------- 开拍 ----------------
def shoot(pid: str, tier: str, takes: int, trial: bool, confirm_total: float, nonce: str,
          expect_mock: bool | None = None) -> dict:
    q = quote(pid, tier, takes, trial)
    if q["blockers"]:
        raise UserError(q["blockers"][0]["text"], "改好再点开拍。")
    if expect_mock is not None and bool(expect_mock) != bool(q["mock"]):
        # 网页上看到的是模拟报价、设置却刚切成真拍（或反过来）→ 不能静默扣费
        raise UserError("模拟 / 真拍刚刚切换过", "请再看一眼价钱后确认。")
    if not q["mock"] and abs(q["sum"] - float(confirm_total or 0)) > 0.011:
        raise UserError("价钱变了", "报价刚刚更新过，请再看一眼价钱后确认。")
    prompt_text = q["prompt"]
    new_ids: list[str] = []

    def fn(p):
        if nonce in p.get("nonces", []):
            raise UserError("这次已经提交过了", "不用重复点。")
        p.setdefault("nonces", []).append(nonce)
        p["nonces"] = p["nonces"][-50:]
        base = len(p["takes"])
        for k in range(q["takes"]):
            tid = f"t{base + k + 1:02d}"
            new_ids.append(tid)
            p["takes"].append({"id": tid, "n": base + k + 1, "status": "submitting", "tier": q["tier"], "dur": q["out_sec"],
                               "trial": bool(trial), "quote": q["total"], "actual": None, "task_id": None,
                               "created": time.strftime("%H:%M:%S"), "ts": time.time(), "elapsed": 0,
                               "file": None, "error": None, "score": None, "prompt": prompt_text, "mode": q["mode"],
                               "audio": q["audio"], "analysis": copy.deepcopy(p.get("analysis")), "mock": bool(q["mock"]),
                               "photos": _snap_photos(p, tid)})
    store.update(pid, fn)
    POOL.submit(_submit, pid, new_ids)
    return store.load(pid)


def _reference(p: dict, dur: int) -> Path:
    d = store.pdir(p["id"])
    a = p["analysis"]
    # 只抹水印；字幕保持原样。11-22 实测：抹掉字幕留下的模糊带反而让 H3 在新片里烧上字幕（F1），原样保留时新片干净（F2）
    boxes = list(a.get("watermark_boxes") or [])
    import hashlib
    tag = hashlib.md5(json.dumps(boxes).encode()).hexdigest()[:6]
    cast = set((p.get("cast") or {}).keys())
    tag += "_" + "".join(sorted(cast))
    out = d / "参考" / f"ref_{dur}s_{tag}.mp4"
    if not out.exists():
        base = d / "参考" / f"_base_{dur}s_{tag}.mp4"
        part = out.with_name(out.stem + "_part.mp4")
        try:
            media.make_reference(d / p["window"]["file"], base, 0.0, dur, erase_boxes=boxes)
            from . import faces
            people = {x["id"] for x in a.get("people", [])}
            r = faces.mask_shots(base, part, a["shots"], cast, people - cast)
            log.info("face mask %s: %s", p["id"], r)
            if r.get("frames") and not r.get("masked"):
                # 一帧都没涂上：原演员的脸会原样交给 H3，换人几乎必失败、钱照扣。拦下，不上传
                raise UserError("原片里没认出要换的人的脸，没法先涂掉",
                                "这条片子用「动作照抄」换不了人：改用「照着拍」（不传原片画面），或换一条脸更清楚的原片。")
            # 写完整才换上：11-24 涂脸中途出错留下 0.08 秒的半截参考片，重拍时被直接拿去用，接口报「视频时长不对」
            os.replace(part, out)
        finally:
            base.unlink(missing_ok=True)
            part.unlink(missing_ok=True)
    return out


def _uploaded(c, p: dict, rel: str) -> str:
    """同一文件 6 天内不重复上传（官方 7 天过期）。"""
    up = p.setdefault("uploads", {})
    hit = up.get(rel)
    if hit and time.time() - hit["t"] < 6 * 86400 and hit.get("mock") == bool(getattr(c, "mock", False)):
        return hit["id"]
    fid = c.upload(store.pdir(p["id"]) / rel)
    up[rel] = {"id": fid, "t": time.time(), "mock": bool(getattr(c, "mock", False))}
    return fid


def _submit(pid: str, tids: list[str]) -> None:
    p = store.load(pid)
    c = client(p)
    stop_err = None
    try:
        first = next(t for t in p["takes"] if t["id"] == tids[0])
        c = client_for(p, first)
        dur = first["dur"]
        content = [{"type": "text", "text": first["prompt"]}]
        names = ["提示词"]            # 和 content 一一对应：MiniMax 报 content[N] 出错时说得出是哪张图
        for k in sorted(p.get("cast") or {}):
            fid = _uploaded(c, p, p["cast"][k]["photo"])
            content.append({"type": "image_url", "image_url": {"url": mm(fid)}, "role": "reference_image"})
            names.append(f"你放的人物{k}照片")
        if p.get("scene"):
            fid = _uploaded(c, p, p["scene"]["photo"])
            content.append({"type": "image_url", "image_url": {"url": mm(fid)}, "role": "reference_image"})
            names.append("场景图")
        if first.get("mode", "video") == "video":
            # 角度照：顺序和 _angle_pics 的图号一致（人物照 → 场景图 → 各人的角度照）
            for k in sorted(p.get("cast") or {}):
                for j, rel in enumerate(angle_photos(p, k), 1):
                    fid = _uploaded(c, p, rel)
                    content.append({"type": "image_url", "image_url": {"url": mm(fid)}, "role": "reference_image"})
                    names.append(f"人物{k}的第 {j} 张角度照")
        if first.get("mode") == "text":
            kr = keep_refs(p)
            for who in sorted(kr):        # 注意别用 pid 当循环变量：会覆盖作品编号（11-22 踩过）
                fid = _uploaded(c, p, kr[who])
                content.append({"type": "image_url", "image_url": {"url": mm(fid)}, "role": "reference_image"})
                names.append(f"原片里人物{who}的截图")
        if first.get("mode", "video") == "video":
            ref = _reference(p, dur)
            vid = _uploaded(c, p, ref.relative_to(store.pdir(pid)).as_posix())
            content.append({"type": "video_url", "video_url": {"url": mm(vid)}, "role": "reference_video"})
            names.append("原片（参考视频）")
        if first.get("audio") == "orig":
            wav = _audio_ref(p, dur)
            aid = _uploaded(c, p, wav.relative_to(store.pdir(pid)).as_posix())
            content.append({"type": "audio_url", "audio_url": {"url": mm(aid)}, "role": "reference_audio"})
            names.append("原声")
        uploads = p["uploads"]
        store.update(pid, lambda x: x.update({"uploads": uploads}))
        w = p["source"]
        ratio = media.ratio_of(w["width"], w["height"])
    except ApiError as e:
        stop_err = _fail_info(e.code, e.raw, None, "create")
    except UserError as e:
        stop_err = {**e.info, "retryable": False}
    except Exception as e:  # noqa: BLE001
        log.error("prepare submit: %s", traceback.format_exc())
        stop_err = {"code": "local", "title": "准备素材时出错", "action": f"再点一次开拍；还不行把「日志」文件夹发给作者。（{str(e)[:80]}）", "retryable": True}

    for tid in tids:
        t = next(t for t in store.load(pid)["takes"] if t["id"] == tid)
        if stop_err:
            _set_take(pid, tid, status="failed", error={**stop_err, "not_charged": True})
            continue
        tier = pricing.tier(t["tier"])
        body = {"model": tier.model, "resolution": tier.resolution, "duration": t["dur"], "ratio": ratio,
                "content": content, "generate_audio": True, "aigc_watermark": False}
        t0 = time.time()
        try:
            task = c.create_video(body)
        except NetError as e:
            # 网断时任务可能已经提交、照常扣费 → 先对账，接得上就接着等
            task = _reconcile(c, body, t0)
            if not task:
                log.error("create_video net error, no matching task: %s", e.raw[:300])
                _set_take(pid, tid, status="failed", content_names=names, error={
                    "code": "net", "title": "网络断了一下，不确定有没有提交成功",
                    "action": "先到 MiniMax 开放平台看最近的任务：有这一条的话已经扣费、等它拍完到平台下载；确认没有再点重拍。",
                    "retryable": True, "detail": e.raw[:300]})
                continue
            log.info("create_video net error, reconciled to task %s", task)
        except ApiError as e:
            if (e.http or 0) >= 500:
                # 网关 / 服务器错误时请求可能已经受理、照常扣费 → 和断网一样先对账
                task = _reconcile(c, body, t0)
                if task:
                    log.info("create_video http %s, reconciled to task %s", e.http, task)
                else:
                    log.error("create_video http %s, no unique matching task: %s", e.http, (e.raw or "")[:300])
                    _set_take(pid, tid, status="failed", content_names=names, error={
                        "code": e.code, "title": "MiniMax 服务器出错，不确定有没有提交成功",
                        "action": "先到 MiniMax 开放平台看最近的任务：有这一条的话已经扣费、等它拍完到平台下载；确认没有再点重拍。",
                        "retryable": True, "detail": (e.raw or "")[:300]})
                    continue
            else:
                err = _fail_info(e.code, e.raw, names, "create")
                _set_take(pid, tid, status="failed", error=err, content_names=names)
                if e.code in ("1008", "402", "2053", "2061", "2068", "1004", "2049"):
                    stop_err = err
                continue
        if getattr(c, "mock", False):
            st = p.get("sample_takes") or []
            if p.get("sample") and st:
                n = sum(1 for x in store.load(pid)["takes"] if x.get("task_id"))
                c.set_audio_source(task, store.pdir(pid) / st[n % len(st)], exact=True)
            else:
                c.set_audio_source(task, store.pdir(pid) / p["window"]["file"])
        _set_take(pid, tid, status="queued", task_id=task, content_names=names)

        def led(p, t=t, task=task):
            store.ledger_add(p, {"what": f"拍第 {t['n']} 条（{pricing.tier(t['tier']).name} {t['dur']} 秒）",
                                 "quote": t["quote"], "task_id": task, "mock": bool(getattr(c, "mock", False))})
        store.update(pid, led)


def _set_take(pid: str, tid: str, **kw) -> None:
    def fn(p):
        for t in p["takes"]:
            if t["id"] == tid:
                t.update(kw)
    store.update(pid, fn)


def retry_take(pid: str, tid: str, confirm_total: float, nonce: str, expect_mock: bool | None = None) -> dict:
    """没拍成的重拍：按原来的档位、时长再报价确认后提交一条新的。"""
    p = store.load(pid)
    t = next((t for t in p["takes"] if t["id"] == tid), None)
    if not t:
        raise UserError("找不到这一条")
    if t["status"] in ACTIVE:
        raise UserError("这条还在拍", "等它拍完再说。")
    return shoot(pid, t["tier"], 1, bool(t.get("trial")), confirm_total, nonce, expect_mock)


def cancel_take(pid: str, tid: str) -> dict:
    p = store.load(pid)
    t = next((t for t in p["takes"] if t["id"] == tid), None)
    if not t or not t.get("task_id"):
        raise UserError("这条还没提交上去", "稍等几秒再试。")
    if t["status"] != "queued":
        raise UserError("已经在拍了，取消不了", "拍摄中的任务官方不允许取消，等它拍完就行。")
    try:
        client(p).cancel(t["task_id"])
    except ApiError:
        raise UserError("已经开始拍了，取消不了", "拍摄中的任务官方不允许取消，等它拍完就行。")
    _set_take(pid, tid, status="cancelled", error={"title": "已取消", "action": "排队中取消，没扣费。", "not_charged": True})
    return store.load(pid)


# ---------------- 锁脸（11-23）----------------
def main_of(p: dict) -> str | None:
    """主角（锁脸、像不像核对都跟他）：A 放了照片就是 A；没有就是第一个放了照片的人。
    11-24 真爆款实测：三人舞里站最前、脸最大的是 B，用户只想换他，原来硬要求 A 有照片就开不了拍。"""
    cast = p.get("cast") or {}
    if "A" in cast:
        return "A"
    return sorted(cast)[0] if cast else None


def _other_refs(p: dict) -> list[Path]:
    """不该换脸的人的参考图：别的换上的人的照片 + 原片里保持原样的人（从原片截脸，两种拍法都要）。"""
    from . import faces
    d = store.pdir(p["id"])
    out = [d / c["photo"] for k, c in (p.get("cast") or {}).items() if k != main_of(p)]
    a = p.get("analysis") or {}
    for x in a.get("people", []):
        who = x["id"]
        if who in (p.get("cast") or {}) or not any(who in (s.get("who") or []) for s in a.get("shots", [])):
            continue
        f = d / f"素材/原片人物{who}.jpg"
        try:
            if f.exists() or faces.crop_person(d / p["window"]["file"], a["shots"], who, f):
                out.append(f)
        except Exception:  # noqa: BLE001
            log.error("crop person: %s", traceback.format_exc())
    return out


def _face_lock(p: dict, tid: str, out: Path) -> dict | None:
    """H3 拍完后用包内换脸引擎再锁一遍脸（实测像照片 0.60 → 0.81）。只锁主角（main_of）；侧脸保留 H3 原样（faces.lock_composite）。
    原来那版留作 拍次/tXX_换脸前.mp4，挑片页可以对比；锁脸失败就用 H3 原版，不影响这条片子。"""
    d = store.pdir(p["id"])
    raw = d / "拍次" / f"{tid}_换脸前.mp4"
    if p.get("sample"):
        # 示例：成片和「换脸前」都是预先做好的，不在用户电脑上现跑
        src = (p.get("sample_raw") or [None])[0]
        if src and (d / src).exists():
            shutil.copy2(d / src, raw)
        return p.get("sample_lock")
    main = main_of(p)
    if not (store.settings().get("face_lock", True) and faceswap.available() and main):
        return None
    take = next((x for x in p.get("takes", []) if x["id"] == tid), None)
    _set_take(p["id"], tid, step="facelock", step_ts=time.time())
    ffo = d / "拍次" / f"{tid}_换脸引擎.mp4"
    try:
        os.replace(out, raw)
        photo = d / _photo_of(p, take, main)
        info = faceswap.run(photo, raw, ffo)
        from . import faces
        st = faces.lock_composite(raw, ffo, out, photo, _other_refs(p))
        if not st.get("locked"):
            # 引擎一帧都没换到（整段侧脸、背影、脸太小）→ 用 AI 原版，挑片页说清楚
            os.replace(raw, out)
            return {**info, **st, "error": "这条没有能锁的正脸（可能整段是侧脸、背影或脸太小），用的是 AI 原版"}
        return {**info, **st}
    except Exception as e:  # noqa: BLE001
        log.error("face lock: %s", traceback.format_exc())
        if raw.exists():
            os.replace(raw, out)          # 用 AI 原版（锁到一半的成片作废）
        return {"error": "锁脸没成功，用的是 AI 原版（" + str(e)[:160] + "）"}
    finally:
        ffo.unlink(missing_ok=True)


# ---------------- 后台查进度 ----------------
def _charge(pid: str, t: dict, task: dict, c) -> None:
    """云端拍好就记账：之后下载、锁脸出错，钱也已经扣了，账本不能少记。按任务号只记一次（重新下载不重复记）。"""
    if getattr(c, "mock", False) or not t.get("task_id"):
        return
    actual = pricing.actual_from_usage(t["tier"], task.get("usage") or {})

    def fn(p):
        if not any(e.get("task_id") == t["task_id"] and "拍好" in (e.get("what") or "") for e in p.get("ledger", [])):
            store.ledger_add(p, {"what": f"第 {t['n']} 条拍好", "task_id": t["task_id"], "actual": actual})
    store.update(pid, fn)


def _finish(pid: str, tid: str, task: dict, c) -> None:
    p = store.load(pid)
    t = next(t for t in p["takes"] if t["id"] == tid)
    _charge(pid, t, task, c)
    d = store.pdir(pid)
    out = d / "拍次" / f"{tid}.mp4"
    _set_take(pid, tid, status="downloading")
    copy_audio = t.get("audio") == "orig"
    sync = None
    if copy_audio:
        # 用原声：H3 自己出的那版留作 _h3.mp4（对照用），成片换成原片原声，声音一点不变
        raw = d / "拍次" / f"{tid}_h3.mp4"
        c.download(task["content"]["url"], raw)
        wav = _audio_ref(p, t["dur"])
        shift = 0
        try:
            # 口型核对：H3 照搬了原声但整体错开一点（11-23 实测晚 0.18 秒，嘴也晚 0.16 秒）→ 原声跟着挪，嘴型就对上；
            # H3 自己重新念了（和原声对不上）→ 不挪，扣分提示
            sync = scoring.audio_sync(wav, raw)
            if sync and not sync["ok"] and sync["best"] >= 0.9 and 40 <= abs(sync["lag_ms"]) <= 600:
                shift = sync["lag_ms"]
                sync.update({"ok": True, "shifted_ms": shift})
        except Exception:  # noqa: BLE001
            log.error("audio sync: %s", traceback.format_exc())
        media.put_audio(raw, wav, out, delay_ms=shift)
    else:
        c.download(task["content"]["url"], out)
    lock = _face_lock(p, tid, out)
    usage = task.get("usage") or {}
    actual = 0.0 if getattr(c, "mock", False) else pricing.actual_from_usage(t["tier"], usage)
    a = t.get("analysis") or p["analysis"]          # 用开拍时那份，拍摄中重新拉片也不影响
    dur = t["dur"]
    src_cuts = [s["start"] for s in a["shots"] if 0.3 < s["start"] < dur - 0.3]
    lines = spoken(a["lines"], dur)
    expect = [say(l) for l in lines]
    orig = [l["text"] for l in a["lines"] if l["start"] < dur - 0.3]
    if copy_audio:
        # 声音就是原声，不用再花钱识别台词；字幕时间直接用原片的
        expect, orig = [], None
    if getattr(c, "mock", False):
        hint = d / "拍次" / f"{tid}_声音.mock.json"
        hint.write_text(json.dumps({"duration": dur, "segments": [
            {"start": l["start"] + 0.1, "end": l["end"] + 0.1, "text": say(l)} for l in lines]},
            ensure_ascii=False), encoding="utf-8")
    try:
        ev = scoring.evaluate(c, out, src_cuts, expect, orig, d / "拍次")
        heard = []
        wav = d / "拍次" / f"{tid}_声音.wav"
        score = {"total": ev["score"], "cut_mean": ev["cuts"]["mean"], "cuts": ev["cuts"]["rows"],
                 "missing": ev["cuts"]["missing"], "extra": len(ev["cuts"]["extra"]),
                 "lines": ev["lines"]["rows"], "lines_ok": ev["lines"]["ok"], "lines_total": ev["lines"]["total"],
                 "original_leak": ev["lines"]["original_leak"]}
        heard = ev.get("segments") or []
        if copy_audio:
            heard = [{"start": l["start"], "end": l["end"], "text": l["text"]} for l in lines]
        wav.unlink(missing_ok=True)
        # 换人核对：拍出来的脸更像你的照片还是更像原演员（本机 SFace，不花钱）
        try:
            from . import faces
            fcs = {}
            for who, c_ in (p.get("cast") or {}).items():
                r = faces.identity(out, a["shots"], d / _photo_of(p, t, who), d / p["window"]["file"], who)
                if r:
                    fcs[who] = r
            before = d / "拍次" / f"{tid}_换脸前.mp4"
            m = main_of(p)
            if before.exists() and m:
                r0 = faces.identity(before, a["shots"], d / _photo_of(p, t, m), d / p["window"]["file"], m)
                if r0:
                    score["faces_before"] = {m: r0}      # 锁脸前（H3 原版）的像不像，挑片页对比用
            if fcs:
                score["faces"] = fcs
                if not all(r["ok"] for r in fcs.values()):
                    score["total"] = max(0, score["total"] - 35)
                    score["face_penalty"] = 35          # 重新锁脸后像了要加回来
        except Exception:  # noqa: BLE001
            log.error("identity: %s", traceback.format_exc())
        if sync and lines:
            # H3 自己重新念了台词（挪也对不齐）→ 嘴型会和原声差零点几秒：扣分并在挑片页提示
            # 没人说话的片子（跳舞配乐）不核对口型：11-24 测侧脸那条只是 H3 自己配的音乐和原声差一点（0.79），被误扣 30 分
            score["audio_sync"] = sync
            if not sync["ok"]:
                score["total"] = max(0, score["total"] - 30)
        cost = 0 if getattr(c, "mock", False) else ev.get("cost", 0)
    except Exception:  # noqa: BLE001
        log.error("score: %s", traceback.format_exc())
        score, heard, cost = None, [], 0

    def fn(p):
        for x in p["takes"]:
            if x["id"] == tid:
                x.update({"status": "succeeded", "file": f"拍次/{tid}.mp4", "actual": actual, "usage": usage,
                          "score": score, "heard": heard, "step": None, "face_lock": lock,
                          "file_raw": f"拍次/{tid}_换脸前.mp4" if (d / "拍次" / f"{tid}_换脸前.mp4").exists() else None,
                          "elapsed": int((task.get("updated_at") or time.time()) - (task.get("created_at") or x["ts"]))})
        if not any(e.get("task_id") == t["task_id"] and "拍好" in (e.get("what") or "") for e in p.get("ledger", [])):
            store.ledger_add(p, {"what": f"第 {t['n']} 条拍好", "task_id": t["task_id"], "actual": actual})
        if cost:
            store.ledger_add(p, {"what": f"第 {t['n']} 条台词核对", "actual": cost})
        best = max((x for x in p["takes"] if x["status"] == "succeeded"),
                   key=lambda x: (x.get("score") or {}).get("total", 0), default=None)
        if best and not p.get("chosen_by_user"):
            p["chosen"] = best["id"]
    store.update(pid, fn)


def poll_once() -> None:
    for pid in store.all_ids():
        try:
            p = store.load(pid)
        except Exception:  # noqa: BLE001
            continue
        ja = (p.get("jobs") or {}).get("analyze") or {}
        if ja.get("status") == "running":
            with _FIN_LOCK:
                stale_ana = pid not in _ANALYZING
            if stale_ana:   # 标着「拉片中」，这个进程里却没在拉：上次拉片时程序被关掉了。不自动重拉（会花几分钱），让用户点
                def fn(x):
                    with _FIN_LOCK:     # 在锁里按最新状态再核一次：刚好拉完或刚开始拉的都不动
                        if pid in _ANALYZING or ((x.get("jobs") or {}).get("analyze") or {}).get("status") != "running":
                            return
                    x["jobs"]["analyze"] = {"status": "error", "step": "", "progress": 0, "error": {
                        "code": "interrupted", "title": "上次拉片时程序被关掉了",
                        "action": "点右下角「再拉一次」（几分钱）。", "retryable": True}}
                store.update(pid, fn)
        active = [t for t in p.get("takes", []) if t["status"] in ("queued", "running")]
        stale = [t for t in p.get("takes", []) if t["status"] == "submitting" and time.time() - t.get("ts", 0) > 180]
        for t in stale:
            _set_take(pid, t["id"], status="failed", error={
                "code": "interrupted", "title": "提交时程序被关掉了",
                "action": "这条可能已经扣费：到 MiniMax 开放平台看最近的任务；这里可以重拍。", "retryable": True})
        for t in p.get("takes", []):
            if t["status"] == "downloading" and t.get("op") == "relock" and (pid, t["id"]) not in _FINISHING:
                _recover_relock(pid, t)           # 本地重新锁脸被中断，不走云端收尾
        stuck_dl = [t for t in p.get("takes", []) if t["status"] == "downloading" and time.time() - t.get("ts", 0) > 60
                    and t.get("op") != "relock" and (pid, t["id"]) not in _FINISHING]   # 程序重开后接着收尾；正在队列里的不重复
        if not active and not stuck_dl:
            continue
        for t in active + stuck_dl:
            c = client_for(p, t)
            try:
                task = c.query(t["task_id"])
            except (ApiError, NetError):
                continue
            st = task.get("status")
            if st in ("queued", "running"):
                _set_take(pid, t["id"], status=st, elapsed=int(time.time() - t.get("ts", time.time())))
            elif st == "succeeded":
                key = (pid, t["id"])
                with _FIN_LOCK:
                    if key in _FINISHING:
                        continue
                    _FINISHING.add(key)
                try:
                    _set_take(pid, t["id"], status="downloading")
                    FINISH_POOL.submit(_finish_job, pid, t["id"], task, c)
                except Exception:  # noqa: BLE001
                    # 入队前出错要把「正在处理」标记还回去，不然这条永远被跳过
                    log.error("queue finish: %s", traceback.format_exc())
                    with _FIN_LOCK:
                        _FINISHING.discard(key)
            elif st in ("failed", "cancelled"):
                err = task.get("error") or {}
                info = _fail_info(str(err["code"]) if err.get("code") else None, err.get("message", ""),
                                  t.get("content_names"), "run")
                _set_take(pid, t["id"], status="failed" if st == "failed" else "cancelled", error=info)


def _finish_job(pid: str, tid: str, task: dict, c) -> None:
    """收尾（下载、贴原声、锁脸、打分）。出错最多再试 3 次，之后标成「拍好了但没存下来」，给「再试一次」。"""
    try:
        _finish(pid, tid, task, c)
    except Exception as e:  # noqa: BLE001
        log.error("finish: %s", traceback.format_exc())
        t = next((x for x in store.load(pid)["takes"] if x["id"] == tid), {})
        n = int(t.get("finish_fail") or 0) + 1
        if n >= 3:
            _set_take(pid, tid, status="failed", finish_fail=n, step=None, error={
                "code": "save_failed", "title": "拍好了，但存到电脑上时出错",
                "action": "片子还在 MiniMax 那边：点「再试一次」重新下载（不扣费）；还不行把「日志」文件夹发给作者。",
                "retryable": True, "refinish": True, "detail": str(e)[:200]})
        else:
            _set_take(pid, tid, status="running", finish_fail=n, step=None)     # 下一轮查进度时再试
    finally:
        with _FIN_LOCK:
            _FINISHING.discard((pid, tid))


def refinish_take(pid: str, tid: str) -> dict:
    """「拍好了但没存下来」的再试一次：重新查任务、下载、收尾，不重新提交、不扣费。"""
    t = next((x for x in store.load(pid)["takes"] if x["id"] == tid), None)
    if not t or not t.get("task_id") or not (t.get("error") or {}).get("refinish"):
        raise UserError("这条不需要再试")
    _set_take(pid, tid, status="running", finish_fail=0, error=None)
    return store.load(pid)


def relock_take(pid: str, tid: str) -> dict:
    """重新锁脸：从「换脸前」的 AI 原版重新做一遍，不花钱。"""
    p = store.load(pid)
    t = next((x for x in p["takes"] if x["id"] == tid and x["status"] == "succeeded"), None)
    if not t:
        raise UserError("这条还没拍好")
    if not faceswap.available():
        raise UserError("这个版本没带换脸引擎")
    key = (pid, tid)
    with _FIN_LOCK:
        if key in _FINISHING:
            raise UserError("这条正在处理", "等它处理完。")
        _FINISHING.add(key)

    def job():
        d = store.pdir(pid)
        out, raw = d / "拍次" / f"{tid}.mp4", d / "拍次" / f"{tid}_换脸前.mp4"
        prev = d / "拍次" / f"{tid}_上次锁脸.mp4"
        old_lock = t.get("face_lock") or {}
        try:
            if out.exists():
                shutil.copy2(out, prev)          # 现在这版先留一份，这次失败就换回来（老拍次没有锁脸记录也一样）
            if raw.exists():
                shutil.copy2(raw, out)           # 从 AI 原版重新锁
            p2 = store.load(pid)
            lock = _face_lock(p2, tid, out)
            if lock and lock.get("error") and prev.exists():
                os.replace(prev, out)
                lock = old_lock or None
            sc = dict(t.get("score") or {})
            a = t.get("analysis") or p2.get("analysis")
            m = main_of(p2)
            if a and m:
                from . import faces
                r = faces.identity(out, a["shots"], d / _photo_of(p2, t, m), d / p2["window"]["file"], m)
                if r:
                    sc["faces"] = {**(sc.get("faces") or {}), m: r}
                    pen = int(sc.get("face_penalty") or 0)
                    if r["ok"] and pen:                       # 原来因为不像扣过分，现在像了就加回来
                        sc["total"], sc["face_penalty"] = min(100, int(sc.get("total") or 0) + pen), 0
                    elif not r["ok"] and not pen and sc.get("total") is not None:
                        sc["total"], sc["face_penalty"] = max(0, int(sc["total"]) - 35), 35

            def fn(p):
                for x in p["takes"]:
                    if x["id"] == tid:
                        x.update({"status": "succeeded", "step": None, "op": None, "face_lock": lock, "score": sc,
                                  "file_raw": f"拍次/{tid}_换脸前.mp4" if raw.exists() else None})
                best = max((x for x in p["takes"] if x["status"] == "succeeded"),
                           key=lambda x: (x.get("score") or {}).get("total", 0), default=None)
                if best and not p.get("chosen_by_user"):
                    p["chosen"] = best["id"]
            store.update(pid, fn)
        except Exception:  # noqa: BLE001
            log.error("relock: %s", traceback.format_exc())
            if prev.exists():
                os.replace(prev, out)
            _set_take(pid, tid, status="succeeded", step=None, op=None)
        finally:
            prev.unlink(missing_ok=True)
            with _FIN_LOCK:
                _FINISHING.discard(key)
    try:
        # 状态仍用「处理中」好让网页自动刷新；op=relock 标明是本地重新锁脸，程序重开后不会被当成云端收尾（R4）
        _set_take(pid, tid, status="downloading", step="facelock", step_ts=time.time(), op="relock")
        FINISH_POOL.submit(job)
    except Exception:  # noqa: BLE001
        with _FIN_LOCK:
            _FINISHING.discard(key)
        raise
    return store.load(pid)


def _recover_relock(pid: str, t: dict) -> None:
    """重新锁脸做到一半程序被关掉：拿上次锁好的（或 AI 原版）放回去，告诉用户可以再点一次。"""
    d = store.pdir(pid)
    tid = t["id"]
    out, raw, prev = d / "拍次" / f"{tid}.mp4", d / "拍次" / f"{tid}_换脸前.mp4", d / "拍次" / f"{tid}_上次锁脸.mp4"
    try:
        if prev.exists():
            os.replace(prev, out)
            lock = t.get("face_lock")
        else:
            if raw.exists():
                shutil.copy2(raw, out)
            lock = {"error": "上次重新锁脸被中断（程序被关掉了），现在用的是 AI 原版，可以再点一次「重新锁脸」"}
        _set_take(pid, tid, status="succeeded", step=None, op=None, face_lock=lock)
    except Exception:  # noqa: BLE001
        log.error("recover relock: %s", traceback.format_exc())


_STOP = threading.Event()


def start_poller() -> None:
    def loop():
        while not _STOP.is_set():
            try:
                poll_once()
            except Exception:  # noqa: BLE001
                log.error("poll: %s", traceback.format_exc())
            _STOP.wait(4 if is_mock() else 10)
    threading.Thread(target=loop, name="h3dt-poller", daemon=True).start()


# ---------------- 挑片和导出 ----------------
def choose(pid: str, tid: str) -> dict:
    def fn(p):
        if not any(t["id"] == tid and t["status"] == "succeeded" for t in p["takes"]):
            raise UserError("这条还没拍好")
        p["chosen"] = tid
        p["chosen_by_user"] = True
    return store.update(pid, fn)


def _srt_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def export(pid: str, tid: str, raw: bool = False) -> dict:
    p = store.load(pid)
    t = next((t for t in p["takes"] if t["id"] == tid and t["status"] == "succeeded"), None)
    if not t:
        raise UserError("这条还没拍好")
    d = store.pdir(pid)
    stamp = time.strftime("%H%M%S")
    src = d / t["file"]
    if raw:
        if not t.get("file_raw") or not (d / t["file_raw"]).exists():
            raise UserError("这条没有换脸前的版本")
        src = d / t["file_raw"]
    tag = "_换脸前" if raw else ""
    out = d / "导出" / f"成片_第{t['n']}条{tag}_{stamp}.mp4"     # 带条号：同一秒导出两条时不会互相覆盖（11-23 实测撞名）
    # 画面上不加任何水印或小标，原样导出（不重新编码，画质无损）
    shutil.copy2(src, out)
    # 字幕：台词文字用我们写的，时间用这一条实际说话的时间
    a = t.get("analysis") or p["analysis"]
    lines = spoken(a["lines"], t["dur"])
    # 用原声时时间就是原片的；重新配音时按顺序一对一配识别结果（同样的两句不会挤到同一个时间），配不上就用分镜时间
    heard = [] if t.get("audio") == "orig" else sorted(t.get("heard") or [], key=lambda h: float(h.get("start", 0)))
    rows = []
    j = 0
    for k, l in enumerate(lines, 1):
        text = say(l)
        st, en = l["start"], l["end"]
        cand = heard[j:j + 3]
        if cand:
            r = [scoring.difflib.SequenceMatcher(None, scoring.norm(text), scoring.norm(h.get("text", ""))).ratio() for h in cand]
            i = max(range(len(cand)), key=lambda n: r[n])
            if r[i] >= 0.4:
                st, en = float(cand[i].get("start", st)), float(cand[i].get("end", en))
                j += i + 1
        rows.append(f"{k}\n{_srt_time(st)} --> {_srt_time(en)}\n{text}\n")
    srt = out.with_suffix(".srt")
    srt.write_text("\n".join(rows), encoding="utf-8-sig")

    def fn(p):
        p.setdefault("exports", []).append({"time": time.strftime("%H:%M"), "take": tid, "raw": bool(raw),
                                           "mp4": f"导出/{out.name}", "srt": f"导出/{srt.name}"})
    store.update(pid, fn)
    return {"mp4": _url(pid, f"导出/{out.name}"), "srt": _url(pid, f"导出/{srt.name}"), "folder": "导出"}


# ---------------- 示例 ----------------
def open_sample() -> dict:
    src = paths.SAMPLES
    cands = [d for d in src.iterdir() if (d / "project.json").exists()] if src.exists() else []
    if not cands:
        raise UserError("示例作品还没装好", "这个版本缺示例文件，直接传一段你自己的视频试试（模拟模式不花钱）。")
    pid = store.new_id()
    shutil.copytree(cands[0], store.pdir(pid))
    def fn(p):
        p["id"] = pid
        p["sample"] = True
        p.setdefault("audio", "new")      # 示例成片是 H3 自己配的声音，不能再贴原声
        p["created"] = time.strftime("%Y-%m-%d %H:%M")
        p["ledger"] = []
        p["nonces"] = []
        p["uploads"] = {}
    return store.update(pid, fn)
