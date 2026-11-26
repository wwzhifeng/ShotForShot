"""模拟模式：接口长得和 MiniMax 一样，但一分钱不花。拍出来的「样片」是把原片段调个色，够走通整个流程。"""
from __future__ import annotations

import itertools
import json
import shutil
import threading
import time
from pathlib import Path

from . import media

_N = itertools.count(1)
_FILES: dict[str, Path] = {}
_TASKS: dict[str, dict] = {}
_LOCK = threading.Lock()


class MockMiniMax:
    mock = True

    def __init__(self, *_, **__):
        self.key = "mock"

    def upload(self, path: Path, purpose: str = "video_generation_input") -> str:
        fid = f"mock{next(_N)}"
        with _LOCK:
            _FILES[fid] = Path(path)
        return fid

    def create_video(self, body: dict) -> str:
        tid = f"mock-{int(time.time() * 1000)}-{next(_N)}"
        ref = next((c["video_url"]["url"] for c in body.get("content", []) if c.get("type") == "video_url"), "")
        with _LOCK:
            _TASKS[tid] = {"t0": time.time(), "ref": _FILES.get(ref.replace("mm_file://", "")),
                           "dur": body.get("duration", 5), "body": body}
        return tid

    def context_ir(self, body: dict) -> str:
        return self.create_video(body)

    def query(self, task_id: str) -> dict:
        t = _TASKS.get(task_id)
        if not t:
            return {"id": task_id, "status": "failed", "error": {"code": "1000", "message": "mock task lost"}}
        el = time.time() - t["t0"]
        if el < 3:
            st = "queued"
        elif el < 10:
            st = "running"
        else:
            st = "succeeded"
        r = {"id": task_id, "status": st, "created_at": int(t["t0"]), "updated_at": int(time.time())}
        if st == "succeeded":
            d = t["dur"]
            r["content"] = {"url": f"mock://{task_id}"}
            r["usage"] = {"total_seconds": d * 2, "input_seconds": d, "output_seconds": d, "input_image_count": 1}
        return r

    def list_tasks(self, *a, **k) -> dict:
        return {"items": [], "total": 0}

    def cancel(self, task_id: str) -> dict:
        t = _TASKS.get(task_id)
        if t and time.time() - t["t0"] < 3:
            _TASKS.pop(task_id, None)
            return {"task_id": task_id, "action": "cancelled", "status": "cancelled"}
        from .errors import ApiError
        raise ApiError("2013", "running task cannot be cancelled")

    def download(self, url: str, dest: Path) -> Path:
        tid = url.replace("mock://", "")
        t = _TASKS.get(tid) or {}
        src = t.get("src") or t.get("ref")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if t.get("exact") and src and Path(src).exists():
            shutil.copy2(src, dest)          # 示例作品：直接给事先真拍好的成片
        elif src and Path(src).exists():
            # 调一点色，加一个轻微缩放，看得出不是原片
            media.ff("-i", str(src), "-t", str(t.get("dur", 5)), "-vf", "eq=saturation=1.25:gamma=1.05,hue=h=12,scale=iw*1.0:ih*1.0",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-movflags", "+faststart", str(dest))
        else:
            media.ff("-f", "lavfi", "-i", f"testsrc2=size=432x768:rate=25:duration={t.get('dur', 5)}",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest))
        return dest

    def set_audio_source(self, task_id: str, src: Path, exact: bool = False) -> None:
        """模拟片的来源：默认拿原片段调色；exact=True 时原样给（示例作品里事先真拍好的成片）。"""
        with _LOCK:
            if task_id in _TASKS:
                _TASKS[task_id]["src"] = src
                _TASKS[task_id]["exact"] = exact

    def asr(self, audio: Path, language: str = "zh", level: str = "sentence") -> dict:
        hint = audio.with_suffix(".mock.json")
        if hint.exists():
            return json.loads(hint.read_text(encoding="utf-8"))
        return {"text": "", "duration": 0, "segments": []}

    def chat(self, messages, **kw):
        return json.dumps({"people": [{"id": "A", "desc": "原片主角（模拟模式没有真看片）", "desc_en": "the main performer", "gender": ""}],
                           "env": "（模拟）", "env_en": "", "style_en": "", "sound_en": "", "music_en": "N/A",
                           "subtitle": {"has": False, "pos": "none", "band": 0}, "watermark": False,
                           "speakers": {}, "shots": []}, ensure_ascii=False), {}

    def wait(self, task_id: str, every: float = 2, limit: float = 60, on_poll=None) -> dict:
        while True:
            t = self.query(task_id)
            if t["status"] in ("succeeded", "failed", "cancelled"):
                return t
            time.sleep(every)
