"""设置和作品的存取。每个作品一个文件夹，project.json 里只存相对路径，拷走即备份。"""
from __future__ import annotations

import json
import os
import random
import shutil
import string
import threading
import time
from pathlib import Path
from typing import Callable

from . import paths, pricing

VERSION = "0.1.0"

DEFAULT_SETTINGS = {"tier": pricing.DEFAULT_TIER, "takes": 1, "budget": 20.0, "auto_analyze": True,
                    "music": "auto", "mock": False, "face_lock": True,   # face_lock：拍完用包内换脸引擎锁脸（11-23）
                    "vision": "minimax"}   # vision：拉片看片用 minimax / gpt（gpt 要填 OpenAI 密钥，11-25）


# ---------------- 设置 ----------------
_SET_LOCK = threading.Lock()


def settings() -> dict:
    p = paths.SETTINGS / "设置.json"
    s = dict(DEFAULT_SETTINGS)
    if p.exists():
        try:
            s.update(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            pass
    if s.get("tier") not in pricing.TIERS:
        s["tier"] = pricing.DEFAULT_TIER
    if s.get("vision") not in ("minimax", "gpt"):
        s["vision"] = "minimax"
    return s


def save_settings(upd: dict) -> dict:
    with _SET_LOCK:
        s = settings()
        for k in DEFAULT_SETTINGS:
            if k in upd and upd[k] is not None:
                s[k] = upd[k]
        s["takes"] = int(min(4, max(1, int(s["takes"]))))
        s["budget"] = float(max(0, float(s["budget"])))
        paths.SETTINGS.mkdir(parents=True, exist_ok=True)
        _atomic(paths.SETTINGS / "设置.json", s)
        return s


def save_key(key: str) -> None:
    paths.SETTINGS.mkdir(parents=True, exist_ok=True)
    (paths.SETTINGS / "MiniMax密钥.txt").write_text(key.strip(), encoding="utf-8")


# ---------------- 作品 ----------------
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock(pid: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(pid, threading.RLock())


def _atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S-") + "".join(random.choices(string.ascii_lowercase + string.digits, k=4))


def pdir(pid: str) -> Path:
    if not pid or any(c in pid for c in "\\/:.") :
        raise KeyError(pid)
    return paths.WORKS / pid


def exists(pid: str) -> bool:
    try:
        return (pdir(pid) / "project.json").exists()
    except KeyError:
        return False


def load(pid: str) -> dict:
    with _lock(pid):
        return json.loads((pdir(pid) / "project.json").read_text(encoding="utf-8"))


def save(p: dict) -> dict:
    with _lock(p["id"]):
        p["updated"] = time.time()
        _atomic(pdir(p["id"]) / "project.json", p)
        return p


def update(pid: str, fn: Callable[[dict], object]) -> dict:
    """加锁读-改-写。fn 原地改 p。"""
    with _lock(pid):
        p = load(pid)
        fn(p)
        return save(p)


def create(name: str) -> dict:
    pid = new_id()
    d = pdir(pid)
    for sub in ("原片", "拉片", "素材", "参考", "拍次", "导出"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    s = settings()
    p = {"id": pid, "name": name, "created": time.strftime("%Y-%m-%d %H:%M"), "version": VERSION,
         "stage": "upload", "source": None, "window": None,
         "jobs": {"analyze": {"status": "idle", "step": "", "progress": 0, "error": None}},
         "analysis": None, "cast": {}, "scene": None, "prompt": {"custom": False, "text": ""},
         "takes": [], "chosen": None, "exports": [], "ledger": [], "uploads": {}, "nonces": [],
         "budget": s["budget"], "sample": False}
    d.mkdir(parents=True, exist_ok=True)
    _atomic(d / "project.json", p)
    return p


def all_ids() -> list[str]:
    if not paths.WORKS.exists():
        return []
    ids = [d.name for d in paths.WORKS.iterdir() if d.is_dir() and (d / "project.json").exists()]
    return sorted(ids, reverse=True)


def trash(pid: str) -> None:
    d = pdir(pid)
    dest = paths.WORKS / "回收站"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(d), str(dest / pid))


def spent(p: dict) -> float:
    return round(sum(e.get("actual") or 0 for e in p.get("ledger", [])), 2)


def reserved(p: dict) -> float:
    """还在拍、没出结果的拍次按报价预留。"""
    return round(sum(t.get("quote") or 0 for t in p.get("takes", [])
                     if t["status"] in ("submitting", "queued", "running", "downloading")), 2)


def ledger_add(p: dict, row: dict) -> None:
    row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), **row}
    p.setdefault("ledger", []).append(row)
    if row.get("actual"):
        paths.WORKS.mkdir(parents=True, exist_ok=True)
        f = paths.WORKS / "账本.csv"
        new = not f.exists()
        with open(f, "a", encoding="utf-8-sig") as fh:
            if new:
                fh.write("时间,作品,项目,任务号,实扣(元)\n")
            fh.write(f"{row['time']},{p['name']},{row.get('what', '')},{row.get('task_id', '')},{row['actual']}\n")


def total_spent() -> float:
    f = paths.WORKS / "账本.csv"
    if not f.exists():
        return 0.0
    s = 0.0
    for line in f.read_text(encoding="utf-8-sig").splitlines()[1:]:
        try:
            s += float(line.rsplit(",", 1)[1])
        except (ValueError, IndexError):
            pass
    return round(s, 2)
