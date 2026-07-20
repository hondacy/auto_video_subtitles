import subprocess
import sys
from pathlib import Path

import yaml


def load_settings(config_path="auto-subtitles.yaml"):
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Settings file not found: {config_file}")
    with config_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_ffmpeg_command(settings):
    input_video = settings["video_input"]
    subtitle_file = settings["subtitle_file"]
    output_video = settings["output_video"]
    ffmpeg_path = settings.get("ffmpeg_path", "ffmpeg")
    burn_in = settings.get("burn_in", False)
    video_codec = settings.get("video_codec", "libx264")
    preset = settings.get("preset", "medium")
    crf = settings.get("crf", 18)

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


def main():
    settings = load_settings()
    command = build_ffmpeg_command(settings)
    run_command(command)


if __name__ == "__main__":
    main()
