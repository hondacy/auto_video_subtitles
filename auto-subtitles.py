import argparse
import sys
import time
from pathlib import Path

from openai import OpenAI
from openai.error import OpenAIError, RateLimitError

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

client = OpenAI()


def transcribe_to_srt(source_path, output_path=None, model="whisper-1", language=None):
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")
    if source.is_dir():
        raise IsADirectoryError(f"Expected a file, got a directory: {source}")

    destination = Path(output_path) if output_path else source.with_suffix(".srt")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with source.open("rb") as audio_file:
        request = {
            "model": model,
            "file": audio_file,
            "response_format": "srt",
        }
        if language:
            request["language"] = language

        max_retries = 5
        backoff = 1.0
        while True:
            try:
                transcript = client.audio.transcriptions.create(**request)
                break
            except RateLimitError as exc:
                if max_retries <= 0:
                    raise
                print(f"Rate limited. Retrying in {backoff} seconds...", file=sys.stderr)
                time.sleep(backoff)
                max_retries -= 1
                backoff *= 2
            except OpenAIError:
                raise

    subtitle_text = getattr(transcript, "text", None)
    if subtitle_text is None:
        if isinstance(transcript, dict):
            subtitle_text = transcript.get("text", "")
        else:
            subtitle_text = str(transcript)

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
    parser.add_argument("input", help="Path to the input audio/video file or a directory containing files")
    parser.add_argument(
        "-o",
        "--output",
        help="Output subtitle path or output directory when input is a folder.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="whisper-1",
        help="Whisper model to use. Default is whisper-1.",
    )
    parser.add_argument(
        "--language",
        help="Optional language code for transcription, e.g. en, es, fr.",
    )
    args = parser.parse_args()

    try:
        input_path = Path(args.input)
        if input_path.is_dir():
            output_paths = transcribe_directory(
                args.input, args.output, args.model, args.language
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
