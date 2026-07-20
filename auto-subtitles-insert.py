import subprocess
import sys
from pathlib import Path

import yaml


def load_settings(config_path="auto-subtitles.yaml"):
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
            f"subtitles={subtitle_file}",
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

    if burn_in:
        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            input_video,
            "-vf",
            f"subtitles={subtitle_file}",
            "-c:v",
            video_codec,
            "-preset",
            str(preset),
            "-crf",
            str(crf),
            "-c:a",
            "copy",
            output_video,
        ]
    else:
        # Add a separate subtitle stream
        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            input_video,
            "-i",
            subtitle_file,
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
            output_video,
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
    main()
