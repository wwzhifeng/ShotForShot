<div align="center">

# ShotForShot

**One viral short video + one photo of you → a shot-for-shot remake starring you**

A Windows desktop tool built on the MiniMax H3 video model (UI in Chinese)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%2011-0078d6)
![Python](https://img.shields.io/badge/Python-3.12-3776ab)
![Version](https://img.shields.io/badge/version-0.1.0-orange)

[中文](README.md) · [How it works (Chinese)](docs/工作原理.md) · [Changelog](CHANGELOG.md)

<img src="docs/images/04-compare.png" width="880" alt="Original clip and the remake side by side">

<sub>Screenshots show the UI in mock mode. The people in the demo project are AI-generated.</sub>

</div>

## What it does

Drop in a viral clip (up to 15 s) and a photo of the person you want in it. ShotForShot then works in four steps:

1. **Shot-by-shot breakdown.** Cuts are measured locally with ffmpeg, and every spoken line gets word-level timestamps from speech recognition. A vision model then writes an editable shot list covering shot size, camera move, action and speaker.
2. **Recast.** It swaps in your person and lets you rewrite the dialogue. New lines are capped by the original line's duration so the rhythm stays intact.
3. **Quote before shooting.** It re-shoots through the official MiniMax H3 API and shows the estimated price first. Nothing is submitted until you confirm.
4. **Compare and pick.** Each take plays in sync next to the original with an automatic "rhythm score" based on cut timing, audio sync and face similarity. You export the take you pick as MP4 + SRT.

There is no prompt writing and no node graph. Double-click `启动导演台.bat` to start.

## Highlights

- **Cuts are measured, not guessed.** In one 15-second sample, the remake's three cuts landed within 0.13 / 0.63 / 0.46 s of the original, and all 4 lines were correct. That is a single example, not an average.
- **Recast and rewrite dialogue.** H3 voices the new lines natively, or you can keep the original audio track.
- **Local face lock.** After H3 renders, a local face-swap pass raises similarity to your photo. Across 7 test clips it went from 0.49–0.64 to 0.65–0.81, with smaller faces gaining less. It runs on your machine and costs nothing.
- **Original watermarks stay out.** "Re-shoot from script" never submits the original video. "Copy the motion" erases platform watermarks from its reference clip before upload.
- **Transparent spending.** You get a quote before every shoot, there is a per-project budget cap, and a ledger records every charge. The demo and mock mode are free.
- **Optional GPT vision.** Add an OpenAI key to have GPT write the shot list. If it fails, the tool falls back to MiniMax automatically.

## Two shooting modes

| | Re-shoot from script (default) | Copy the motion |
|---|---|---|
| Sent to H3 | Shot-list script, your photo, and face crops of people you keep. **No original video.** | Original video (the original actor's face is masked locally; upload is blocked if nothing could be masked) and your photo |
| Result | Looks most like you. Framing is re-shot, not frame-exact. | Motion and framing stay close to the original |
| Best for | Dialogue, close-ups, talking-head ads | Dance and full-body action without dialogue |
| 15 s costs about | ¥7.5 | ¥15 |

## Pricing (official MiniMax rates)

| Item | Price |
|---|---|
| Re-shoot from script (H3 768P) | ¥0.5/s, about ¥7.5 for 15 s. A 5-second trial costs about ¥2.5. |
| Copy the motion (H3 768P) | ¥1/s (the reference clip is billed too), about ¥15 for 15 s |
| 2K | about 60% more |
| Shot-list analysis | a few fen per clip. With GPT vision, the vision step uses your own OpenAI quota. |
| Dialogue check (automatic when re-voicing lines) | about ¥0.01 per clip |
| Face lock, comparison, export | free, done locally |

Quotes are estimates based on official prices. The ledger records what MiniMax actually charges.

## Quick start

**Users:**
1. Download the package from [Quark Drive](https://pan.quark.cn/s/b4732e377421) and unzip it anywhere.
2. Run `启动导演台.bat`.
3. Try the built-in demo first. It is free.
4. For real shoots, add a pay-as-you-go [MiniMax](https://platform.minimax.cn) API key in Settings. Top up your account balance; a Token Plan key cannot generate H3 video.

**Developers:** set up the environment with Python 3.12.

```powershell
git clone https://github.com/wwzhifeng/ShotForShot.git
cd ShotForShot
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Copy these from the release package into the same paths before you start:
- `runtime\ffmpeg\bin\ffmpeg.exe` and `ffprobe.exe` (required)
- `程序\models\*.onnx` (required)
- `换脸引擎\` (optional, enables face lock)
- `示例\` (optional, enables the demo)

Then start the app:

```powershell
.venv\Scripts\python -X utf8 程序\launcher.py
```

## Privacy

The program, your projects and your API keys stay on your PC. Keys never go into projects or logs. Data leaves your machine only when you use a step that needs it:

| Sent to | When | What |
|---|---|---|
| MiniMax | Analysis | The selected clip, for speech recognition and vision |
| MiniMax | Shooting | Your photos, scene image, and face crops of people you keep. Plus the masked reference clip in "Copy the motion" mode, and the original audio if you keep it. |
| MiniMax | Dialogue check | The audio of the new take |
| OpenAI | Analysis, only with GPT vision enabled | Frames sampled at 2 fps and the recognized lines |

The local server binds to `127.0.0.1` and checks a per-launch token plus the request origin on every API call. There is no telemetry and no update check.

## Known limitations

- 15 s per take is H3's maximum. 30 s (two takes stitched together) is still being tested.
- Turned heads and three-quarter views work, but full profiles don't yet.
- In wide shots with two people, masking may hit the wrong person.
- "Copy the motion" occasionally reproduces the original subtitles.
- Fully tested only on Windows 11 + NVIDIA. Windows 10 and high-DPI screens are untested.

## Responsible use

- Use only footage and photos you have rights to, and get consent before putting someone's face in a video.
- Remakes carry no AI watermark, so label them as AI-generated wherever platforms require it.
- Do not use the tool to impersonate others, defraud anyone, create sexual content, or for any other illegal purpose.

## License

Copyright (C) 2026 Wang Zhifeng (王知风)

- The source code is licensed under the [GNU GPL v3](LICENSE). The release package is compiled from the matching version of this source.
- The package bundles third-party components with their own licenses. Some face-lock models are non-commercial or research-only, so the package as a whole is for personal, non-commercial use. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- This is not an official MiniMax product. "MiniMax" and "H3" refer to the API and model this tool calls.

## Author

**Wang Zhifeng (王知风)** · [huigui.ai](https://huigui.ai) · QQ group 957732664 · [Issues](https://github.com/wwzhifeng/ShotForShot/issues)
