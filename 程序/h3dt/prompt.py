"""复刻提示词：按官方 Ref2VA 六段写法拼（参考\\skills\\MiniMax-H3\\...\\ref-en.txt）。

要点（官方）：
- 原片只借镜头、切点、节奏时，任务类型写 [reference generation]，不写 [video editing]。
- 换上去的人写成 <Subject N>，外貌来自 <Picture N>，动作表演来自 <Video 1>；retention 用 attribute_transfer。
- <Video 1> 只管运镜、切点、节奏；第一镜无时间码，后面写 [Shot N] At MM:SS.mmm。
- 说话人 (S1)，台词 <d>[Chinese] …</d>；只借节奏时不把原台词带进新片（所以原片要去音轨）。
- 不写否定句（「不要字幕」会招来字幕），字幕靠裁掉参考片的字幕区解决。
"""
from __future__ import annotations

import re

from . import analyze, media


CAM_VERB = {"推": "pushes in", "拉": "pulls out", "摇": "pans", "移": "trucks sideways", "跟": "tracks the subject",
            "升降": "pedestals up", "手持": "shakes slightly like a handheld camera", "环绕": "moves in an arc shot around the subject"}


def _cam(c: dict) -> str:
    """官方写法：运动类型 + 幅度 + 速度；中等幅度、正常速度省略（base-en.txt 4.3）。"""
    t = c.get("type", "固定")
    if t == "固定":
        return "the camera holds a static shot"
    s = f"the camera {CAM_VERB.get(t, 'moves')}"
    amp = {"轻微": "small", "小幅": "small", "大幅": "large"}.get(c.get("amp"))
    spd = {"慢": "slow", "快": "fast"}.get(c.get("speed"))
    if amp:
        s += f" with {amp} amplitude"
    if spd:
        s += f" at {spd} speed"
    return s


def _lc(s: str) -> str:
    return s[0].lower() + s[1:] if s and not s.startswith(("<", "I ")) else s


# 「用原片原声」（11-23 用户要的选项）：原片声音当 <Audio 1> 整轨照搬，人照着它对口型。写法按官方 ref-en.txt 2.4 / 4.2 / 5.4：
# 照搬的台词保留原话，说话人仍写 (Sx)；关系标记 fully_copy；任务类型加 audio reuse。
_AUDIO_DEF = ("<Audio 1> is the original soundtrack of the target video, containing its dialogue, ambience and music, "
              "and is reused 1:1 as the final audio track.")
_AUDIO_KEEP = "<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final audio track."
_SYNC = ", with lips precisely synced to the same words in <Audio 1>"
_QUIET = " does not speak in this shot; the body movement and expression follow the rhythm and mood of <Audio 1>."


def _copied_sound(a: dict) -> tuple[str, str]:
    sound = "The complete soundtrack of <Audio 1>, including its dialogue, ambience and sound effects, is reused 1:1 from the first frame to the last."
    # 拉片看不出有没有配乐时也照写：原声整轨照搬，里面有什么就是什么，不另加配乐
    mus = "Any music in <Audio 1> is reused 1:1 as part of the copied soundtrack; no other score is added."
    return sound, mus


def _lang(line: str) -> str:
    """台词语言标记：有汉字算中文，否则按英文（11-23 实测原片台词是英文 Damn.，原来一律写 [Chinese]）。"""
    return "Chinese" if re.search(r"[一-鿿]", line) else "English"


