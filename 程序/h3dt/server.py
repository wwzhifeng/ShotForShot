"""本机网页服务：只绑 127.0.0.1；所有接口靠启动时生成的 cookie 令牌校验，防别的网页替你花钱。"""
from __future__ import annotations

import logging
import os
import re
import secrets
import subprocess
from pathlib import Path
from urllib.parse import unquote

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import faceswap, gpt, paths, pricing, service, store
from .errors import ApiError
from .minimax import MiniMax, key_tail, read_key
from .service import UserError

log = logging.getLogger("h3dt")
TOKEN = secrets.token_urlsafe(24)
PORT = {"n": 0}


def _err(info: dict, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": info}, status_code=status)


def guard(fn):
    async def inner(request: Request):
        if request.cookies.get("h3dt") != TOKEN:
            return _err({"code": "auth", "title": "页面过期了", "action": "关掉这个网页，重新双击「启动导演台」。"}, 401)
        host_port = request.headers.get("host") or ""
        if host_port.split(":")[0] not in ("127.0.0.1", "localhost"):
            return _err({"code": "auth", "title": "不允许的访问来源"}, 403)
        # cookie 不分端口：本机别的网页服务（如其他端口上的网页）也能带着 cookie 发请求，所以再核来源必须是本页
        site = request.headers.get("sec-fetch-site")
        origin = request.headers.get("origin")
        if (site and site not in ("same-origin", "none")) or (origin and origin != f"http://{host_port}"):
            return _err({"code": "auth", "title": "不允许的访问来源"}, 403)
        try:
            return await fn(request)
        except UserError as e:
            return _err(e.info, 400)
        except ApiError as e:
            return _err(e.to_dict(), 400)
        except (KeyError, FileNotFoundError):
            return _err({"code": "notfound", "title": "找不到这个作品", "action": "回到作品列表重新打开。"}, 404)
        except Exception as e:  # noqa: BLE001
            log.exception("api error")
            return _err({"code": "local", "title": "程序出错了", "action": f"再试一次；还不行把「日志」文件夹发给作者。（{str(e)[:80]}）"}, 500)
    return inner


def state() -> dict:
    s = store.settings()
    return {"version": store.VERSION, "has_key": bool(read_key()), "key_tail": key_tail(), "mock": service.is_mock(),
            "has_okey": bool(gpt.read_key()), "okey_tail": gpt.key_tail(),
            "tiers": [{"id": t.id, "name": t.name, "hint": t.hint, "model": t.model, "resolution": t.resolution,
                       "per_sec": t.per_sec} for t in pricing.TIERS.values()],
            "settings": {k: s[k] for k in ("tier", "takes", "budget", "auto_analyze", "music", "mock", "face_lock", "vision")},
            "face_lock": {"available": faceswap.available(), "gpu": faceswap.has_nvidia() if faceswap.available() else False},
            "spent_total": store.total_spent()}


# ---------------- 页面 ----------------
async def index(request: Request):
    html = (paths.WEB / "index.html").read_text(encoding="utf-8")
    r = HTMLResponse(html, headers={"Cache-Control": "no-store"})
    r.set_cookie("h3dt", TOKEN, httponly=True, samesite="strict", path="/")
    return r


async def ping(request: Request):
    return JSONResponse({"ok": True, "app": "h3dt", "version": store.VERSION})


@guard
async def files(request: Request):
    pid = request.path_params["pid"]
    rel = unquote(request.path_params["path"])
    base = store.pdir(pid).resolve()
    f = (base / rel).resolve()
    if base not in f.parents or not f.is_file():
        return Response(status_code=404)
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


# ---------------- 设置 ----------------
@guard
async def get_state(request: Request):
    return JSONResponse(state())


@guard
async def post_settings(request: Request):
    body = await request.json()
    if body.get("key"):
        k = str(body["key"]).strip()
        if len(k) < 20:
            raise UserError("密钥看起来不完整", "到 MiniMax 开放平台「接口密钥」页复制完整的一串。")
        store.save_key(k)
    if body.get("okey"):
        k = re.sub(r"\s+", "", str(body["okey"]))
        if not k.startswith("sk-") or len(k) < 20:
            raise UserError("OpenAI 密钥看起来不对", "到 OpenAI 网站的「API keys」页复制完整的一串，以 sk- 开头。")
        gpt.save_key(k)
        body["vision"] = "gpt"   # 填了 OpenAI 密钥就默认用 GPT 看片
    if body.get("vision") == "gpt" and not gpt.read_key():
        raise UserError("还没填 OpenAI 密钥", "先在上面填 OpenAI 密钥，再选 GPT 看片。")
    store.save_settings(body)
    return JSONResponse(state())


@guard
async def test_key(request: Request):
    if not read_key():
        raise UserError("还没填密钥", "先把 MiniMax 密钥粘贴进来。")
    MiniMax().list_tasks(page_size=1)
    return JSONResponse({"ok": True})


@guard
async def test_okey(request: Request):
    """只查这把 OpenAI 密钥能不能连上、有哪个看图模型；不花钱。"""
    try:
        m = await run_in_threadpool(gpt.GPT(timeout=30).pick_model)
    except gpt.GPTError as e:
        raise UserError(e.why, "国内要先开代理（系统代理即可）；密钥要在 OpenAI 网站「API keys」页复制。") from None
    return JSONResponse({"ok": True, "model": m})


# ---------------- 作品 ----------------
@guard
async def list_projects(request: Request):
    out = []
    for pid in store.all_ids():
        try:
            out.append(service.summary(pid))
        except Exception:  # noqa: BLE001
            continue
    return JSONResponse(out)


@guard
async def create_project(request: Request):
    form = await request.form(max_part_size=600 * 1024 * 1024)
    up = form.get("file")
    if up is None:
        raise UserError("没收到视频文件")

    def chunks():
        while True:
            b = up.file.read(1 << 20)
            if not b:
                break
            yield b
    p = service.create_from_upload(up.filename, chunks(), form.get("name"))
    return JSONResponse(service.view(p))


@guard
async def sample(request: Request):
    return JSONResponse(service.view(service.open_sample()))


@guard
async def get_project(request: Request):
    return JSONResponse(service.view(store.load(request.path_params["pid"])))


@guard
async def delete_project(request: Request):
    service.delete_project(request.path_params["pid"])
    return JSONResponse({"ok": True})


@guard
async def open_folder(request: Request):
    body = await request.json()
    d = store.pdir(body["id"])
    sub = body.get("sub")
    if sub in ("导出", "拍次", "原片"):
        d = d / sub
    os.startfile(str(d))  # noqa: S606
    return JSONResponse({"ok": True})


# ---------------- 拉片 ----------------
@guard
async def window(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.set_window(request.path_params["pid"], float(b.get("start", 0)), int(b.get("dur", 15)))))


