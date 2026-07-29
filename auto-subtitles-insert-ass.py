# This script inserts subtitles into video files using the Advanced SubStation Alpha (ASS)
# method: matching .srt files are converted to styled .ass files (using the subtitles_style
# block in auto-subtitles-insert.yaml) and then either burned into the video or muxed in as
# a selectable subtitle track.

import re
import subprocess
import sys
from pathlib import Path

import yaml


def load_settings(config_path="auto-subtitles-insert.yaml"):
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Settings file not found: {config_file}")
    with config_file.open("r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    settings.setdefault("video_input_dir", "proccessing")
    settings.setdefault("subtitle_dir", settings["video_input_dir"])
    settings.setdefault("output_dir", str(Path(settings["video_input_dir"]) / "with_subtitles"))
    settings.setdefault("ffmpeg_path", "ffmpeg")
    settings.setdefault("burn_in", False)
    settings.setdefault("video_codec", "libx264")
    settings.setdefault("preset", "medium")
    settings.setdefault("crf", 18)
    settings.setdefault("subtitle_language", "eng")
    settings.setdefault("supported_extensions", [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".mpg", ".mpeg", ".m4v"])
    settings.setdefault("subtitles_style", {})
    return settings


DEFAULT_STYLE = {
    "FontName": "Arial",
    "FontSize": "24",
    "PrimaryColour": "FFFFFF",
    "BackColour": "000000",
    "Outline": "1",
    "Shadow": "2",
}


def to_ass_color(hex_color, alpha="00"):
    hex_color = str(hex_color).lstrip("#").strip()
    hex_color = hex_color.zfill(6)
    rr, gg, bb = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def build_ass_style_line(style):
    merged = {**DEFAULT_STYLE, **style}
    return (
        "Style: Default,"
        f"{merged['FontName']},{merged['FontSize']},"
        f"{to_ass_color(merged['PrimaryColour'])},{to_ass_color('FFFFFF')},"
        f"{to_ass_color(merged['PrimaryColour'])},{to_ass_color(merged['BackColour'])},"
        "0,0,0,0,100,100,0,0,1,"
        f"{merged['Outline']},{merged['Shadow']},2,10,10,10,1"
    )


SRT_TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2}),(\d{3})")


def srt_time_to_ass(time_str):
    match = SRT_TIME_RE.match(time_str.strip())
    if not match:
        raise ValueError(f"Unrecognized SRT timestamp: {time_str}")
    hours, minutes, seconds, millis = match.groups()
    centiseconds = int(millis) // 10
    return f"{int(hours)}:{minutes}:{seconds}.{centiseconds:02d}"


def parse_srt(subtitle_path):
    content = subtitle_path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []

    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip() != ""]
        if len(lines) < 2:
            continue

        timing_line_index = 0
        if "-->" not in lines[0]:
            timing_line_index = 1
        if timing_line_index >= len(lines) or "-->" not in lines[timing_line_index]:
            continue

        start_str, end_str = [part.strip() for part in lines[timing_line_index].split("-->")]
        text_lines = lines[timing_line_index + 1:]
        if not text_lines:
            continue

        entries.append((srt_time_to_ass(start_str), srt_time_to_ass(end_str), "\\N".join(text_lines)))

    return entries


def escape_ass_text(text):
    return text.replace("{", "\\{").replace("}", "\\}")


def build_ass_file(subtitle_path, ass_path, style):
    entries = parse_srt(subtitle_path)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        build_ass_style_line(style),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for start, end, text in entries:
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{escape_ass_text(text)}")

    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_ffmpeg_filter_value(value):
    text = str(value)

    for char in "\\':":
        text = text.replace(char, f"\\{char}")

    for char in "\\'[],;":
        text = text.replace(char, f"\\{char}")

    return text


def build_ass_filter(ass_file):
    ass_path = ass_file.as_posix() if isinstance(ass_file, Path) else str(ass_file)
    return f"ass=filename={escape_ffmpeg_filter_value(ass_path)}"


def ffmpeg_has_filter(ffmpeg_path, filter_name):
    try:
        result = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"FFmpeg executable not found: {ffmpeg_path}") from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(f"Could not inspect FFmpeg filters: {details}") from exc

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == filter_name:
            return True

    return False


def validate_ffmpeg_capabilities(settings):
    if not settings["burn_in"]:
        return

    ffmpeg_path = settings["ffmpeg_path"]
    if ffmpeg_has_filter(ffmpeg_path, "ass"):
        return

    raise RuntimeError(
        "burn_in is true, but this FFmpeg build does not include the 'ass' filter. "
        "Install/use an FFmpeg build configured with --enable-libass, or set burn_in: false "
        "in auto-subtitles-insert.yaml to add subtitles as a selectable subtitle track instead."
    )


def build_ffmpeg_command(settings, input_video, ass_file, output_video):
    ffmpeg_path = settings["ffmpeg_path"]
    burn_in = settings["burn_in"]
    video_codec = settings["video_codec"]
    preset = settings["preset"]
    crf = settings["crf"]

    if burn_in:
        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            str(input_video),
            "-vf",
            build_ass_filter(ass_file),
            "-c:v",
            video_codec,
            "-preset",
            str(preset),
            "-crf",
            str(crf),
            "-c:a",
            "copy",
            str(output_video),
        ]
    else:
        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            str(input_video),
            "-i",
            str(ass_file),
            "-c:v",
            video_codec,
            "-preset",
            str(preset),
            "-crf",
            str(crf),
            "-c:a",
            "copy",
            "-c:s",
            "ass",
            "-metadata:s:s:0",
            f"language={settings.get('subtitle_language', 'eng')}",
            str(output_video),
        ]

    return cmd


def run_command(cmd):
    print("Running ffmpeg command:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
    print(result.stdout)


def find_video_files(settings):
    input_dir = Path(settings["video_input_dir"])
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Video input directory not found: {input_dir}")

    return [
        child
        for child in sorted(input_dir.iterdir())
        if child.is_file() and child.suffix.lower() in settings["supported_extensions"]
    ]


def main():
    settings = load_settings()
    validate_ffmpeg_capabilities(settings)

    output_dir = Path(settings["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    subtitle_dir = Path(settings["subtitle_dir"])
    if not subtitle_dir.exists() or not subtitle_dir.is_dir():
        raise FileNotFoundError(f"Subtitle directory not found: {subtitle_dir}")

    videos = find_video_files(settings)
    if not videos:
        print(f"No supported videos found in {settings['video_input_dir']}")
        return

    style = settings["subtitles_style"] or {}

    for video_path in videos:
        subtitle_file = subtitle_dir / f"{video_path.stem}.srt"
        if not subtitle_file.exists():
            print(f"Skipping {video_path.name}: no matching subtitle file found at {subtitle_file}")
            continue

        ass_file = output_dir / f"{video_path.stem}.ass"
        build_ass_file(subtitle_file, ass_file, style)

        output_suffix = video_path.suffix if settings["burn_in"] else ".mkv"
        output_video = output_dir / f"{video_path.stem}_subtitled_ass{output_suffix}"
        command = build_ffmpeg_command(settings, video_path, ass_file, output_video)
        run_command(command)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
