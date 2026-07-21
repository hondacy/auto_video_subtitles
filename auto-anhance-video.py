import subprocess
import cv2
import numpy as np
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
    if frame is None or frame.size == 0:
        return frame

    frame_rgb = frame.astype(np.uint8)
    bgr_frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    lab = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)

    lab = cv2.merge((l_channel, a_channel, b_channel))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.06, beta=8)

    hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.12, 0, 255).astype(np.uint8)
    enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)
    blurred = cv2.GaussianBlur(denoised, (0, 0), 1.2)
    enhanced = cv2.addWeighted(denoised, 1.12, blurred, -0.12, 0)

    return cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)


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
    temp_output_file = output_dir / f"{video_path.stem}_enhanced_temp{video_path.suffix}"
    output_file = output_dir / f"{video_path.stem}_enhanced{video_path.suffix}"

    temp_output_file.unlink(missing_ok=True)
    frame_count = process_video_stream(video_path, temp_output_file)

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

        merge_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_output_file),
            "-i",
            str(audio_output),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            str(output_file),
        ]
        subprocess.run(merge_cmd, check=True, capture_output=True)
        audio_ok = True
        audio_output.unlink(missing_ok=True)
        temp_output_file.unlink(missing_ok=True)
    except subprocess.CalledProcessError as exc:
        print(f"Warning: audio could not be processed for {video_path.name}: {exc.stderr.decode().strip()}")
        audio_ok = False
        if temp_output_file.exists():
            temp_output_file.replace(output_file)

    if audio_ok:
        print(f"Finished {video_path.name}. Enhanced video saved to: {output_file} ({frame_count} frames, audio enhanced too)")
    else:
        print(f"Finished {video_path.name}. Enhanced video saved to: {output_file} ({frame_count} frames, audio not enhanced)")

print(f"Processing complete for all files in the '{input_dir.name}' directory.")
