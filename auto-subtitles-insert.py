# This script fusses the generated subtitles into the video files using ffmpeg. It reads settings from auto-subtitles.yaml and processes all video files in the specified input directory, adding subtitles either as a selectable track or burning them into the video.

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
    return settings


def escape_ffmpeg_filter_value(value):
    text = str(value)

    for char in "\\':":
        text = text.replace(char, f"\\{char}")

    for char in "\\'[],;":
        text = text.replace(char, f"\\{char}")

    return text


def build_subtitles_filter(subtitle_file):
    subtitle_path = subtitle_file.as_posix() if isinstance(subtitle_file, Path) else str(subtitle_file)
    return f"subtitles=filename={escape_ffmpeg_filter_value(subtitle_path)}"


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
    if ffmpeg_has_filter(ffmpeg_path, "subtitles"):
        return

    raise RuntimeError(
        "burn_in is true, but this FFmpeg build does not include the 'subtitles' filter. "
        "Install/use an FFmpeg build configured with --enable-libass, or set burn_in: false "
        "in auto-subtitles-insert.yaml to add subtitles as a selectable subtitle track instead."
    )


def build_ffmpeg_command(settings, input_video, subtitle_file, output_video):
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
            build_subtitles_filter(subtitle_file),
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
            str(subtitle_file),
            "-c:v",
            video_codec,
            "-preset",
            str(preset),
            "-crf",
            str(crf),
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
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

    for video_path in videos:
        subtitle_file = subtitle_dir / f"{video_path.stem}.srt"
        if not subtitle_file.exists():
            print(f"Skipping {video_path.name}: no matching subtitle file found at {subtitle_file}")
            continue

        output_video = output_dir / f"{video_path.stem}_subtitled{video_path.suffix}"
        command = build_ffmpeg_command(settings, video_path, subtitle_file, output_video)
        run_command(command)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