@guard
async def analyze(request: Request):
    pid = request.path_params["pid"]
    service.start_analyze(pid)
    return JSONResponse(service.view(store.load(pid)))


@guard
async def patch_analysis(request: Request):
    return JSONResponse(service.view(service.edit_analysis(request.path_params["pid"], await request.json())))


# ---------------- 换人 ----------------
@guard
async def cast(request: Request):
    form = await request.form(max_part_size=40 * 1024 * 1024)
    up = form.get("file")
    if up is None:
        raise UserError("没收到照片")
    data = await up.read()
    if form.get("angle"):          # 角度照：补在这个人的主照片后面（11-24）
        return JSONResponse(service.view(service.add_angle(request.path_params["pid"], form.get("person", "A"), up.filename, data)))
    return JSONResponse(service.view(service.set_cast(request.path_params["pid"], form.get("person", "A"), up.filename, data)))


@guard
async def del_cast(request: Request):
    return JSONResponse(service.view(service.del_cast(request.path_params["pid"], request.path_params["person"])))


@guard
async def del_angle(request: Request):
    return JSONResponse(service.view(service.del_angle(request.path_params["pid"], request.path_params["person"],
                                                       int(request.path_params["i"]))))


@guard
async def scene(request: Request):
    pid = request.path_params["pid"]
    if request.method == "DELETE":
        return JSONResponse(service.view(service.del_scene(pid)))
    form = await request.form(max_part_size=40 * 1024 * 1024)
    up = form.get("file")
    if up is None:
        raise UserError("没收到照片")
    return JSONResponse(service.view(service.set_scene(pid, up.filename, await up.read())))


