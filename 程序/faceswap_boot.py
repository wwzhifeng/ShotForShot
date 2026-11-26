"""换脸引擎启动器：用导演台自带的 Python 跑包里的 FaceFusion（headless-run），不碰用户电脑上的任何 Python / CUDA。
用法（由 h3dt.faceswap 调用）：python -I -X utf8 faceswap_boot.py <换脸引擎目录> <FaceFusion 参数…>
- 引擎自带的 libs（OpenCV 4.x、onnxruntime-gpu、scipy）排在最前面，盖过导演台自己的 OpenCV 5；
- cuda\\ 里的 DLL 加进 DLL 搜索路径；只在这个子进程里生效。"""
import os
import runpy
import sys

eng = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.join(eng, "libs"))
sys.path.insert(0, eng)
for d in (os.path.join(eng, "cuda"), os.path.join(eng, "libs", "onnxruntime", "capi")):
    if os.path.isdir(d):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
# FaceFusion 从 PATH 找 ffmpeg：用导演台包里自带的（开发时可用 H3DT_FFMPEG_DIR 指定）
ff = os.environ.get("H3DT_FFMPEG_DIR") or os.path.join(os.path.dirname(eng), "runtime", "ffmpeg", "bin")
os.environ["PATH"] = ff + os.pathsep + os.environ.get("PATH", "")
os.chdir(eng)
sys.argv = [os.path.join(eng, "facefusion.py")] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
