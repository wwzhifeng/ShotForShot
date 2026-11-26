"""MiniMax 官方接口（国内站）。只做协议，不管业务；所有错误统一抛 ApiError。

字段名按 2026-11-22 读的官方文档：
  创建  POST /v2/video_generation            -> {"task_id"}
  查询  GET  /v2/query/video_generation/{id}  -> {"task": {...}}
  列表  GET  /v2/query/video_generation       -> {"items", "total"}
  取消  DELETE /v2/video_generation/{id}
  润色  POST /v2/h3_context_ir                -> {"task_id"}，结果在查询的 content.prompt
  上传  POST /v1/files/upload                 -> {"file": {"file_id"}, "base_resp"}
  识别  POST /v1/speech_to_text (asr-1.0)
  对话  POST /v1/chat/completions（M3.1-Flash 可看视频）
v2 报错：HTTP 状态码 + {"type":"error","error":{"type","message":"... (内部码)"}}
"""
from __future__ import annotations

import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any

import httpx

from .errors import HTTP_FALLBACK, ApiError, NetError, parse_code
from . import paths

BASE = "https://api.minimax.cn"
KEY_FILE = "MiniMax密钥.txt"


def read_key() -> str:
    p = paths.SETTINGS / KEY_FILE
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8-sig", errors="ignore").strip()


def key_tail() -> str:
    k = read_key()
    return k[-4:] if len(k) >= 8 else ""