# ---------------- 报价和开拍 ----------------
@guard
async def quote(request: Request):
    q = request.query_params
    s = store.settings()
    return JSONResponse(service.quote(request.path_params["pid"], q.get("tier") or s["tier"],
                                      int(q.get("takes") or s["takes"]), q.get("trial") in ("1", "true")))


@guard
async def set_mode(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.set_mode(request.path_params["pid"], str(b.get("mode")))))


@guard
async def set_swap(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.set_swap(request.path_params["pid"], str(b.get("swap")))))


@guard
async def set_audio(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.set_audio(request.path_params["pid"], str(b.get("audio")))))


@guard
async def set_prompt(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.set_prompt(request.path_params["pid"], b.get("text"), bool(b.get("reset")))))


@guard
async def shoot(request: Request):
    b = await request.json()
    p = service.shoot(request.path_params["pid"], b.get("tier") or store.settings()["tier"], int(b.get("takes") or 1),
                      bool(b.get("trial")), float(b.get("confirm_total") or 0), str(b.get("nonce") or ""),
                      b.get("mock") if "mock" in b else None)
    return JSONResponse(service.view(p))


@guard
async def cancel(request: Request):
    return JSONResponse(service.view(service.cancel_take(request.path_params["pid"], request.path_params["tid"])))


@guard
async def retry(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.retry_take(request.path_params["pid"], request.path_params["tid"],
                                                        float(b.get("confirm_total") or 0), str(b.get("nonce") or ""),
                                                        b.get("mock") if "mock" in b else None)))


@guard
async def choose(request: Request):
    b = await request.json()
    return JSONResponse(service.view(service.choose(request.path_params["pid"], b["take"])))


@guard
async def export(request: Request):
    b = await request.json()
    return JSONResponse(service.export(request.path_params["pid"], b["take"], bool(b.get("raw"))))


@guard
async def relock(request: Request):
    return JSONResponse(service.view(service.relock_take(request.path_params["pid"], request.path_params["tid"])))


@guard
async def refinish(request: Request):
    return JSONResponse(service.view(service.refinish_take(request.path_params["pid"], request.path_params["tid"])))


P = "/api/projects/{pid}"
routes = [
    Route("/", index),
    Route("/index.html", index),
    Route("/api/ping", ping),
    Route("/api/state", get_state),
    Route("/api/settings", post_settings, methods=["POST"]),
    Route("/api/settings/test-key", test_key, methods=["POST"]),
    Route("/api/settings/test-okey", test_okey, methods=["POST"]),
    Route("/api/projects", list_projects),
    Route("/api/projects", create_project, methods=["POST"]),
    Route("/api/projects/sample", sample, methods=["POST"]),
    Route(P, get_project),
    Route(P, delete_project, methods=["DELETE"]),
    Route("/api/open-folder", open_folder, methods=["POST"]),
    Route(P + "/window", window, methods=["POST"]),
    Route(P + "/analyze", analyze, methods=["POST"]),
    Route(P + "/analysis", patch_analysis, methods=["PATCH"]),
    Route(P + "/cast", cast, methods=["POST"]),
    Route(P + "/cast/{person}", del_cast, methods=["DELETE"]),
    Route(P + "/cast/{person}/angles/{i:int}", del_angle, methods=["DELETE"]),
    Route(P + "/scene", scene, methods=["POST", "DELETE"]),
    Route(P + "/quote", quote),
    Route(P + "/prompt", set_prompt, methods=["POST"]),
    Route(P + "/mode", set_mode, methods=["POST"]),
    Route(P + "/swap", set_swap, methods=["POST"]),
    Route(P + "/audio", set_audio, methods=["POST"]),
    Route(P + "/shoot", shoot, methods=["POST"]),
    Route(P + "/takes/{tid}/cancel", cancel, methods=["POST"]),
    Route(P + "/takes/{tid}/retry", retry, methods=["POST"]),
    Route(P + "/takes/{tid}/relock", relock, methods=["POST"]),
    Route(P + "/takes/{tid}/refinish", refinish, methods=["POST"]),
    Route(P + "/choose", choose, methods=["POST"]),
    Route(P + "/export", export, methods=["POST"]),
    Route("/files/{pid}/{path:path}", files),
    Mount("/", StaticFiles(directory=str(paths.WEB)), name="web"),
]

app = Starlette(routes=routes)
