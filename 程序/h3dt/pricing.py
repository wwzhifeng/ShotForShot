"""官方价（元/秒，2026-11-20 定价页）。产品不给 480P（画质太低，换人不值得花这个钱）。
参考视频按「秒数 × 输出档单价」收；参考图每次前 5 张免费（Lite 超出 0.13，其余 0.20）；参考音频免费。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    id: str
    name: str
    hint: str
    model: str
    resolution: str
    per_sec: float
    extra_img: float


# 11-22 实测：复刻换人只有 MiniMax-H3 做得到；Lite、Highspeed 768P 都会把脸拉回原片的人 → 不给用户选
TIERS: dict[str, Tier] = {
    "h3-768": Tier("h3-768", "标准", "推荐，换人稳，性价比最高", "MiniMax-H3", "768P", 0.50, 0.20),
    "h3-2k": Tier("h3-2k", "高清", "2K 直出，画面更细，贵六成", "MiniMax-H3", "2K", 0.80, 0.20),
}
DEFAULT_TIER = "h3-768"

# 只给开发测试用的档位（产品界面不出现）
TEST_TIERS = {
    "lite-480": Tier("lite-480", "测试", "", "MiniMax-H3-Lite", "480P", 0.16, 0.13),
    "lite-768": Tier("lite-768", "测试", "", "MiniMax-H3-Lite", "768P", 0.26, 0.13),
}

ASR_PER_HOUR = 2.50          # 语音识别 元/小时
FLASH_IN, FLASH_OUT = 1.00, 4.00   # M3.1-Flash 元/百万 tokens


def tier(tid: str) -> Tier:
    return TIERS.get(tid) or TEST_TIERS[tid]


def video_quote(tid: str, out_sec: int, ref_video_sec: float = 0, ref_images: int = 0) -> dict:
    t = tier(tid)
    out = round(out_sec * t.per_sec, 2)
    ref = round(ref_video_sec * t.per_sec, 2)
    img = round(max(0, ref_images - 5) * t.extra_img, 2)
    return {"tier": t.id, "model": t.model, "resolution": t.resolution, "per_sec": t.per_sec,
            "out_sec": out_sec, "out": out, "ref_sec": round(ref_video_sec, 2), "ref": ref,
            "images": ref_images, "img": img, "total": round(out + ref + img, 2)}


def takes_quote(tid: str, out_sec: int, ref_video_sec: float, ref_images: int, takes: int) -> dict:
    one = video_quote(tid, out_sec, ref_video_sec, ref_images)
    one["takes"] = takes
    one["sum"] = round(one["total"] * takes, 2)
    return one


def asr_cost(seconds: float) -> float:
    return round(seconds / 3600 * ASR_PER_HOUR, 4)


def tokens_cost(usage: dict) -> float:
    pin = usage.get("prompt_tokens", 0) or 0
    pout = usage.get("completion_tokens", 0) or 0
    return round((pin * FLASH_IN + pout * FLASH_OUT) / 1e6, 4)


def actual_from_usage(tid: str, usage: dict) -> float:
    """按任务返回的 usage 算实扣（秒数 × 单价 + 超额参考图）。"""
    t = tier(tid)
    secs = usage.get("total_seconds")
    if secs is None:
        secs = (usage.get("input_seconds") or 0) + (usage.get("output_seconds") or 0)
    img = max(0, (usage.get("input_image_count") or 0) - 5) * t.extra_img
    return round(secs * t.per_sec + img, 2)