class MiniMax:
    def __init__(self, key: str | None = None, timeout: float = 120):
        self.key = key if key is not None else read_key()
        # 国内接口直连：不读系统代理（用户开着 VPN 也不绕出去）
        self.http = httpx.Client(base_url=BASE, timeout=timeout, trust_env=False,
                                 headers={"Authorization": f"Bearer {self.key}"})

    # ---------- 底层 ----------
    def _req(self, method: str, url: str, retries: int = 2, **kw) -> httpx.Response:
        if not self.key:
            raise ApiError("1004", "no key")
        last: Exception | None = None
        for i in range(retries + 1):
            try:
                r = self.http.request(method, url, **kw)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                last = NetError(str(e))
                if method == "POST" and url.startswith("/v2/video_generation"):
                    raise last  # 花钱接口不盲目重发：网络断时可能已提交，交给对账处理
                time.sleep(2 * (i + 1))
                continue
            if r.status_code >= 400:
                err = self._error(r)
                if err.code in ("1002", "1039") and i < retries:
                    time.sleep(5 * (i + 1))
                    continue
                raise err
            return r
        raise last or NetError("unknown")

    @staticmethod
    def _error(r: httpx.Response) -> ApiError:
        raw = r.text[:500]
        code = None
        try:
            j = r.json()
            msg = (j.get("error") or {}).get("message") or ""
            code = parse_code(msg)
            br = j.get("base_resp") or {}
            if not code and br.get("status_code"):
                code = str(br["status_code"])
        except ValueError:
            pass
        return ApiError(code or HTTP_FALLBACK.get(r.status_code, str(r.status_code)), raw, r.status_code)

    @staticmethod
    def _check_base(j: dict) -> dict:
        br = j.get("base_resp") or {}
        if br and br.get("status_code", 0) != 0:
            raise ApiError(str(br.get("status_code")), br.get("status_msg", ""))
        return j

    # ---------- 视频 ----------
    def create_video(self, body: dict) -> str:
        r = self._req("POST", "/v2/video_generation", json=body, retries=0)
        return str(r.json()["task_id"])

    def context_ir(self, body: dict) -> str:
        r = self._req("POST", "/v2/h3_context_ir", json=body, retries=0)
        return str(r.json()["task_id"])

    def query(self, task_id: str) -> dict:
        j = self._req("GET", f"/v2/query/video_generation/{task_id}").json()
        return j.get("task", j)

    def list_tasks(self, page_num: int = 1, page_size: int = 50, **filters) -> dict:
        params: dict[str, Any] = {"page_num": page_num, "page_size": page_size}
        for k, v in filters.items():
            params[f"filter.{k}"] = v
        return self._req("GET", "/v2/query/video_generation", params=params).json()

    def cancel(self, task_id: str) -> dict:
        return self._req("DELETE", f"/v2/video_generation/{task_id}").json()

    def wait(self, task_id: str, every: float = 10, limit: float = 1800, on_poll=None) -> dict:
        t0 = time.time()
        while True:
            t = self.query(task_id)
            if on_poll:
                on_poll(t)
            if t.get("status") in ("succeeded", "failed", "cancelled"):
                return t
            if time.time() - t0 > limit:
                return t
            time.sleep(every)

    def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with httpx.Client(timeout=300, trust_env=False, follow_redirects=True) as c, c.stream("GET", url) as r:
            if r.status_code >= 400:
                raise NetError(f"download {r.status_code}")
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
        tmp.replace(dest)
        return dest

    # ---------- 文件 ----------
    def upload(self, path: Path, purpose: str = "video_generation_input") -> str:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            # 文件名用 ASCII，避免服务端对中文文件名的编码问题
            files = {"file": (f"upload{path.suffix.lower()}", f, mime)}
            r = self._req("POST", "/v1/files/upload", data={"purpose": purpose}, files=files)
        j = self._check_base(r.json())
        return str(j["file"]["file_id"])

    # ---------- 语音识别 ----------
    def asr(self, audio: Path, language: str = "zh", level: str = "sentence") -> dict:
        with open(audio, "rb") as f:
            files = {"file": (f"audio{audio.suffix.lower()}", f, mimetypes.guess_type(audio.name)[0] or "audio/wav")}
            data = {"model": "asr-1.0", "response_format": "verbose_json", "timestamp_level": level}
            headers = {"language": language} if language else {}
            r = self._req("POST", "/v1/speech_to_text", data=data, files=files, headers=headers)
        return r.json()

    # ---------- 出图（H3-Image 官方接口）----------
    def images(self, prompt: str, aspect_ratio: str = "3:4", area: str = "2K", n: int = 1) -> tuple[list[str], dict]:
        body = {"model": "MiniMax-H3-Image", "prompt": prompt, "aspect_ratio": aspect_ratio, "area": area, "n": n,
                "response_format": "url", "output_format": "jpeg", "aigc_watermark": False}
        j = self._req("POST", "/v1/images/generations", json=body, retries=0, timeout=600).json()
        return [d["url"] for d in j.get("data", []) if d.get("url")], j.get("usage") or {}

    def image_edit(self, prompt: str, images: list[Path], aspect_ratio: str = "3:4", area: str = "2K",
                   n: int = 1) -> tuple[list[str], dict]:
        """图片编辑（官方 /v1/images/edits）：带 1~16 张参考图，列表顺序就是图1、图2…。
        接口不幂等：超时重试会再扣一次费，所以不自动重试。"""
        import base64
        refs = []
        for f in images:
            mime = {".png": "png", ".webp": "webp"}.get(Path(f).suffix.lower(), "jpeg")
            refs.append({"image_url": f"data:image/{mime};base64," + base64.b64encode(Path(f).read_bytes()).decode()})
        body = {"model": "MiniMax-H3-Image", "prompt": prompt, "images": refs, "aspect_ratio": aspect_ratio, "area": area,
                "n": n, "response_format": "url", "output_format": "jpeg", "aigc_watermark": False}
        j = self._req("POST", "/v1/images/edits", json=body, retries=0, timeout=600).json()
        bad = [d["error"] for d in j.get("data", []) if d.get("error")]
        if bad and not any(d.get("url") for d in j.get("data", [])):
            raise ApiError(str(bad[0].get("code", "")), str(bad[0].get("message", "")))
        return [d["url"] for d in j.get("data", []) if d.get("url")], j.get("usage") or {}

    # ---------- 文字 / 看片 ----------
    def chat(self, messages: list, model: str = "MiniMax-M3.1-Flash", json_mode: bool = False,
             max_tokens: int = 4000, temperature: float = 0.2) -> tuple[str, dict]:
        body: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens,
                                "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        j = self._check_base(self._req("POST", "/v1/chat/completions", json=body, timeout=300).json())
        msg = j["choices"][0]["message"]
        text = msg.get("content") or ""
        if isinstance(text, list):
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        if not text:
            raise ApiError("empty", f"empty content, finish={j['choices'][0].get('finish_reason')}")
        return text, j.get("usage") or {}


def mm(file_id: str) -> str:
    return f"mm_file://{file_id}"


def dumps(o: Any) -> str:
    return json.dumps(o, ensure_ascii=False, indent=2)
