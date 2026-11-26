"""接口报错 → 中文说明 + 怎么办。界面只显示这里的文字，不显示英文原文。"""
from __future__ import annotations

import re

# 内部码 → (标题, 怎么办, 是否值得自动重试)
CODES: dict[str, tuple[str, str, bool]] = {
    "1000": ("MiniMax 服务器出错", "稍等一两分钟再点一次；没扣费。", True),
    "1001": ("请求超时", "网络或服务器慢，再点一次就行。", True),
    "1002": ("请求太快被限流", "程序会自动等一会儿再提交，不用管。", True),
    "1004": ("密钥不对", "到「设置」里重新粘贴 MiniMax 密钥（在开放平台「接口密钥」页新建）。", False),
    "2049": ("密钥不对", "到「设置」里重新粘贴 MiniMax 密钥（在开放平台「接口密钥」页新建）。", False),
    "1008": ("MiniMax 账户余额不够", "这次没扣费。去 MiniMax 开放平台「账户管理 → 余额」充值，回来点「继续」。", False),
    "1013": ("MiniMax 服务器出错", "稍等一两分钟再点一次。", True),
    "1026": ("描述里有敏感内容，被平台拦下", "改一下台词或拉片表里的动作描述（避开暴力、色情、政治、真实名人等），再拍。", False),
    "1027": ("生成结果被平台判定敏感", "这条没出片。改一下台词或动作描述再拍。", False),
    "1039": ("请求太快被限流", "程序会自动等一会儿再提交。", True),
    "1040": ("音频内容被平台拦下", "换一段参考音频，或者不用参考音频。", False),
    "1045": ("同时进行的任务太多", "程序会排队，等前面的拍完再自动提交。", True),
    "1046": ("参考图里的人被识别为身份声明问题", "换一张人物照片，或者别在台词、描述里写真实人名。", False),
    "2013": ("参数不对", "多半是素材规格不符（时长、画幅、格式）。如果提示「套餐不支持」，说明密钥是套餐密钥，要到开放平台「接口密钥」页新建按量付费的密钥。", False),
    "2022": ("这个模型没有权限", "确认密钥是按量付费的，并且账户开通了 H3。", False),
    "2053": ("积分不足", "去 MiniMax 开放平台充值。", False),
    "2061": ("你的套餐不支持这个模型", "H3 视频要用按量付费的密钥，到开放平台「接口密钥」页新建一个。", False),
    "2068": ("你的套餐不支持这个模型", "H3 视频要用按量付费的密钥，到开放平台「接口密钥」页新建一个。", False),
    "2064": ("MiniMax 平台忙", "稍后再试；程序会自动重试。", True),
    "2066": ("MiniMax 平台超时", "稍后再试；程序会自动重试。", True),
}

HTTP_FALLBACK = {
    400: "2013", 401: "1004", 402: "1008", 422: "1026", 429: "1002", 500: "1000", 529: "2064",
}


class ApiError(Exception):
    def __init__(self, code: str, raw: str = "", http: int | None = None):
        self.code = str(code)
        self.raw = raw
        self.http = http
        title, action, retry = CODES.get(self.code, ("MiniMax 返回了错误", "稍后再试；如果一直这样，把「日志」文件夹发给作者。", False))
        if self.code == "2013" and re.search(r"token ?plan|credit|套餐", raw, re.I):
            title, action, retry = CODES["2061"]
        self.title, self.action, self.retryable = title, action, retry
        super().__init__(f"{title}（{self.code}）")

    def to_dict(self) -> dict:
        return {"code": self.code, "title": self.title, "action": self.action, "retryable": self.retryable}


class NetError(ApiError):
    def __init__(self, raw: str = ""):
        super().__init__("net", raw)
        self.title = "连不上 MiniMax"
        self.action = "检查网络；如果开着代理或 VPN，可以先关掉再试。这次没扣费。"
        self.retryable = True


def parse_code(message: str) -> str | None:
    m = re.search(r"\((\d{3,5})\)\s*$", message or "")
    return m.group(1) if m else None
