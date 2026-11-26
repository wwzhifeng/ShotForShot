# 第三方组件与许可

本仓库自己的源代码：Copyright (C) 2026 王知风，按 [GNU GPL v3](LICENSE) 发布。下面这些第三方组件各按自己的许可使用。

## 随仓库分发

| 组件 | 用途 | 许可 | 许可原文 |
|---|---|---|---|
| Noto Sans SC / Noto Serif SC（思源黑体 / 思源宋体，已裁剪子集） | 界面字体 | SIL Open Font License 1.1 | `程序/web/fonts/OFL_Noto.txt` |
| JetBrains Mono | 界面等宽字体 | SIL Open Font License 1.1 | `程序/web/fonts/OFL_JetBrainsMono.txt` |
| YuNet、SFace 的许可文件 | 模型本身不在仓库里，许可文件随仓库一起放 | 见下一节 | `程序/models/LICENSE_*.txt` |

## 只在安装包里

### 运行环境和工具

| 组件 | 用途 | 许可 |
|---|---|---|
| Python 3.12 便携运行环境 | 运行程序 | PSF License |
| FFmpeg（gyan.dev 编译的 essentials 版，2023-05-31） | 切镜、抽帧、转码、合成 | GPL v3。源码：<https://ffmpeg.org>，编译说明：<https://www.gyan.dev/ffmpeg/builds/> |
| httpx、starlette、uvicorn | 本机网页服务、联网 | BSD-3-Clause |
| python-multipart | 上传 | Apache-2.0 |
| numpy | 数值计算 | BSD-3-Clause |
| opencv-python | 读帧、人脸模型推理 | Apache-2.0 |

### 人脸模型（`程序\models\`）

| 模型 | 用途 | 许可 | 来源 |
|---|---|---|---|
| YuNet `face_detection_yunet_2023mar` | 找脸、查照片 | MIT | OpenCV Zoo |
| SFace `face_recognition_sface_2021dec` | 像不像打分、认出原片里的人 | Apache-2.0 | OpenCV Zoo |
| BiSeNet `bisenet_resnet_34` | 动作照抄时涂掉原演员的脸和头发 | MIT | yakhyo/face-parsing |

### 换脸引擎（`换脸引擎\`，用于锁脸）

| 组件 | 许可 | 来源 |
|---|---|---|
| FaceFusion 程序 | OpenRAIL-AS（原文：`换脸引擎\LICENSE.md`） | facefusion.io |
| ONNX Runtime | MIT | Microsoft |
| NVIDIA CUDA / cuDNN 运行库 | NVIDIA 软件许可（可再分发部分） | NVIDIA |
| 引擎自带的 Python 库（opencv、onnx、scipy、numpy 等） | 各按其许可，原文在 `换脸引擎\libs\` 各包目录 | — |

引擎里的模型，许可按 FaceFusion 官方的模型许可表（<https://docs.facefusion.io/introduction/licenses>）：

| 模型 | 用途 | 许可 | 原作者 |
|---|---|---|---|
| hyperswap_1b_256 | 换脸 | **ResearchRAIL** | FaceFusion |
| arcface_w600k_r50 | 人脸特征 | **Non-Commercial** | InsightFace |
| fairface | 人脸属性 | **Non-Commercial** | dchen236 |
| kim_vocal_2 | 人声分离 | **Non-Commercial** | KimberleyJensen |
| fan_68_5 | 关键点 | OpenRAIL-M | FaceFusion |
| gfpgan_1.4 | 修脸 | Apache 2.0 | TencentARC |
| xseg_1 | 遮挡（手、话筒挡脸） | GPL-3.0 | DeepFaceLab |
| yoloface_8n | 找脸 | GPL-3.0 | derronqi |
| 2dfan4 | 关键点 | MIT | breadbread1984 |
| bisenet_resnet_34 | 人脸分割 | MIT | yakhyo |
| nsfw_1 / nsfw_2 | 内容检查 | Apache 2.0 | EraX / Marqo |
| nsfw_3 | 内容检查 | MIT | Freepik |

因为锁脸要用的换脸模型（ResearchRAIL）和人脸特征模型（Non-Commercial）不允许商业用途，**安装包整体仅供个人非商业使用**。

## 参考资料（没有复制代码文件）

- 提示词格式参照 MiniMax 官方的 H3 提示词写法（[MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) 里的 `h3-prompt-writing`，MiniMax H3 Community License）。
- 写作规则（台词时长、动作清单、环境声等）参考了：
  - [h3-storyboard-skill](https://github.com/phileiny/h3-storyboard-skill)（MIT，Copyright (c) 2026 Ray）
  - [forest-laoli-h3](https://github.com/lixiaoxiao9888-create/forest-laoli-h3)（MIT）
  - [drama-skills](https://github.com/zenstory-ai/drama-skills)（MIT）
- 「先出逐镜计划、报价、确认再生成」的流程参考了 [ChatCut viral-video-cloner](https://github.com/ChatCut-Inc/viral-video-cloner)（Apache-2.0）。

## 云端接口

视频生成、语音识别、AI 看片调用 [MiniMax 开放平台](https://platform.minimax.cn)；可选的 GPT 看片调用 OpenAI 接口。用的都是你自己的密钥，按各平台的服务条款计费和使用。本项目不是 MiniMax 或 OpenAI 的官方产品。