def build_novideo(a: dict, cast: dict, out_dur: float, music: str = "auto", offset: float = 0.0,
                  lines_override: list | None = None, keep_refs: dict | None = None, outfit_from: str = "video",
                  audio_copy: bool = False) -> str:
    """不传参考视频：按拉片表把每镜写成文字，只带人物照片（换人靠 H3 的参考图能力；11-22 实测带参考视频时脸会被拉回原片演员）。
    keep_refs = {不换的人: 参考图编号}：从原片截出来的他的脸，让他保持原样。
    audio_copy = 用原片原声（<Audio 1>，官方 ref-en.txt 4.2 的 fully_copy + 任务类型 audio reuse）。"""
    people = {p["id"]: p for p in a.get("people", [])}
    shots = [s for s in a["shots"] if s["end"] - offset > 0.05 and s["start"] - offset < out_dur - 0.05]
    subj: dict[str, int] = {}
    defs = []
    for n, (pid, pic) in enumerate(cast.items(), 1):
        subj[pid] = n
        outfit = (people.get(pid, {}).get("outfit_en") or "").strip().rstrip(".")
        if outfit_from == "photo":
            # 换整个人：脸、发型、身材、整套衣服鞋包都跟照片
            defs.append(f"<Subject {n}> is the person in <Picture {pic}>, keeping the face, facial features, hairstyle, body shape "
                        f"and the complete outfit shown in <Picture {pic}> (clothing, shoes and accessories) in every shot.")
        else:
            defs.append(f"<Subject {n}> is the person in <Picture {pic}>, keeping the face, facial features and hairstyle of <Picture {pic}>"
                        + (f", wearing {_lc(outfit)}" if outfit else "") + ".")
    for pid, pic in (keep_refs or {}).items():
        if pid in subj:
            continue
        subj[pid] = len(subj) + 1
        d = (people.get(pid, {}).get("desc_en") or "").strip().rstrip(".")
        defs.append(f"<Subject {subj[pid]}> is the person in <Picture {pic}>" + (f": {_lc(d)}" if d else "") + ".")

    def who(pid: str) -> str:
        if pid in subj:
            return f"<Subject {subj[pid]}>"
        d = (people.get(pid, {}).get("desc_en") or "a person").strip().rstrip(".")
        return _lc(d)

    def short(pid: str) -> str:
        if pid in subj:
            return f"<Subject {subj[pid]}>"
        g = people.get(pid, {}).get("gender")
        return "the man" if g == "male" else "the woman" if g == "female" else "the other person"

    lines = lines_override if lines_override is not None else a.get("lines", [])
    lines = [l for l in lines if l.get("new") != "" and (l.get("new") or l.get("text"))
             and l["start"] >= offset - 0.2 and (l["end"] - offset <= out_dur + 0.3
                                                  or (audio_copy and l["start"] - offset < out_dur - 0.3))]
    spk: dict[str, str] = {}
    for l in sorted(lines, key=lambda x: x["start"]):
        spk.setdefault(l["who"], f"S{len(spk) + 1}")
    style = a.get("style_en") or "live-action cinematic short-drama style"
    env = a.get("env_en") or ""
    introduced: set[str] = set()
    body = [f"The target video is live-action, cinematic, in this visual style: {_lc(style.rstrip('.'))}."
            + (f" The setting is {_lc(env.rstrip('.'))}." if env else "")]
    for k, s in enumerate(shots):
        st = max(0.0, s["start"] - offset)
        head = "[Shot 1]" if k == 0 else f"[Shot {k + 1}] At {media.tc(st)}, the camera cuts to"
        size = analyze.SIZE_EN.get(s.get("size"), "medium shot")
        names = []
        for p in s.get("who", []):
            names.append(short(p) if p in introduced else who(p))
            introduced.add(p)
        subjects = ", ".join(names) or "the scene"
        action = (s.get("action_en") or "").strip().rstrip(".")
        for pid in people:
            action = re.sub(rf"\b[Pp]erson {pid}\b", short(pid), action)
        txt = f"{head} {'A' if k == 0 else 'a'} {size} of {subjects}; {_cam(s.get('camera', {}))}."
        if action:
            txt += f" {action[0].upper() + action[1:]}."
        said: list[tuple[str, str]] = []
        for l in lines:
            ls = l["start"] - offset
            if (st - 0.05 <= ls < max(0.0, s["end"] - offset)) or (k == 0 and ls < st):
                line = (l.get("new") or l.get("text")).strip() + ("<cutoff>" if l["end"] - offset > out_dur + 0.3 else "")
                if said and said[-1][0] == l["who"]:
                    said[-1] = (l["who"], said[-1][1] + line)
                else:
                    said.append((l["who"], line))
        for pid, line in said:
            sp = short(pid)
            txt += f" {sp[0].upper() + sp[1:]} ({spk[pid]}) says{_SYNC if audio_copy else ''}, <d>[{_lang(line)}] {line}</d>"
        if not said and s.get("who"):
            txt += " " + " and ".join(short(p) for p in s["who"]) + (_QUIET if audio_copy else " stays silent throughout this shot.")
        body.append(txt)
    if audio_copy:
        defs.append(_AUDIO_DEF)
    summary = (f"[reference generation{' + audio reuse' if audio_copy else ''}] A {len(shots)}-shot short-drama scene featuring "
               + ", ".join(f"<Subject {v}>" for v in subj.values()) + ((", with the original dialogue from <Audio 1>." if audio_copy else ", with Chinese dialogue.") if lines else "."))
    pics = {**(keep_refs or {}), **cast}
    retention = [f"<Subject {n}> (appears in " + (", ".join(f"[Shot {k + 1}]" for k, s in enumerate(shots) if pid in s.get("who", [])) or "[Shot 1]")
                 + f"): fully_preserved - the identity, face and hairstyle of the person in <Picture {pics[pid]}> are kept in every shot."
                 for pid, n in subj.items()]
    sound = a.get("sound_en") or "Natural ambience matching the scene."
    m = (a.get("music_en") or "").strip()
    mus = "N/A" if music == "none" else (m if m and m.upper() != "N/A" else "A subtle underscore that matches the mood, kept low under the dialogue.")
    if audio_copy:
        retention.append(_AUDIO_KEEP)
        sound, mus = _copied_sound(a)
    return "\n\n".join(["subject_definitions:\n" + "\n".join(defs), "summary:\n" + summary,
                        "retention_analysis:\n" + "\n".join(retention), "detailed_description:\n" + "\n".join(body),
                        "overall_soundscape:\n" + sound, "non_diegetic_music:\n" + mus])


