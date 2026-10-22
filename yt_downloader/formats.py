from __future__ import annotations


def _lang_filter(code: str | None) -> str:
    if not code or code == "default":
        return ""
    return f"[language^={code}]"


def _tbr_filter(kbps: int | None) -> str:
    if kbps is None:
        return ""
    try:
        value = int(kbps)
    except Exception:
        return ""
    if value <= 0:
        return ""
    return f"[tbr<={value}]"


def choose_merge_output_format(default_fmt: str, max_height: int | None) -> str:
    if max_height and max_height > 1080:
        return "mkv"
    return default_fmt


def build_video_format(
    *,
    max_height: int | None,
    max_video_bitrate_kbps: int | None,
    audio_lang_code: str | None,
) -> str:
    h = f"[height<={max_height}]" if max_height else ""
    br = _tbr_filter(max_video_bitrate_kbps)
    lang = _lang_filter(audio_lang_code)

    candidates: list[str] = []

    if max_height and max_height > 1080:
        candidates.append(f"bv*{h}{br}+ba{lang}")
        candidates.append(f"bv*{h}{br}+ba")
        candidates.append(f"bv*{h}[vcodec^=avc1]{br}+ba[acodec^=mp4a]{lang}")
        candidates.append(f"bv*{h}[vcodec^=avc1]{br}+ba[acodec^=mp4a]")
        candidates.append(f"b{h}{br}")
        return "/".join(candidates)

    candidates.append(f"bv*{h}[vcodec^=avc1]{br}+ba[acodec^=mp4a]{lang}")
    candidates.append(f"bv*{h}[vcodec^=avc1]{br}+ba[acodec^=mp4a]")
    candidates.append(f"bv*{h}{br}+ba{lang}")
    candidates.append(f"bv*{h}{br}+ba")
    candidates.append(f"b{h}{br}")
    return "/".join(candidates)


def build_audio_only_format(*, audio_preset_key: str, audio_lang_code: str | None) -> str:
    lang = _lang_filter(audio_lang_code)
    if "m4a" in audio_preset_key.lower():
        if lang:
            return f"bestaudio[ext=m4a]{lang}/bestaudio{lang}/bestaudio[ext=m4a]/bestaudio/b"
        return "bestaudio[ext=m4a]/bestaudio/b"
    if lang:
        return f"bestaudio{lang}/bestaudio/b"
    return "bestaudio/b"

