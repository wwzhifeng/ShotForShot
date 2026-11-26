"""王知风 H3 导演台 启动器：中文提示都在这里（bat 保持纯 ASCII）。"""
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

ORIG_ENV = dict(os.environ)          # 打开浏览器用用户原本的环境
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from h3dt import paths  # noqa: E402

paths.ensure_dirs()
for k, v in {"TEMP": paths.TEMP, "TMP": paths.TEMP, "XDG_CACHE_HOME": paths.CACHE}.items():
    os.environ[k] = str(v)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

from h3dt import store  # noqa: E402

BANNER = f"""
  ============================================================
    王知风 H3 导演台 · 爆款复刻版  v{store.VERSION}
    作者：王知风   官网 https://huigui.ai   AI工具群 957732664
  ============================================================
"""
STATE = paths.CACHE / "server.json"


def say(msg: str) -> None:
    print("  " + msg, flush=True)


def alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/ping"), timeout=1.5) as r:
            return json.loads(r.read().decode()).get("app") == "h3dt"
    except Exception:  # noqa: BLE001
        return False


def patch_proactor() -> None:
    """浏览器断开时 Windows 会在 _call_connection_lost 的 shutdown() 抛 10054，且跳过后面的清理。
    只吞 shutdown 的 OSError，并保证 close/置空/detach 照常执行；以后 Python 自己修了就不动。"""
    import asyncio.proactor_events as pe
    import inspect
    import socket as _s
    cls = pe._ProactorBasePipeTransport
    try:
        if "except OSError" in inspect.getsource(cls._call_connection_lost):
            return
    except (OSError, TypeError):
        return

    def _call_connection_lost(self, exc):
        if getattr(self, "_called_connection_lost", False):
            return
        try:
            self._protocol.connection_lost(exc)
        finally:
            try:
                if hasattr(self._sock, "shutdown") and self._sock.fileno() != -1:
                    self._sock.shutdown(_s.SHUT_RDWR)
            except OSError:
                pass
            finally:
                try:
                    self._sock.close()
                finally:
                    self._sock = None
                    server = self._server
                    if server is not None:
                        server._detach()
                        self._server = None
                    self._called_connection_lost = True

    cls._call_connection_lost = _call_connection_lost


def free_port(start: int = 18730) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("找不到空闲端口")


def open_browser(url: str) -> None:
    try:
        subprocess.Popen(["cmd", "/c", "start", "", url], env=ORIG_ENV, creationflags=0x08000000)
    except Exception:  # noqa: BLE001
        say(f"请手动打开浏览器访问：{url}")


def main() -> None:
    print(BANNER, flush=True)
    logging.basicConfig(level=logging.INFO, handlers=[
        RotatingFileHandler(paths.LOGS / "导演台.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")],
        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    say("[1/3] 检查 ...")
    if STATE.exists():
        try:
            old = json.loads(STATE.read_text(encoding="utf-8"))
            if alive(old["port"]):
                say("导演台已经开着，直接打开网页。")
                open_browser(f"http://127.0.0.1:{old['port']}/")
                time.sleep(1.5)
                return
        except Exception:  # noqa: BLE001
            pass
    try:
        paths.tool("ffmpeg")
    except FileNotFoundError as e:
        say(f"[失败] {e}")
        say("包不完整，请重新解压完整的压缩包。")
        input("  按回车关闭 ...")
        return
    from h3dt.minimax import read_key
    say("已找到 MiniMax 密钥。" if read_key() else "还没填 MiniMax 密钥：可以先用模拟模式免费走一遍，真拍前到「设置」里粘贴密钥。")

    port = free_port(int(os.environ.get("H3DT_PORT") or 18730))
    say(f"[2/3] 启动本机服务（端口 {port}）...")
    patch_proactor()
    import uvicorn
    from h3dt import server, service

    service.start_poller()
    cfg = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    srv = uvicorn.Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if alive(port):
            break
        time.sleep(0.1)
    else:
        say("[失败] 服务没起来，详情看「日志」文件夹。")
        input("  按回车关闭 ...")
        return
    STATE.write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    url = f"http://127.0.0.1:{port}/"
    say(f"[3/3] 就绪：{url}")
    say("网页已自动打开。用完关掉这个黑窗口即可（拍摄中的任务下次打开会接着查）。")
    if not os.environ.get("H3DT_NO_BROWSER"):
        open_browser(url)
    try:
        while th.is_alive():
            th.join(1)
    except KeyboardInterrupt:
        pass
    finally:
        STATE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
