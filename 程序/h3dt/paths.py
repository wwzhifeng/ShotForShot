"""产品目录约定：所有运行数据都在产品根目录内，路径由本文件位置推导，不写死盘符。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # 王知风H3导演台\
PROGRAM = ROOT / "程序"
WEB = PROGRAM / "web"
SETTINGS = Path(os.environ.get("H3DT_SETTINGS_DIR") or (ROOT / "设置"))
WORKS = Path(os.environ.get("H3DT_WORKS_DIR") or (ROOT / "作品"))
SAMPLES = ROOT / "示例"
RUNTIME = ROOT / "runtime"          # bat 要引用它，所以用 ASCII 名
CACHE = ROOT / "缓存"
LOGS = ROOT / "日志"
TEMP = CACHE / "temp"


def ensure_dirs() -> None:
    for d in (SETTINGS, WORKS, CACHE, LOGS, TEMP):
        d.mkdir(parents=True, exist_ok=True)


def tool(name: str) -> str:
    """找包内的 ffmpeg / ffprobe。开发时可用 H3DT_FFMPEG_DIR 指到项目内其他位置。"""
    dirs = []
    if os.environ.get("H3DT_FFMPEG_DIR"):
        dirs.append(Path(os.environ["H3DT_FFMPEG_DIR"]))
    dirs += [RUNTIME / "ffmpeg" / "bin", RUNTIME / "ffmpeg"]
    for d in dirs:
        p = d / f"{name}.exe"
        if p.exists():
            return str(p)
    raise FileNotFoundError(f"包内缺少 {name}.exe（应在 runtime\\ffmpeg\\bin）")


def rel(p: Path, base: Path) -> str:
    return p.resolve().relative_to(base.resolve()).as_posix()
