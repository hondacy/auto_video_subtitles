import subprocess
import cv2
from pathlib import Path


def find_input_dir():
    candidate = Path("proccessing")
    if candidate.exists() and candidate.is_dir():
        return candidate
    raise FileNotFoundError(
        "Input directory not found. Expected 'proccessing' in the current working directory."
    )


def open_video_capture(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")
    return cap


def enhance_frame(frame):
    ## Anhance colors and brightness using OpenCV's detailEnhance function
    return cv2.detailEnhance(frame, sigma_s=10, sigma_r=0.15)


def process_video_stream(video_path, output_path):
    cap = open_video_capture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video writer for: {output_path}")

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        enhanced_frame = enhance_frame(frame)
        writer.write(cv2.cvtColor(enhanced_frame, cv2.COLOR_RGB2BGR))
        frame_count += 1

    cap.release()
    writer.release()

    if frame_count == 0:
        raise RuntimeError(f"Video contains no frames: {video_path}")

    return frame_count


input_dir = find_input_dir()
output_dir = input_dir / "enhanced_videos"
output_dir.mkdir(parents=True, exist_ok=True)

supported_extensions = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".mpg", ".mpeg", ".m4v"
}

skip_patterns = ["_enhanced", "_subtitled"]

# Process every file in the input directory
for video_path in sorted(input_dir.iterdir()):
    if not video_path.is_file():
        continue
    if video_path.suffix.lower() not in supported_extensions:
        print(f"Skipping unsupported file: {video_path.name}")
        continue
    if any(pattern in video_path.stem for pattern in skip_patterns):
        print(f"Skipping generated output file: {video_path.name}")
        continue

    print(f"Processing: {video_path.name}")
    output_file = output_dir / f"{video_path.stem}_enhanced{video_path.suffix}"

    # 1. Stream video processing frame by frame
    # Current skipped because of quality issues with the enhancement. Uncomment the following line to enable frame-by-frame processing. 
    # frame_count = process_video_stream(video_path, output_file)

    # 2. Audio Extraction and Enhancement using ffmpeg
    try:
        audio_output = output_dir / f"{video_path.stem}_audio.wav"
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-af",
            "highpass=f=120,afftdn=nf=-25,volume=5dB",
            str(audio_output),
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        # Combine enhanced audio with original video stream
        output_file = output_dir / f"{video_path.stem}_enhanced{video_path.suffix}"
        remux_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_output),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            str(output_file),
        ]
        subprocess.run(remux_cmd, check=True, capture_output=True)
        audio_ok = True
        audio_output.unlink(missing_ok=True)
    except subprocess.CalledProcessError as exc:
        print(f"Warning: audio could not be processed for {video_path.name}: {exc.stderr.decode().strip()}")
        audio_ok = False

    if audio_ok:
        print(f"Finished {video_path.name}. Enhanced video saved to: {output_file} (audio enhanced too)")
    else:
        print(f"Finished {video_path.name}. Enhanced video saved to: {output_file} (audio not enhanced)")

print(f"Processing complete for all files in the '{input_dir.name}' directory.")
