"""本机视频处理（全部用包内 ffmpeg，不花钱）：读信息、切镜头、抽帧、分离声音、去音轨、裁字幕区、截取。"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import paths

NOWIN = 0x08000000  # CREATE_NO_WINDOW


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout, creationflags=NOWIN,
                          encoding="utf-8", errors="replace")


def ff(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    p = _run([paths.tool("ffmpeg"), "-hide_banner", "-y", *args], timeout)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg 失败：" + (p.stderr or "")[-800:])
    return p


def probe(path: Path) -> dict:
    p = _run([paths.tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if p.returncode != 0:
        raise RuntimeError("读不出这个视频：" + (p.stderr or "")[-300:])
    j = json.loads(p.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        raise RuntimeError("文件里没有视频画面")
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    dur = float(j.get("format", {}).get("duration") or v.get("duration") or 0)
    return {"duration": round(dur, 3), "width": w, "height": h, "fps": round(fps, 3),
            "vcodec": v.get("codec_name"), "has_audio": a is not None,
            "acodec": a.get("codec_name") if a else None,
            "size": int(j.get("format", {}).get("size") or 0)}


def scenes(path: Path, threshold: float = 0.30, min_gap: float = 0.25) -> list[float]:
    """用 ffmpeg 的场景检测找切点（秒）。不依赖 OpenCV，包不变大。"""
    p = _run([paths.tool("ffmpeg"), "-hide_banner", "-i", str(path), "-an",
              "-filter:v", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"], 600)
    cuts: list[float] = []
    for m in re.finditer(r"pts_time:([0-9.]+)", p.stderr or ""):
        t = float(m.group(1))
        if t > min_gap and (not cuts or t - cuts[-1] >= min_gap):
            cuts.append(round(t, 3))
    return cuts


def frame(path: Path, t: float, out: Path, width: int = 480) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1",
       "-vf", f"scale={width}:-2", "-q:v", "3", str(out))
    return out


def strip_frames(path: Path, out: Path, count: int, height: int = 120) -> Path:
    """时间线用的胶片条：等间隔抽 count 帧横向拼成一张图。"""
    info = probe(path)
    fps = max(count / max(info["duration"], 0.1), 0.05)
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-i", str(path), "-vf", f"fps={fps:.4f},scale=-2:{height},tile={count}x1", "-frames:v", "1",
       "-q:v", "4", str(out))
    return out


def extract_audio(path: Path, out: Path) -> Path:
    """给语音识别：16k 单声道 wav。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out))
    return out


def audio_ref(src: Path, out: Path, dur: float) -> Path:
    """「用原声」：截原片前 dur 秒的声音给 H3 当参考音频（官方要求 WAV/MP3、2~15 秒、≤15MB；48k 立体声 15 秒约 3MB）。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-i", str(src), "-t", f"{dur:.3f}", "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(out))
    return out


def put_audio(video: Path, audio: Path, out: Path, delay_ms: int = 0) -> Path:
    """把原声原样贴回成片：画面不重新编码；声音比画面短时补静音，不截画面。
    delay_ms > 0：原声整体往后挪（H3 照搬原声但晚了一点时，跟着它的嘴型走）；< 0：往前挪。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    if delay_ms > 0:
        af = f"adelay={delay_ms}:all=1,apad"
    elif delay_ms < 0:
        af = f"atrim=start={-delay_ms / 1000:.3f},asetpts=PTS-STARTPTS,apad"
    else:
        af = "apad"
    ff("-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
       "-af", af, "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    return out


def make_reference(src: Path, out: Path, start: float, dur: float, crop_bottom: float = 0.0,
                   crop_top: float = 0.0, max_long: int = 1280, erase_boxes: list | None = None) -> Path:
    """做参考片：截取 [start, start+dur]、去掉音轨、抹掉水印（不裁画面）、可裁掉上/下字幕区、转 H.264 25fps、限制尺寸（≤50MB）。
    erase_boxes：[[x, y, w, h], ...] 占画面比例。"""
    info = probe(src)
    w, h = info["width"], info["height"]
    graph = []
    cur = "[0:v]"
    for i, (bx, by, bw, bh) in enumerate(erase_boxes or []):
        # 先 delogo 抹字，再在同一块上叠一层强模糊，避免残留条纹被 AI 学去（11-22 实测 delogo 单用会留印子）
        x = max(1, int(bx * w))
        y = max(1, int(by * h))
        ww = max(8, min(int(bw * w), w - x - 2)) // 2 * 2
        hh = max(8, min(int(bh * h), h - y - 2)) // 2 * 2
        r = max(1, min(24, hh // 4 - 1, ww // 4 - 1))   # 色度平面只有一半大，半径要按 1/4 算
        graph.append(f"{cur}delogo=x={x}:y={y}:w={ww}:h={hh},split[m{i}][c{i}];"
                     f"[c{i}]crop={ww}:{hh}:{x}:{y},boxblur={r}:3[b{i}];[m{i}][b{i}]overlay={x}:{y}[v{i}]")
        cur = f"[v{i}]"
    vf = []
    if crop_bottom > 0 or crop_top > 0:
        keep = 1.0 - crop_bottom - crop_top
        ch = int(h * keep) // 2 * 2
        y = int(h * crop_top) // 2 * 2
        vf.append(f"crop={w}:{ch}:0:{y}")
        h = ch
    if max(w, h) > max_long:
        vf.append(f"scale='if(gt(iw,ih),{max_long},-2)':'if(gt(iw,ih),-2,{max_long})'")
    vf.append("fps=25")
    graph.append(f"{cur}{','.join(vf)}[out]")
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}", "-an",
       "-filter_complex", ";".join(graph), "-map", "[out]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out))
    return out


def trim(src: Path, out: Path, start: float, dur: float, keep_audio: bool = True) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"]
    args += (["-c:a", "aac", "-b:a", "160k"] if keep_audio else ["-an"])
    ff(*args, "-movflags", "+faststart", str(out))
    return out


def ratio_of(w: int, h: int) -> str:
    """H3 支持的比例里挑最接近的。"""
    opts = {"21:9": 21 / 9, "16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0, "3:4": 3 / 4, "9:16": 9 / 16}
    r = w / h if h else 1
    return min(opts, key=lambda k: abs(opts[k] - r))


def tc(t: float) -> str:
    """秒 → MM:SS.mmm（H3 切镜时间码格式）。"""
    t = max(0.0, t)
    m = int(t // 60)
    return f"{m:02d}:{t - m * 60:06.3f}"
