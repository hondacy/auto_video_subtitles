# For auto generating subtitle from video file with OpenAI whisper model

import argparse
import sys
from pathlib import Path

import whisper

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

WHISPER_MODEL = None


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


def segments_to_srt(segments):
    lines = []
    for index, segment in enumerate(segments, start=1):
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        text = segment["text"].strip()
        lines.append(f"{index}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def transcribe_to_srt(source_path, output_path=None, model="small", language=None):
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")
    if source.is_dir():
        raise IsADirectoryError(f"Expected a file, got a directory: {source}")

    destination = Path(output_path) if output_path else source.with_suffix(".srt")
    destination.parent.mkdir(parents=True, exist_ok=True)

    whisper_model = get_whisper_model(model)
    options = {}
    if language:
        options["language"] = language

    result = whisper_model.transcribe(str(source), **options)
    subtitle_text = segments_to_srt(result.get("segments", []))

    destination.write_text(subtitle_text, encoding="utf-8")
    return destination


def transcribe_directory(source_dir, output_dir=None, model="whisper-1", language=None):
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
        created_files.append(transcribe_to_srt(child, output_path, model, language))

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
    args = parser.parse_args()

    try:
        input_path = Path(args.input)
        if input_path.is_dir():
            output_dir = args.output if args.output else args.input
            output_paths = transcribe_directory(
                args.input, output_dir, args.model, args.language
            )
            for output_path in output_paths:
                print(f"Subtitles saved to: {output_path}")
        else:
            output_path = transcribe_to_srt(
                args.input, args.output, args.model, args.language
            )
            print(f"Subtitles saved to: {output_path}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
