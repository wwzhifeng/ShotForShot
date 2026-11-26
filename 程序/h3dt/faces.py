"""人脸相关（全部本机、OpenCV DNN 跑，不需要显卡）：
- YuNet 检测（MIT，opencv_zoo）
- BiSeNet 人脸分割（MIT，yakhyo/face-parsing；模型和预处理参数与 FaceFusion 一致）
- SFace 人脸识别（Apache-2.0，opencv_zoo）
用途：①「动作照抄」时把要换掉的演员的脸和头发涂掉（11-22 实测 E1：涂实心块 H3 才不会把原演员学回去）；
     ②挑片打分：拍出来的脸更像你的照片还是更像原演员；③「照着拍」时截不换的人的脸当参考图。
FaceFusion 里的 RetinaFace / SCRFD / ArcFace（InsightFace 禁商用）、YOLO-Face / XSeg（GPL）都不用。"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from . import media, paths

MODEL_DIR = paths.PROGRAM / "models"
DET = "face_detection_yunet_2023mar.onnx"
PARSER = "bisenet_resnet_34.onnx"
REC = "face_recognition_sface_2021dec.onnx"
# BiSeNet（CelebAMask-HQ 19 类）：要涂掉的 = 脸、眉、眼、眼镜、耳、耳饰、鼻、嘴、唇、头发、帽子；脖子和衣服不涂
MASK_CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18)
GRAY = (90, 90, 90)
SAME = 0.363          # SFace 官方建议的余弦相似度阈值：高于它算同一个人

_LOCK = threading.Lock()
_TL = threading.local()


def _cache() -> dict:
    """模型按线程各存一份：11-24 实测同时开拍几条时，多个线程共用一个 OpenCV 人脸检测器会报
    buf.shape() == m.shape() 断言错误（OpenCV 5 的新推理引擎不能多线程共用同一个网络）。"""
    c = getattr(_TL, "cache", None)
    if c is None:
        c = _TL.cache = {}
    return c


def _in_model_dir(fn):
    """OpenCV 的 C++ 层打不开中文路径：切到模型目录、只传 ASCII 文件名。"""
    with _LOCK:
        cwd = os.getcwd()
        os.chdir(MODEL_DIR)
        try:
            return fn()
        finally:
            os.chdir(cwd)


def _det(w: int, h: int):
    import cv2
    key = ("det", w, h)
    if key not in _cache():
        _cache()[key] = _in_model_dir(lambda: cv2.FaceDetectorYN.create(DET, "", (w, h), 0.6, 0.3, 50))
    return _cache()[key]


def _parser():
    import cv2
    if "parser" not in _cache():
        _cache()["parser"] = _in_model_dir(lambda: cv2.dnn.readNetFromONNX(PARSER))
    return _cache()["parser"]


def _rec():
    import cv2
    if "rec" not in _cache():
        _cache()["rec"] = _in_model_dir(lambda: cv2.FaceRecognizerSF.create(REC, ""))
    return _cache()["rec"]


def _frames(video: Path, w: int, h: int, fps: float | None = None, start: float = 0.0):
    """用包内 ffmpeg 读帧（不依赖 OpenCV 的视频模块）。"""
    import numpy as np
    args = [paths.tool("ffmpeg"), "-hide_banner", "-loglevel", "error"]
    if start:
        args += ["-ss", f"{start:.3f}"]
    args += ["-i", str(video)]
    if fps:
        args += ["-vf", f"fps={fps}"]
    args += ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, creationflags=media.NOWIN)
    size = w * h * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
    finally:
        p.stdout.close()
        p.wait()


def _frame(video: Path, w: int, h: int, t: float = 0.0):
    """读单帧（带 -frames:v 1，免得提前关管道时 ffmpeg 报 Broken pipe）。"""
    import numpy as np
    seek = ["-ss", f"{t:.3f}"] if t > 0 else []      # 图片加 -ss 0 会读不出帧（实测）
    p = subprocess.run([paths.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", *seek, "-i", str(video),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True,
                       creationflags=media.NOWIN)
    if len(p.stdout) < w * h * 3:
        return None
    return np.frombuffer(p.stdout[: w * h * 3], np.uint8).reshape(h, w, 3).copy()


def detect(fr):
    """大图（>1280）先缩小再检测，框按比例放回原图坐标（实测 2K 大头照原尺寸检测不到脸）。"""
    import cv2
    h, w = fr.shape[:2]
    s = min(1.0, 1280 / max(w, h))
    img = fr if s == 1.0 else cv2.resize(fr, (int(w * s) // 2 * 2, int(h * s) // 2 * 2))
    ih, iw = img.shape[:2]
    _, res = _det(iw, ih).detect(img)
    if res is None:
        return []
    out = []
    for r in res:
        r = r.copy()
        r[:14] = r[:14] / s           # 框和 5 个关键点都放回原图坐标
        out.append(r)
    return out


def embed(fr, face):
    rec = _rec()
    return rec.feature(rec.alignCrop(fr, face))


def similar(a, b) -> float:
    import cv2
    return float(_rec().match(a, b, cv2.FaceRecognizerSF_FR_COSINE))


def photo_embedding(photo: Path):
    import numpy as np
    info = media.probe(photo)
    w, h = info["width"], info["height"]
    fr = _frame(photo, w, h)
    faces = detect(fr)
    if not faces:
        return None
    f = max(faces, key=lambda r: r[2] * r[3])
    return embed(fr, f)


def _parse_mask(fr, face):
    """脸 + 头发的精确轮廓（BiSeNet），返回整帧大小的布尔遮罩；失败时退回放大的矩形。"""
    import cv2
    import numpy as np
    h, w = fr.shape[:2]
    x, y, fw, fh = (float(v) for v in face[:4])
    cx, cy = x + fw / 2, y + fh / 2
    s = max(fw, fh) * 2.6
    x0, y0 = int(max(0, cx - s / 2)), int(max(0, cy - s * 0.6))
    x1, y1 = int(min(w, cx + s / 2)), int(min(h, cy + s * 0.4))
    m = np.zeros((h, w), bool)
    try:
        crop = fr[y0:y1, x0:x1]
        inp = cv2.resize(crop, (512, 512))[:, :, ::-1].astype(np.float32) / 255.0
        inp = (inp - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        net = _parser()
        with _LOCK:
            net.setInput(np.ascontiguousarray(inp.transpose(2, 0, 1)[None]))
            out = net.forward()
        cls = out[0].argmax(0)
        sub = np.isin(cls, MASK_CLASSES).astype(np.uint8)
        sub = cv2.resize(sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        sub = cv2.dilate(sub, np.ones((15, 15), np.uint8))
        m[y0:y1, x0:x1] = sub.astype(bool)
        if m.sum() < fw * fh * 0.5:          # 分割不靠谱时退回矩形
            raise ValueError
    except Exception:  # noqa: BLE001
        bx0, by0 = int(max(0, cx - fw * 0.85)), int(max(0, cy - fh * 1.15))
        bx1, by1 = int(min(w, cx + fw * 0.85)), int(min(h, cy + fh * 0.85))
        m[by0:by1, bx0:bx1] = True
    return m


def person_refs(video: Path, shots: list[dict], people: set[str]) -> dict:
    """每个人在他单独出镜的镜头里取一张脸的特征，用来在同框镜头里分清谁是谁。"""
    info = media.probe(video)
    w, h = info["width"], info["height"]
    refs = {}
    for pid in people:
        for s in [s for s in shots if s.get("who") == [pid]]:
            t = (s["start"] + s["end"]) / 2
            fr = _frame(video, w, h, t)
            if fr is None:
                continue
            faces = detect(fr)
            if faces:
                refs[pid] = embed(fr, max(faces, key=lambda r: r[2] * r[3]))
                break
    return refs


def mask_shots(src: Path, out: Path, shots: list[dict], cast: set[str], keep: set[str]) -> dict:
    """src 是做好的参考片（去音轨、25fps）。有要换的人出场的镜头里，把他的脸和头发涂成灰色；
    同框的不换的人用人脸识别分出来、不涂（分不出来时宁可都涂）。"""
    info = media.probe(src)
    w, h, fps = info["width"], info["height"], info["fps"] or 25
    refs = person_refs(src, shots, cast | keep)
    out.parent.mkdir(parents=True, exist_ok=True)
    wr = subprocess.Popen([paths.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                           "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-", "-c:v", "libx264",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE, creationflags=media.NOWIN)

    def shot_at(t):
        return next((s for s in shots if s["start"] <= t < s["end"]), None)

    k = hits = masked = 0
    last_mask = None
    for fr in _frames(src, w, h):
        t = k / fps
        s = shot_at(t)
        who = set((s or {}).get("who") or [])
        if who & cast:
            if k % 2 == 0 or last_mask is None:          # 隔帧重算，省一半时间
                faces = detect(fr)
                if faces:
                    hits += 1
                mask = None
                for f in faces:
                    if who - cast and refs:
                        e = embed(fr, f)
                        best = max(refs, key=lambda p: similar(e, refs[p]))
                        if best not in cast:
                            continue
                    fm = _parse_mask(fr, f)
                    mask = fm if mask is None else (mask | fm)
                last_mask = mask if mask is not None else last_mask
            if last_mask is not None:
                fr[last_mask] = GRAY
                masked += 1
        else:
            last_mask = None
        wr.stdin.write(fr.tobytes())
        k += 1
    wr.stdin.close()
    wr.wait()
    return {"frames": k, "detected": hits, "masked": masked, "refs": sorted(refs)}


def identity(video: Path, shots: list[dict], cast_photo: Path, orig_video: Path | None, pid: str = "A") -> dict | None:
    """拍出来的片子里，这个人的脸更像你的照片还是更像原演员（每秒取 2 帧，只看他出镜的镜头）。"""
    me = photo_embedding(cast_photo)
    if me is None:
        return None
    orig = None
    if orig_video:
        orig = person_refs(orig_video, shots, {pid}).get(pid)
    info = media.probe(video)
    w, h = info["width"], info["height"]
    # 11-23 实测：多人镜头里他背身/侧脸时只检出别人，切点附近成片和原片差零点几秒会取到别人的镜头，
    # 都会把分数拉到 0 附近、把换成功的判成不像。所以有单独出镜的镜头就只看那些，并避开切点前后 0.35 秒。
    use = [s for s in shots if (s.get("who") or []) == [pid]] or [s for s in shots if pid in (s.get("who") or [])]
    sims, sims_o = [], []
    for k, fr in enumerate(_frames(video, w, h, fps=2)):
        t = k / 2
        if not any(s["start"] + 0.35 <= t < s["end"] - 0.35 for s in use):
            continue
        faces = detect(fr)
        if not faces:
            continue
        embs = [embed(fr, f) for f in faces]
        best = max(embs, key=lambda e: similar(e, me))
        sims.append(similar(best, me))
        if orig is not None:
            sims_o.append(similar(best, orig))
    if not sims:
        return None
    sp = round(sum(sims) / len(sims), 3)
    so = round(sum(sims_o) / len(sims_o), 3) if sims_o else None
    ok = sp >= SAME and (so is None or sp > so)
    return {"photo": sp, "orig": so, "ok": ok, "frames": len(sims)}


def crop_person(video: Path, shots: list[dict], pid: str, out: Path) -> bool:
    """「照着拍」时保住不换的人：在他单独出镜的镜头里截一帧，取最大的脸，连头发肩膀一起裁出来当参考图。"""
    info = media.probe(video)
    w, h = info["width"], info["height"]
    cands = [s for s in shots if s.get("who") == [pid]] or [s for s in shots if pid in (s.get("who") or [])]
    for s in sorted(cands, key=lambda s: -(s["end"] - s["start"])):
        for frac in (0.5, 0.3, 0.7):
            t = s["start"] + (s["end"] - s["start"]) * frac
            fr = _frame(video, w, h, t)
            if fr is None:
                continue
            faces = detect(fr)
            if not faces:
                continue
            x, y, fw, fh = (int(v) for v in max(faces, key=lambda r: r[2] * r[3])[:4])
            if fw < w * 0.08:
                continue
            cx, cy = x + fw / 2, y + fh / 2
            side = max(fw, fh) * 2.6
            x0, y0 = int(max(0, cx - side / 2)), int(max(0, cy - side * 0.45))
            x1, y1 = int(min(w, cx + side / 2)), int(min(h, cy + side * 0.55))
            out.parent.mkdir(parents=True, exist_ok=True)
            media.ff("-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                     "-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0},scale='max(512,iw)':-2", "-q:v", "2", str(out))
            return True
    return False


# ---------------- 锁脸合成（11-23）----------------
# 用户：FaceFusion 侧脸效果不好，不能把侧脸换成不能用的。所以按每张脸转头的程度决定用不用换过的脸：
# 偏转指标 = 鼻尖离两眼中点的横向距离 / 两眼间距（正脸约 0，转 30° 约 0.3，45° 约 0.5）。
YAW_FULL = 0.22       # 不超过它：整张用换过的脸
YAW_ZERO = 0.38       # 超过它：保留 H3 原样；中间按比例渐变
MIN_SIM = 0.15        # H3 拍出来的脸和你的照片至少这么像才算「要换的那个人」（防止换到路人）


def _yaw(det) -> float:
    import numpy as np
    lm = np.asarray(det[4:14], dtype="float32").reshape(5, 2)    # YuNet：右眼、左眼、鼻尖、右嘴角、左嘴角
    v = lm[1] - lm[0]
    eye = float(np.linalg.norm(v)) + 1e-6
    # 只算鼻尖沿「两眼连线」方向的偏移。歪头时两眼连线跟着转，鼻尖仍在中线上 → 不会被当成侧脸
    return abs(float(np.dot(lm[2] - (lm[0] + lm[1]) / 2, v / eye))) / eye


_SWS = "accurate_rnd+full_chroma_int+full_chroma_inp"


def _frames_cm(video: Path, w: int, h: int):
    """锁脸合成专用的读帧：精确取整（11-24 实测：ffmpeg 默认转 RGB 和转回 YUV 都截断取整，
    一来一回整体暗约 2 级；两头都用 accurate_rnd 后偏差 0.05 级）。色彩矩阵按片子自己的标记，不强改。"""
    import numpy as np
    args = [paths.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", str(video),
            "-vf", f"scale=flags={_SWS}",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, creationflags=media.NOWIN)
    size = w * h * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
    finally:
        p.stdout.close()
        p.kill()
        p.wait()


def lock_composite(h3: Path, ff: Path, out: Path, photo: Path, others: list[Path] | None = None) -> dict:
    """h3 = H3 原片（已贴好声音），ff = 整段换过脸的版本；逐帧只把「要换的人、且不是大侧脸」那块用 ff 的，其余用 h3。
    others = 不该换的人的参考图（别的换上的人、原片里保持原样的人），和他们更像的脸不动。"""
    import cv2
    import numpy as np
    me = photo_embedding(photo)
    if me is None:
        raise RuntimeError("照片里找不到脸")
    refs = [e for e in (photo_embedding(p) for p in (others or []) if Path(p).exists()) if e is not None]
    info = media.probe(h3)
    w, h, fps = info["width"], info["height"], info["fps"] or 24
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + "_合成.mp4")
    enc = subprocess.Popen([paths.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                            "-i", str(h3), "-map", "0:v:0", "-map", "1:a:0?",
                            "-vf", f"scale=flags={_SWS},format=yuv420p", "-c:v", "libx264", "-crf", "17",
                            "-preset", "medium",
                            # 原来 -c:a copy + -shortest 会按声音长度截掉结尾几帧；改成声音补静音到画面长度
                            "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest",
                            "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE, creationflags=media.NOWIN)
    tracks: list[dict] = []           # 上一帧的脸：中心、宽、平滑后的权重（让换/不换之间渐变，不闪）
    n = locked = skipped_side = 0
    try:
        ffi = _frames_cm(ff, w, h)
        for fa in _frames_cm(h3, w, h):
            fb = next(ffi, None)
            if fb is None:
                fb = fa                       # 引擎那条短了：剩下的帧用 H3 原帧
            n += 1
            alpha = np.zeros((h, w), np.float32)
            new_tracks, used = [], set()
            for det in detect(fa):
                x, y, fw, fh = (float(v) for v in det[:4])
                cx, cy = x + fw / 2, y + fh / 2
                e = embed(fa, det)
                sim = similar(e, me)
                rs = [similar(e, r) for r in refs]
                # 确认是别人（更像原片里保持原样的人 / 别的换上的人，或几乎不像你的照片）→ 硬排除，
                # 不能被上一帧同位置的人带着平滑进来；只是这一帧判不准的，照旧平滑过渡，免得目标人物闪
                other = (bool(rs) and max(rs) > sim) or sim < 0.05
                target = not other and sim >= MIN_SIM
                yaw = _yaw(det)
                wt = float(np.clip((YAW_ZERO - yaw) / (YAW_ZERO - YAW_FULL), 0, 1)) if target else 0.0
                cand = [i for i, t in enumerate(tracks) if i not in used
                        and abs(t["cx"] - cx) < fw * 0.6 and abs(t["cy"] - cy) < fh * 0.6]
                if cand:
                    used.add(cand[0])
                    if not other:
                        wt = 0.5 * tracks[cand[0]]["w"] + 0.5 * wt
                new_tracks.append({"cx": cx, "cy": cy, "fw": fw, "fh": fh, "w": 0.0 if other else wt})
                if target and wt < 0.5:
                    skipped_side += 1
            # 这一帧没检出的脸（比如转成全侧脸 YuNet 认不出）：沿用上一帧的位置，权重每帧减半，渐变回 H3 原样
            for i, t in enumerate(tracks):
                if i not in used and t["w"] > 0.05:
                    new_tracks.append(dict(t, w=t["w"] * 0.5))
            tracks = new_tracks
            changed = False
            for t in tracks:
                cx, cy, fw, fh, wt = t["cx"], t["cy"], t["fw"], t["fh"], t["w"]
                if wt <= 0.01:
                    continue
                # 换脸改动的区域：脸框放大 1.6 倍内，ff 和 h3 有差别的地方（+ 脸中心椭圆兜底），羽化边缘
                s = 1.6
                x0, y0 = int(max(0, cx - fw * s / 2)), int(max(0, cy - fh * s / 2))
                x1, y1 = int(min(w, cx + fw * s / 2)), int(min(h, cy + fh * s / 2))
                d = np.abs(fb[y0:y1, x0:x1].astype(np.int16) - fa[y0:y1, x0:x1].astype(np.int16)).max(axis=2)
                m = (d > 6).astype(np.uint8) * 255
                k = max(3, int(fw * 0.06) | 1)
                m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
                core = np.zeros_like(m)
                cv2.ellipse(core, (int(cx - x0), int(cy - y0)), (int(fw * 0.42), int(fh * 0.55)), 0, 0, 360, 255, -1)
                if wt > 0.5 and core.any() and float((d[core > 0] > 6).mean()) > 0.2:
                    changed = True            # 引擎确实在这张脸上动了（不是只算遮罩）
                m = np.maximum(m, core)
                b = max(3, int(fw * 0.12) | 1)
                m = cv2.GaussianBlur(m, (b, b), 0).astype(np.float32) / 255.0
                alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], m * wt)
            if changed:
                locked += 1
            a = alpha[..., None]
            frame = (fa.astype(np.float32) * (1 - a) + fb.astype(np.float32) * a).astype(np.uint8)
            enc.stdin.write(frame.tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
    if enc.returncode != 0 or not tmp.exists():
        raise RuntimeError("锁脸合成编码失败")
    os.replace(tmp, out)
    return {"frames": n, "locked": locked, "side_kept": skipped_side}
