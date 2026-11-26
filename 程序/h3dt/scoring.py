"""挑片打分（本机切镜免费 + 语音识别约 1 分钱/条）：切点误差、台词核对、有没有带出原台词。"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from . import media, pricing
from .minimax import MiniMax

PUNCT = r"[\s，。！？、,.!?…“”\"'：:；;（）()\-—]"


def norm(s: str) -> str:
    return re.sub(PUNCT, "", s or "")


def cut_error(src_cuts: list[float], out_cuts: list[float], tol: float = 1.0) -> dict:
    rows, errs = [], []
    used: set[int] = set()
    for c in src_cuts:
        best, bi = None, None
        for i, o in enumerate(out_cuts):
            if i in used:
                continue
            d = abs(o - c)
            if best is None or d < best:
                best, bi = d, i
        if best is not None and best <= tol:
            used.add(bi)
            rows.append({"src": c, "out": out_cuts[bi], "diff": round(out_cuts[bi] - c, 3)})
            errs.append(best)
        else:
            rows.append({"src": c, "out": None, "diff": None})
    extra = [o for i, o in enumerate(out_cuts) if i not in used]
    missing = sum(1 for r in rows if r["out"] is None)
    mean = round(sum(errs) / len(errs), 3) if errs else None
    return {"rows": rows, "extra": extra, "missing": missing, "mean": mean}


def line_check(expected: list[str], heard: list[dict], original: list[str] | None = None) -> dict:
    heard_txt = norm("".join(h.get("text", "") for h in heard))
    rows = []
    for e in expected:
        ne = norm(e)
        if not ne:
            continue
        m = difflib.SequenceMatcher(None, ne, heard_txt)
        blk = m.find_longest_match(0, len(ne), 0, len(heard_txt))
        # 用滑窗找最像的一段
        best = 0.0
        L = len(ne)
        for i in range(0, max(1, len(heard_txt) - L + 1)):
            r = difflib.SequenceMatcher(None, ne, heard_txt[i:i + L + 2]).ratio()
            best = max(best, r)
        if not heard_txt:
            best = 0.0
        # 语音识别常把「了/啦」这类字听错，短句错一个字也算对上
        rows.append({"text": e, "match": round(best, 2), "ok": best >= 0.75, "longest": blk.size})
    leak = 0.0
    for o in original or []:
        no = norm(o)
        if no and no not in [norm(e) for e in expected]:
            leak = max(leak, difflib.SequenceMatcher(None, no, heard_txt).ratio() if heard_txt else 0.0)
    return {"rows": rows, "ok": sum(1 for r in rows if r["ok"]), "total": len(rows), "heard": heard_txt,
            "original_leak": round(leak, 2)}


def score(cuts: dict, lines: dict) -> int:
    s = 100.0
    if cuts["mean"] is not None:
        s -= min(30, cuts["mean"] * 40)
    s -= cuts["missing"] * 12 + len(cuts["extra"]) * 5
    if lines["total"]:
        s -= (lines["total"] - lines["ok"]) * 12
    s -= lines.get("original_leak", 0) > 0.6 and 15 or 0
    return int(max(0, min(100, round(s))))


def audio_sync(ref_audio: Path, h3_video: Path) -> dict | None:
    """「用原声」时核对口型（本机，不花钱）：把 H3 自己出的声音和原声比。照搬且对齐（相关 ≥0.85、偏移 0）
    说明嘴型就是跟着原声做的；H3 自己重新念了一遍时嘴型跟的是它自己的节奏，贴回原声会差零点几秒。
    11-23 实测：照着拍 0.993/0ms（嘴和原片的嘴同步）；动作照抄一条 0.036、它自己的声音晚 0.41 秒（嘴晚约 0.36 秒）。"""
    import subprocess
    import numpy as np
    from . import paths

    def env(path: Path):
        raw = subprocess.run([paths.tool("ffmpeg"), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "-"], capture_output=True, creationflags=media.NOWIN).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32)
        k = len(a) // 160                                     # 10 毫秒一格的音量曲线
        return np.sqrt((a[:k * 160].reshape(k, 160) ** 2).mean(1) + 1e-6)

    ea, eb = env(ref_audio), env(h3_video)
    n = min(len(ea), len(eb))
    if n < 100 or ea[:n].std() == 0 or eb[:n].std() == 0:
        return None
    za = (ea[:n] - ea[:n].mean()) / ea[:n].std()
    zb = (eb[:n] - eb[:n].mean()) / eb[:n].std()

    def c(L: int) -> float:
        return float(np.mean(za[max(0, L):n + min(0, L)] * zb[max(0, -L):n - max(0, L)]))
    best = max(range(-60, 61), key=c)
    c0 = c(0)
    # lag_ms > 0：H3 自己的声音比原声晚
    return {"corr": round(c0, 3), "lag_ms": -best * 10, "best": round(c(best), 3), "ok": c0 >= 0.85}


def evaluate(client: MiniMax | None, video: Path, src_cuts: list[float], expected: list[str],
             original: list[str] | None, work: Path) -> dict:
    out_cuts = media.scenes(video)
    c = cut_error(src_cuts, out_cuts)
    cost = 0.0
    heard: list[dict] = []
    if client and expected and media.probe(video)["has_audio"]:
        wav = media.extract_audio(video, work / (video.stem + "_声音.wav"))
        try:
            from .analyze import words_to_lines
            j = client.asr(wav, level="word")
            segs = j.get("segments") or []
            heard = words_to_lines(segs) if segs and max(len(s.get("text", "")) for s in segs) <= 4 else segs
            cost = pricing.asr_cost(float(j.get("duration") or 0))
        except Exception:  # noqa: BLE001  只有音乐没人声时官方会报错（实测 1041），按没听到台词算
            heard = []
    l = line_check(expected, heard, original)
    segs = [{"start": h.get("start"), "end": h.get("end"), "text": h.get("text", "")} for h in heard]
    return {"cuts": c, "out_cuts": out_cuts, "lines": l, "score": score(c, l), "cost": cost, "segments": segs}
