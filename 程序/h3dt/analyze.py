"""拉片：本机切镜 + 语音识别（每句起止时间）+ M3.1-Flash 看片写每镜描述。

结果结构（存进 project.json 的 analysis）：
{
  "shots": [{"i":1,"start":0.0,"end":3.2,"thumb":"拉片/shot01.jpg","size":"中景","camera":{"type":"推","amp":"小幅","speed":"慢"},
             "action":"...","action_en":"...","who":["A"],"hard":[],"edited":false}],
  "lines": [{"i":1,"start":0.4,"end":2.6,"speaker":"S1","who":"A","text":"...","new":null}],
  "people": [{"id":"A","desc":"...","desc_en":"...","gender":"female"}],
  "env": "...", "env_en": "...", "style_en": "...", "sound_en": "...", "music_en": "...",
  "subtitle": {"has":true,"pos":"bottom","band":0.14}, "watermark": false,
  "cost": 0.03
}
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

from . import media, pricing
from .errors import ApiError
from .minimax import MiniMax

SIZES = ["远景", "全景", "中景", "近景", "特写"]
CAM_TYPES = ["固定", "推", "拉", "摇", "移", "跟", "升降", "手持", "环绕"]
AMPS = ["轻微", "小幅", "中幅", "大幅"]
SPEEDS = ["慢", "中", "快"]

SIZE_EN = {"远景": "extreme wide shot", "全景": "wide shot", "中景": "medium shot", "近景": "medium close-up", "特写": "close-up"}
CAM_EN = {"固定": "static camera", "推": "push-in", "拉": "pull-out", "摇": "pan", "移": "tracking move",
          "跟": "follow shot", "升降": "crane move", "手持": "handheld camera", "环绕": "orbit"}
AMP_EN = {"轻微": "subtle", "小幅": "small", "中幅": "moderate", "大幅": "large"}
SPEED_EN = {"慢": "slow", "中": "medium-speed", "快": "fast"}


def cut_shots(video: Path, dur: float) -> list[dict]:
    cuts = [c for c in media.scenes(video) if 0.2 < c < dur - 0.2]
    bounds = [0.0, *cuts, round(dur, 3)]
    shots = []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        hard = ["快切"] if e - s < 0.5 else []
        shots.append({"i": i + 1, "start": round(s, 3), "end": round(e, 3), "hard": hard})
    return shots


def thumbs(video: Path, shots: list[dict], out_dir: Path, rel_base: Path) -> None:
    for s in shots:
        mid = s["start"] + (s["end"] - s["start"]) * 0.5
        p = media.frame(video, mid, out_dir / f"shot{s['i']:02d}.jpg", width=360)
        s["thumb"] = p.relative_to(rel_base).as_posix()


SENT_END = "。！？!?…"


def words_to_lines(words: list[dict], gap: float = 1.5) -> list[dict]:
    """逐字时间戳 → 句子。官方按句模式会把整段并成一句（实测 11-22），所以自己按句末标点和长停顿断句。"""
    lines: list[dict] = []
    cur: list[dict] = []

    def flush():
        if cur:
            text = "".join(w.get("text", "") for w in cur).strip()
            if text:
                lines.append({"start": round(float(cur[0]["start"]), 3), "end": round(float(cur[-1]["end"]), 3),
                              "speaker": cur[0].get("speaker") or "S1", "text": text, "new": None})
        cur.clear()

    for w in words:
        if cur and float(w["start"]) - float(cur[-1]["end"]) >= gap:
            flush()
        cur.append(w)
        if (w.get("text") or "").strip()[-1:] in SENT_END:
            flush()
    flush()
    for n, l in enumerate(lines, 1):
        l["i"] = n
    return lines


def transcribe(client: MiniMax, video: Path, work: Path) -> tuple[list[dict], float]:
    wav = media.extract_audio(video, work / "拉片" / "原声.wav")
    try:
        j = client.asr(wav, level="word")
    except ApiError:
        return [], 0.0   # 只有音乐、没人声时官方会报错（实测 1041）
    segs = j.get("segments") or []
    lines = words_to_lines(segs) if segs and max(len(s.get("text", "")) for s in segs) <= 4 else [
        {"i": n, "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
         "speaker": s.get("speaker") or "S1", "text": s["text"].strip(), "new": None}
        for n, s in enumerate(segs, 1) if s.get("text", "").strip()]
    return lines, pricing.asr_cost(float(j.get("duration") or 0))


VISION_SYS = """你是专业剪辑师兼分镜师，任务是「拉片」：逐镜头拆解一段短视频，供 AI 视频模型照着重拍。
只输出 JSON，不要任何解释。字段：
{
 "people": [{"id":"A","desc":"中文：性别、年龄段、发型、衣着、显著特征","desc_en":"same in English","outfit_en":"English: clothing, shoes and accessories ONLY (no face, hair, makeup or body)","gender":"female|male"}],
 "env": "中文：地点、时间、天气、光线", "env_en": "English",
 "style_en": "one English sentence: visual style, color grade, lighting mood",
 "sound_en": "English: ambience and physical sounds only (no music, no dialogue)",
 "music_en": "English: background music style if any, else N/A",
 "subtitle": {"has": true|false, "pos": "bottom|top|none", "box": [x, y, w, h]},
 "watermark": true|false,
 "watermark_boxes": [[x, y, w, h]],
 "line_who": {"1": "A"},
 "line_kinds": {"1": "dialogue|lyrics|narration"},
 "shots": [{"i":1,"size":"远景|全景|中景|近景|特写","camera":{"type":"固定|推|拉|摇|移|跟|升降|手持|环绕","amp":"轻微|小幅|中幅|大幅","speed":"慢|中|快"},
            "action":"中文：这一镜谁在画面哪里、做什么动作、表情变化，一两句","action_en":"English, concrete and visual, present tense","who":["A"],
            "hard": ["打斗"|"复杂运镜"|"多人"]}]
}
规则：action_en 里提到人一律写 "person A"、"person B"（不要只写 A，也不要写 she/he 开头），只写动作、姿态、表情、走位，不写外貌和衣着；
镜头数量和顺序必须和给定的切点表完全一致；固定镜头的 amp 和 speed 写 "轻微" 和 "慢"；
人物用 A、B、C 编号，同一人在所有镜头编号一致；A 必须是全片最主要的人（站得最靠前、脸在画面里最大、出镜最多的那个，多人跳舞时通常是中间领舞），其余按主次往后排，people 也按这个顺序；
line_who：逐句（按序号）判断是谁说的（语音识别分不清男女，别信它的 S1/S2）：看这句话的时间落在哪个镜头、画面里谁在张嘴、声音该是男是女；
不要描述字幕文字本身；看不清的就写看得见的部分，不编造。
subtitle.box：所有字幕出现过的区域合起来的框（[左, 上, 宽, 高]，占画面比例，宁可框大一点，上下各多留一点），没有字幕给 null；
watermark_boxes：平台水印、账号名、台标、贴纸的位置（不含字幕），每个是 [左, 上, 宽, 高]，都用占画面宽高的比例（0~1），宁可框大一点；水印会移动就把出现过的位置都列上。没有就给 []。
line_kinds：逐句判断语音识别的每一句（按序号）：画面里的人张嘴在说 = dialogue；是背景音乐里的歌词（画面里没人在说或口型对不上）= lyrics；画外旁白 = narration。
如果有 lyrics，music_en 要写这段背景音乐的风格（按歌词语言、画面节奏推断，例如 an upbeat English hip-hop track with a strong beat），不要写 N/A。"""


def vision(client: MiniMax, video: Path, shots: list[dict], lines: list[dict], max_mb: float = 45) -> tuple[dict, float]:
    size = video.stat().st_size / 1e6
    if size > max_mb:
        raise RuntimeError("原片太大，AI 看片前请先截短")
    b64 = base64.b64encode(video.read_bytes()).decode()
    cut_table = "\n".join(f"镜{s['i']}: {s['start']:.2f}s - {s['end']:.2f}s" for s in shots)
    line_table = "\n".join(f"{l['i']}. {l['start']:.2f}-{l['end']:.2f}s: {l['text']}" for l in lines) or "（没有台词）"
    user = [
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}, "fps": 2},
        {"type": "text", "text": f"切点表（共 {len(shots)} 镜）：\n{cut_table}\n\n语音识别的台词：\n{line_table}\n\n按要求输出 JSON。"},
    ]
    msgs = [{"role": "system", "content": VISION_SYS}, {"role": "user", "content": user}]
    cost = 0.0
    last = None
    for tokens in (12000, 20000):   # 偶尔输出被截断（实测 11-22），再要一次
        try:
            text, usage = client.chat(msgs, json_mode=True, max_tokens=tokens)
        except ApiError as e:
            last = e
            continue
        cost += pricing.tokens_cost(usage)
        try:
            return parse_json(text), cost
        except ValueError as e:
            last = e
    raise RuntimeError(f"AI 看片结果读不出来：{last}")


def vision_gpt(g, video: Path, shots: list[dict], lines: list[dict], work: Path) -> tuple[dict, dict]:
    """GPT 看片（可选，用用户的 OpenAI 额度）：GPT 收不了整段视频，按每秒 2 帧抽图、每张标时间发过去，要求同一份 JSON。"""
    from .gpt import GPTError
    fdir = work / "拉片" / "_gpt帧"
    if fdir.exists():
        for f in fdir.glob("*.jpg"):
            f.unlink()
    fdir.mkdir(parents=True, exist_ok=True)
    media.ff("-i", str(video), "-vf", "fps=2,scale='if(gt(iw,ih),768,-2)':'if(gt(iw,ih),-2,768)'", "-q:v", "3",
             str(fdir / "f%03d.jpg"))
    frames = sorted(fdir.glob("f*.jpg"))
    cut_table = "\n".join(f"镜{s['i']}: {s['start']:.2f}s - {s['end']:.2f}s" for s in shots)
    line_table = "\n".join(f"{l['i']}. {l['start']:.2f}-{l['end']:.2f}s: {l['text']}" for l in lines) or "（没有台词）"
    user: list[dict] = [{"type": "text", "text": f"下面是这段视频按每秒 2 帧抽出的画面（共 {len(frames)} 张，每张前面标了时间）。"}]
    for n, f in enumerate(frames):
        user += [{"type": "text", "text": f"t={n * 0.5:.1f}s"},
                 {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode(),
                                                     "detail": "high"}}]
    user.append({"type": "text", "text": f"切点表（共 {len(shots)} 镜）：\n{cut_table}\n\n语音识别的台词：\n{line_table}\n\n按要求输出 JSON。"})
    try:
        text, usage = g.chat_json([{"role": "system", "content": VISION_SYS}, {"role": "user", "content": user}])
        return parse_json(text), usage
    except ValueError:
        raise GPTError("GPT 返回的拉片表读不出来") from None
    finally:
        for f in frames:
            f.unlink(missing_ok=True)


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


def merge(shots: list[dict], lines: list[dict], v: dict) -> dict:
    vs = {int(s.get("i", n + 1)): s for n, s in enumerate(v.get("shots") or [])}
    for s in shots:
        x = vs.get(s["i"], {})
        size = x.get("size") if x.get("size") in SIZES else "中景"
        cam = x.get("camera") or {}
        s["size"] = size
        s["camera"] = {"type": cam.get("type") if cam.get("type") in CAM_TYPES else "固定",
                       "amp": cam.get("amp") if cam.get("amp") in AMPS else "轻微",
                       "speed": cam.get("speed") if cam.get("speed") in SPEEDS else "慢"}
        s["action"] = x.get("action") or ""
        s["action_en"] = x.get("action_en") or ""
        s["who"] = [w for w in (x.get("who") or []) if isinstance(w, str)]
        s["hard"] = sorted(set(s.get("hard", []) + [h for h in (x.get("hard") or []) if h in ("打斗", "复杂运镜", "多人")]))
        s["edited"] = False
    lw = {str(k): str(x) for k, x in (v.get("line_who") or {}).items()}
    spk = v.get("speakers") or {}
    kinds = {str(k): str(x) for k, x in (v.get("line_kinds") or {}).items()}
    lyrics = []
    talk = []
    for l in lines:
        l["who"] = lw.get(str(l["i"])) or spk.get(l["speaker"]) or "A"
        kind = kinds.get(str(l["i"]), "dialogue")
        if kind == "lyrics":
            lyrics.append(l)
        else:
            l["kind"] = kind
            talk.append(l)
    for n, l in enumerate(talk, 1):
        l["i"] = n
    boxes = []
    for b in v.get("watermark_boxes") or []:
        try:
            x, y, w, h = (float(t) for t in b)
            if 0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and w * h < 0.2:
                boxes.append([round(x, 3), round(y, 3), round(w, 3), round(h, 3)])
        except (TypeError, ValueError):
            continue
    sub = v.get("subtitle") or {}
    band = 0.0
    erase = None
    sb = sub.get("box")
    if sub.get("has") and isinstance(sb, list) and len(sb) == 4:
        try:
            x, y, w, h = (float(t) for t in sb)
            # 字幕框：左右撑满、上下各多留 2%，和水印一样抹掉（不裁画面，画幅和成片保持一致）
            y0, y1 = max(0.0, y - 0.02), min(1.0, y + h + 0.02)
            erase = [0.0, round(y0, 3), 1.0, round(y1 - y0, 3)]
            band = round(y1 - y0, 3)
        except (TypeError, ValueError):
            pass
    return {
        "shots": shots, "lines": talk, "lyrics": lyrics, "watermark_boxes": boxes,
        "people": v.get("people") or [{"id": "A", "desc": "", "desc_en": "", "gender": ""}],
        "env": v.get("env", ""), "env_en": v.get("env_en", ""),
        "style_en": v.get("style_en", ""), "sound_en": v.get("sound_en", ""), "music_en": v.get("music_en", "N/A"),
        "subtitle": {"has": bool(sub.get("has")), "pos": sub.get("pos") or "none", "band": band, "erase": erase},
        "watermark": bool(v.get("watermark")),
    }


def speech_rate(lines: list[dict]) -> float:
    """原片语速（字/秒），用来给新台词限字数。没有台词时按 4 字/秒。"""
    chars = sum(len(re.sub(r"[\s，。！？、,.!?…“”\"']", "", l["text"])) for l in lines)
    secs = sum(max(0.3, l["end"] - l["start"]) for l in lines)
    return round(chars / secs, 2) if secs > 0 and chars else 4.0


def run(client: MiniMax, video: Path, work: Path, rel_base: Path, on_step=None, gpt=None) -> dict:
    """完整拉片。video 应是已截好的原片段（≤15 秒）。gpt：设置里选了 GPT 看片时传入，出错自动改用 MiniMax。"""
    step = on_step or (lambda *_: None)
    info = media.probe(video)
    step("切镜头", 0.1)
    shots = cut_shots(video, info["duration"])
    step("抽关键帧", 0.25)
    thumbs(video, shots, work / "拉片", rel_base)
    media.strip_frames(video, work / "拉片" / "胶片.jpg", count=max(8, int(info["duration"] * 2)))
    cost = 0.0
    lines: list[dict] = []
    if info["has_audio"]:
        step("识别台词", 0.4)
        lines, c = transcribe(client, video, work)
        cost += c
    v, by, note, gu = None, "MiniMax M3.1-Flash", "", None
    if gpt is not None:
        step("GPT 看片", 0.6)
        try:
            v, gu = vision_gpt(gpt, video, shots, lines, work)
            by = gpt.model
        except Exception as e:  # noqa: BLE001  GPT 这条路任何问题都不让拉片失败
            note = f"{getattr(e, 'why', 'GPT 看片出错')}，这次改用 MiniMax 看片"
            logging.getLogger("h3dt.analyze").warning("GPT 看片失败，改用 MiniMax：%r", e)
    if v is None:
        step("AI 看片", 0.6)
        v, c = vision(client, video, shots, lines)
        cost += c
    step("整理拉片表", 0.95)
    a = merge(shots, lines, v)
    a["vision_by"] = by
    if note:
        a["vision_note"] = note
    if gu:
        a["gpt_usage"] = {k: gu.get(k, 0) for k in ("prompt_tokens", "completion_tokens")}
    a["rate"] = speech_rate(a["lines"])
    a["cost"] = round(cost, 4)
    a["strip"] = (work / "拉片" / "胶片.jpg").relative_to(rel_base).as_posix()
    return a