def build(a: dict, cast: dict, out_dur: float, scene_photo: bool = False, music: str = "auto",
          offset: float = 0.0, lines_override: list | None = None, outfit_from: str = "video",
          audio_copy: bool = False, angles: dict | None = None) -> str:
    """a = analysis；cast = {"A": 1, ...} 人物 → 参考图编号；offset 用于只拍前几秒时把时间轴对齐；
    angles = {"A": [3, 4], ...} 这个人另外几张角度照的图号（11-24：给了侧脸/转头照，头才会跟着原片转）。"""
    people = {p["id"]: p for p in a.get("people", [])}
    subj: dict[str, int] = {}
    defs: list[str] = []
    n = 0
    for pid, pic in cast.items():
        n += 1
        subj[pid] = n
        outfit = (people.get(pid, {}).get("outfit_en") or "").strip().rstrip(".")
        if outfit and outfit_from == "video":
            look = (f"whose face, facial features and hairstyle come from <Picture {pic}>, wearing the outfit of person {pid} "
                    f"in <Video 1>: {outfit[0].lower() + outfit[1:]}")
        else:
            look = (f"whose face, facial features, hairstyle, body shape and complete outfit (clothing, shoes and accessories) "
                    f"all come from <Picture {pic}>")
        extra = (angles or {}).get(pid) or []
        if extra:
            shown = ", ".join(f"<Picture {x}>" for x in [pic] + extra[:-1]) + f" and <Picture {extra[-1]}>"
            head = (f"<Subject {n}> is the person shown in {shown}: the same person seen from the front and from other angles "
                    f"(turned and profile views), {look}, and the face stays the same from every angle")
        else:
            head = f"<Subject {n}> is the person in <Picture {pic}>, {look}"
        defs.append(f"{head}; <Subject {n}> takes over the role, movements and performance of person {pid} in <Video 1>.")
    shots = [s for s in a["shots"] if s["end"] - offset > 0.05 and s["start"] - offset < out_dur - 0.05]
    # 不换的人：官方写法是从 <Video 1> 里定义成 <Subject N>，保持原样（fully_preserved）
    kept: list[str] = []
    for pid in sorted(people):
        if pid in cast or not any(pid in s.get("who", []) for s in shots):
            continue
        n += 1
        subj[pid] = n
        kept.append(pid)
        d = (people[pid].get("desc_en") or "").strip().rstrip(".")
        defs.append(f"<Subject {n}> is person {pid} in <Video 1>" + (f": {_lc(d)}" if d else "") + ".")
    env_subject = None
    if scene_photo:
        n += 1
        env_subject = n
        pic = len(cast) + 1
        defs.append(f"<Subject {n}> is the environment in <Picture {pic}>.")
    defs.append("<Video 1> is the reference video providing the shot sizes, camera movement, cut timing, blocking and performance rhythm of the target video.")
    if audio_copy:
        defs.append(_AUDIO_DEF)

    def who(pid: str) -> str:
        if pid in subj:
            return f"<Subject {subj[pid]}>"
        return "a person"
    lines = lines_override if lines_override is not None else a.get("lines", [])
    # new == "" 表示这句不说（用户删掉了）；new is None 表示照搬原台词
    lines = [l for l in lines if l.get("new") != "" and (l.get("new") or l.get("text"))
             and l["start"] >= offset - 0.2 and (l["end"] - offset <= out_dur + 0.3
                                                  or (audio_copy and l["start"] - offset < out_dur - 0.3))]

    # 说话人编号按新片里出声顺序分配
    spk: dict[str, str] = {}
    for l in sorted(lines, key=lambda x: x["start"]):
        if l["who"] not in spk:
            spk[l["who"]] = f"S{len(spk) + 1}"

    style = a.get("style_en") or "realistic short-drama style with natural cinematic lighting"
    env = a.get("env_en") or ""
    body = [f"The target video follows this visual style: {_lc(style.rstrip('.'))}."
            + (f" The setting is {_lc(env.rstrip('.'))}." if env and not env_subject else "")]
    for k, s in enumerate(shots):
        st = max(0.0, s["start"] - offset)
        head = "[Shot 1]" if k == 0 else f"[Shot {k + 1}] At {media.tc(st)}, the shot cuts to"
        size = analyze.SIZE_EN.get(s.get("size"), "medium shot")
        subjects = ", ".join(who(p) for p in s.get("who", [])) or "the scene"
        action = (s.get("action_en") or "").strip().rstrip(".")
        for pid in subj:
            action = re.sub(rf"\b[Pp]erson {pid}\b", who(pid), action)
        txt = f"{head} a {size} of {subjects}" if k else f"{head} A {size} of {subjects}"
        if env_subject:
            txt += f" in <Subject {env_subject}>"
        txt += f"; {_cam(s.get('camera', {}))}, matching the corresponding shot of <Video 1>."
        if action:
            txt += f" {action[0].upper() + action[1:]}."
        spoke = False
        said: list[tuple[str, str]] = []     # 同一镜头里同一个人连着说的句子合成一句
        for l in lines:
            ls = l["start"] - offset
            if (st - 0.05 <= ls < max(0.0, s["end"] - offset)) or (k == 0 and ls < st):
                line = (l.get("new") or l.get("text")).strip() + ("<cutoff>" if l["end"] - offset > out_dur + 0.3 else "")
                if said and said[-1][0] == l["who"]:
                    said[-1] = (l["who"], said[-1][1] + line)
                else:
                    said.append((l["who"], line))
        for pid, line in said:
            sp = who(pid)
            sp = sp[0].upper() + sp[1:]
            txt += f" {sp} ({spk[pid]}) says{_SYNC if audio_copy else ''}, <d>[{_lang(line)}] {line}</d>"
            spoke = True
        if not spoke and s.get("who"):
            # H3 默认会出声，没台词的镜头写明闭嘴（麦麦提文章的「闭嘴铁律」，正面写法）
            txt += " " + " and ".join(who(p) for p in s["who"]) + (_QUIET if audio_copy else " stays silent throughout this shot; any mouth movement is expression only.")
        body.append(txt)

    subjects_all = ", ".join(f"<Subject {v}>" for v in subj.values())
    summary = (f"[reference generation{' + audio reuse' if audio_copy else ''}] The target video recreates the shot structure, camera movement and editing rhythm of "
               f"<Video 1> shot by shot, with {subjects_all or 'the same performers'} performing the original actions"
               + ((" and speaking the original dialogue from <Audio 1>." if audio_copy else " and speaking new Chinese dialogue.") if lines else "."))
    retention = []
    for pid, sn in subj.items():
        appear = ", ".join(f"[Shot {k + 1}]" for k, s in enumerate(shots) if pid in s.get("who", [])) or "[Shot 1]"
        if pid in kept:
            retention.append(f"<Subject {sn}> (appears in {appear}): fully_preserved - person {pid}'s appearance, clothing, "
                             f"movements and blocking from <Video 1> are kept.")
            continue
        retention.append(f"<Subject {sn}> (appears in {appear}): attribute_transfer - the movements, gestures, expressions and "
                         f"blocking of person {pid} in <Video 1> are transferred onto the person from <Picture {cast[pid]}>, "
                         f"whose identity, face and hairstyle are fully preserved"
                         + (f", while the outfit follows person {pid} in <Video 1>." if outfit_from == "video"
                            and (people.get(pid, {}).get("outfit_en")) else
                            f" together with the body shape and the complete outfit from <Picture {cast[pid]}>; only the motion comes from <Video 1>."))
    if env_subject:
        retention.append(f"<Subject {env_subject}> (appears in all shots): fully_preserved - the location, layout and lighting are retained.")
    retention.append("<Video 1> (shot sizes, camera movement, cut and pacing structure): fully_preserved - every cut lands at the same time "
                     "as in <Video 1> and each shot keeps its framing and camera move.")
    if audio_copy:
        retention.append(_AUDIO_KEEP)

    sound = a.get("sound_en") or "Natural ambience matching the scene."
    if music == "none":
        mus = "N/A"
    else:
        m = (a.get("music_en") or "").strip()
        mus = m if m and m.upper() != "N/A" else "A subtle underscore that matches the mood, kept low under the dialogue."
    if audio_copy:
        sound, mus = _copied_sound(a)
    return "\n\n".join([
        "subject_definitions:\n" + "\n".join(defs),
        "summary:\n" + summary,
        "retention_analysis:\n" + "\n".join(retention),
        "detailed_description:\n" + "\n".join(body),
        "overall_soundscape:\n" + sound,
        "non_diegetic_music:\n" + mus,
    ])
