"""可选：用用户自己的 OpenAI 密钥让 GPT 看片写拉片表（给有 OpenAI 赠送额度的人用）。
实测 7 条原片：GPT-6.2-astra 比 M3.1-Flash 人物细节更准、水印框得更全。
- 密钥在 设置\\OpenAI密钥.txt，和 MiniMax 密钥一样只在本机；
- 国内连 OpenAI 要代理：先走 Windows 系统代理（Clash 等开「系统代理」），连不上再直连（TUN 模式）；
- 出任何错都抛 GPTError（带一句中文原因），拉片时自动改用 MiniMax，流程不断。"""
from __future__ import annotations

import re
import urllib.request

import httpx

from . import paths

BASE = "https://api.openai.com/v1"
KEY_FILE = "OpenAI密钥.txt"
# 按新旧、档次从高到低；这把密钥有哪个就用哪个（11-25 实测用的是 gpt-6.2-astra）
PREFER = ["gpt-6.2-astra", "gpt-6.2-sol", "gpt-6.1-sol", "gpt-6-astra", "gpt-6-sol", "gpt-5.5", "gpt-5.4",
          "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"]
_MODEL: dict[str, str] = {}


class GPTError(Exception):
    def __init__(self, why: str):
        self.why = why
        super().__init__(why)


def read_key() -> str:
    p = paths.SETTINGS / KEY_FILE
    if not p.exists():
        return ""
    return re.sub(r"\s+", "", p.read_text(encoding="utf-8-sig", errors="ignore"))


def key_tail() -> str:
    k = read_key()
    return k[-4:] if len(k) >= 8 else ""


def save_key(key: str) -> None:
    paths.SETTINGS.mkdir(parents=True, exist_ok=True)
    (paths.SETTINGS / KEY_FILE).write_text(key.strip(), encoding="utf-8")


def _proxies() -> list[str | None]:
    """先试 Windows 系统代理，再直连（启动 bat 会清掉代理环境变量，本机服务和 MiniMax 要直连）。"""
    out: list[str | None] = []
    try:
        reg = urllib.request.getproxies_registry()   # Windows「系统代理」（Clash 等）
        r = reg.get("https") or reg.get("http")
        if r and r not in out:
            out.append(r if "://" in r else "http://" + r)
    except Exception:  # noqa: BLE001
        pass
    out.append(None)
    return out


def _why(r: httpx.Response) -> str:
    try:
        e = r.json().get("error") or {}
    except ValueError:
        e = {}
    code = str(e.get("code") or e.get("type") or "")
    if r.status_code == 401:
        return "OpenAI 密钥不对或已失效"
    if code == "insufficient_quota":
        return "OpenAI 额度用完了"
    if code == "unsupported_country_region_territory" or r.status_code == 403:
        return "OpenAI 不对你现在的网络地区开放，要开代理"
    if r.status_code == 429:
        return "OpenAI 太忙（限流）"
    if r.status_code == 404:
        return "这把 OpenAI 密钥用不了看图的模型"
    return f"OpenAI 出错（{r.status_code}{' ' + code if code else ''}）"


class GPT:
    def __init__(self, key: str | None = None, timeout: float = 300):
        self.key = key if key is not None else read_key()
        self.timeout = timeout
        self.model = ""

    def _req(self, method: str, path: str, **kw) -> dict:
        if not self.key:
            raise GPTError("还没填 OpenAI 密钥")
        last = "连不上 OpenAI（国内要开代理）"
        for proxy in _proxies():
            try:
                with httpx.Client(base_url=BASE, timeout=self.timeout, trust_env=False, proxy=proxy,
                                  headers={"Authorization": f"Bearer {self.key}"}) as c:
                    r = c.request(method, path, **kw)
            except (httpx.TransportError, httpx.TimeoutException, ImportError, ValueError):
                continue   # 这条路不通（或代理格式用不了，如没装 socks 支持），换下一条（代理 → 直连）
            if r.status_code >= 400:
                last = _why(r)
                if r.status_code == 403:
                    continue   # 地区不开放：换条路再试
                raise GPTError(last)
            return r.json()
        raise GPTError(last)

    def pick_model(self) -> str:
        if self.key in _MODEL:
            self.model = _MODEL[self.key]
            return self.model
        ids = {m.get("id") for m in self._req("GET", "/models").get("data") or []}
        m = next((x for x in PREFER if x in ids), None)
        if not m:
            raise GPTError("这把 OpenAI 密钥里没有能看图的 GPT 模型")
        _MODEL[self.key] = self.model = m
        return m

    def chat_json(self, messages: list, max_tokens: int = 30000) -> tuple[str, dict]:
        self.pick_model()
        body = {"model": self.model, "messages": messages, "response_format": {"type": "json_object"},
                "max_completion_tokens": max_tokens, "reasoning_effort": "high"}
        try:
            j = self._req("POST", "/chat/completions", json=body)
        except GPTError as e:
            if "400" not in e.why:
                raise
            body.pop("reasoning_effort")   # 有的模型不认这个参数
            j = self._req("POST", "/chat/completions", json=body)
        text = (j.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        if not text:
            raise GPTError("GPT 没返回内容")
        return text, j.get("usage") or {}
