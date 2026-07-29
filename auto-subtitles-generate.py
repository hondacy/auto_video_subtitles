# For auto generating subtitle from video file with OpenAI whisper model

import argparse
import sys
from pathlib import Path

import whisper
import yaml

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

WHISPER_MODEL = None


def load_settings(config_path="auto-subtitles-generate.yaml"):
    config_file = Path(config_path)
    if not config_file.exists():
        return {"words_per_subtitle": 6}

    with config_file.open("r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    settings.setdefault("words_per_subtitle", 6)
    return settings


def get_whisper_model(model_name="small"):
    global WHISPER_MODEL
    if WHISPER_MODEL is None or WHISPER_MODEL.name != model_name:
        WHISPER_MODEL = whisper.load_model(model_name)
    return WHISPER_MODEL


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def words_to_srt(segments, words_per_subtitle):
    words = [word for segment in segments for word in segment.get("words", [])]

    lines = []
    index = 1
    for chunk_start in range(0, len(words), words_per_subtitle):
        chunk = words[chunk_start:chunk_start + words_per_subtitle]
        start = format_timestamp(chunk[0]["start"])
        end = format_timestamp(chunk[-1]["end"])
        text = "".join(word["word"] for word in chunk).strip()
        lines.append(f"{index}\n{start} --> {end}\n{text}\n")
        index += 1

    return "\n".join(lines)


def transcribe_to_srt(source_path, output_path=None, model="small", language=None, words_per_subtitle=6):
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")
    if source.is_dir():
        raise IsADirectoryError(f"Expected a file, got a directory: {source}")

    destination = Path(output_path) if output_path else source.with_suffix(".srt")
    destination.parent.mkdir(parents=True, exist_ok=True)

    whisper_model = get_whisper_model(model)
    options = {"word_timestamps": True}
    if language:
        options["language"] = language

    result = whisper_model.transcribe(str(source), **options)
    subtitle_text = words_to_srt(result.get("segments", []), words_per_subtitle)

    destination.write_text(subtitle_text, encoding="utf-8")
    return destination


def transcribe_directory(source_dir, output_dir=None, model="whisper-1", language=None, words_per_subtitle=6):
    source = Path(source_dir)
    if not source.exists():
        raise FileNotFoundError(f"Input directory not found: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"Expected a directory, got a file: {source}")

    dest_dir = Path(output_dir) if output_dir else source
    dest_dir.mkdir(parents=True, exist_ok=True)

    media_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".mp4", ".mov", ".webm", ".avi", ".mkv"}
    created_files = []

    media_files = [child for child in sorted(source.iterdir()) if child.is_file() and child.suffix.lower() in media_exts]
    if not media_files:
        raise FileNotFoundError(f"No supported media files found in directory: {source}")

    iterator = tqdm(media_files, desc="Transcribing files", unit="file") if tqdm else media_files
    for child in iterator:
        output_path = dest_dir / f"{child.stem}.srt"
        created_files.append(transcribe_to_srt(child, output_path, model, language, words_per_subtitle))

    if not created_files:
        raise FileNotFoundError(f"No supported media files found in directory: {source}")

    return created_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate subtitle files from audio or video using Whisper."
    )
    parser.add_argument("input", nargs="?", default="proccessing", help="Path to the input audio/video file or a directory containing files. Defaults to proccessing.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output subtitle path or output directory when input is a folder.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="small",
        help="Whisper model to use. Default is small.",
    )
    parser.add_argument(
        "--language",
        help="Optional language code for transcription, e.g. en, es, fr.",
    )
    parser.add_argument(
        "--words-per-subtitle",
        type=int,
        help="Number of words per subtitle entry. Defaults to the value in auto-subtitles-generate.yaml (or 6).",
    )
    args = parser.parse_args()

    settings = load_settings()
    words_per_subtitle = args.words_per_subtitle if args.words_per_subtitle else settings["words_per_subtitle"]

    try:
        input_path = Path(args.input)
        if input_path.is_dir():
            output_dir = args.output if args.output else args.input
            output_paths = transcribe_directory(
                args.input, output_dir, args.model, args.language, words_per_subtitle
            )
            for output_path in output_paths:
                print(f"Subtitles saved to: {output_path}")
        else:
            output_path = transcribe_to_srt(
                args.input, args.output, args.model, args.language, words_per_subtitle
            )
            print(f"Subtitles saved to: {output_path}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
