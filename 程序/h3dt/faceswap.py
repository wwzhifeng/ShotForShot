"""锁脸：H3 拍完后用包内的 FaceFusion 引擎把脸再换一遍，像照片得多（实测 7 条：0.49~0.64 → 0.65~0.81）。
- 引擎在 产品根\\换脸引擎（随安装包分发，不在源码仓库里）；
- 有 N 卡用显卡（5 秒约 15~60 秒），没有就走 CPU（8 核约 1.4 秒/帧）；显卡跑失败自动改 CPU；
- 引擎在子进程里跑（自带 OpenCV 4 / onnxruntime-gpu / CUDA 库），不影响导演台主程序；
- 换脸模型仅限非商业用途，所以安装包仅供个人非商业使用。
只负责「整段都换一遍」；哪些帧、哪张脸用换过的，由 faces.lock_composite 决定（侧脸不用）。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from functools import lru_cache
from pathlib import Path

from . import media, paths

ENGINE = paths.ROOT / "换脸引擎"
BOOT = paths.PROGRAM / "faceswap_boot.py"
SWAPPER = "hyperswap_1b_256"
ENHANCER = "gfpgan_1.4"
SEC_PER_FRAME = {"cuda": 0.15, "cpu": 2.0}     # 报价页估时用（CPU 按普通电脑估，比开发机 8 核的 1.4 秒慢一些）


def available() -> bool:
    return (ENGINE / "facefusion.py").exists() and (ENGINE / ".assets" / "models" / f"{SWAPPER}.onnx").exists()


@lru_cache(maxsize=1)
def has_nvidia() -> bool:
    """有没有 N 卡：问显卡驱动自带的 nvidia-smi（装了 N 卡驱动就有，在 System32 里）。"""
    exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
    if not exe.exists():
        return False
    try:
        r = subprocess.run([str(exe), "-L"], capture_output=True, text=True, timeout=8, creationflags=media.NOWIN)
        return r.returncode == 0 and "GPU" in (r.stdout or "")
    except Exception:  # noqa: BLE001
        return False


def provider() -> str:
    return "cuda" if has_nvidia() else "cpu"


def estimate_seconds(dur: float, fps: float = 24.0) -> int:
    return int(dur * fps * SEC_PER_FRAME[provider()] + 30)


def _cmd(photo: Path, video: Path, out: Path, prov: str, tmp: Path) -> list[str]:
    (tmp / "temp").mkdir(parents=True, exist_ok=True)
    (tmp / "jobs").mkdir(parents=True, exist_ok=True)
    return [sys.executable, "-I", "-X", "utf8", str(BOOT), str(ENGINE), "headless-run",
            "--jobs-path", str(tmp / "jobs"), "--temp-path", str(tmp / "temp"),
            "-s", str(photo), "-t", str(video), "-o", str(out),
            "--processors", "face_swapper", "face_enhancer",
            # 引擎默认只认第 1 帧最大的脸（开头没脸就整段不换、开头是别人就换错）→ 全换，换谁由 faces.lock_composite 按相似度把关
            "--face-selector-mode", "many",
            # 手、话筒、产品挡在脸前时不被换上去的脸盖住（xseg 遮挡模型已在包里）
            "--face-mask-types", "box", "occlusion",
            "--face-swapper-model", SWAPPER, "--face-swapper-pixel-boost", "512x512",
            "--face-enhancer-model", ENHANCER, "--face-enhancer-blend", "80",
            "--output-video-quality", "90", "--execution-providers", prov, "--log-level", "info"]


def run(photo: Path, video: Path, out: Path) -> dict:
    """整段换脸。返回 {"provider", "seconds"}；失败抛 RuntimeError（调用方保留 H3 原片）。"""
    info = media.probe(video)
    frames = max(1, int(info["duration"] * (info["fps"] or 24)))
    env = dict(os.environ)
    env["H3DT_FFMPEG_DIR"] = str(Path(paths.tool("ffmpeg")).parent)
    env["PYTHONIOENCODING"] = "utf-8"
    tried = []
    # 每次运行用自己的临时目录：11-24 两个任务同时锁脸时，先跑完的清理共用的 temp，把另一个的中间帧删了
    tmp = paths.CACHE / "faceswap" / uuid.uuid4().hex[:8]
    for prov in (["cuda", "cpu"] if has_nvidia() else ["cpu"]):
        out.unlink(missing_ok=True)
        t0 = time.time()
        limit = frames * (3.0 if prov == "cuda" else 12.0) + 300
        try:
            r = subprocess.run(_cmd(photo, video, out, prov, tmp), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=limit, env=env, cwd=str(ENGINE), creationflags=media.NOWIN)
            ok = r.returncode == 0 and out.exists() and out.stat().st_size > 1000
            tail = ((r.stdout or "") + (r.stderr or ""))[-600:]
        except subprocess.TimeoutExpired:
            ok, tail = False, f"超时（{int(limit)} 秒）"
        _cleanup(tmp)
        if ok:
            return {"provider": prov, "seconds": int(time.time() - t0)}
        tried.append(f"{prov}: {tail}")
    raise RuntimeError("换脸引擎失败：" + " | ".join(tried)[-1200:])


def _cleanup(tmp: Path) -> None:
    """引擎的临时帧和任务记录（记录里带本机绝对路径）每次跑完就清掉，不越积越多。"""
    shutil.rmtree(tmp, ignore_errors=True)
