import os
from pathlib import Path

import torch
import torchvision.transforms.v2 as v2
from torchvision.models import get_model
import torchcodec
import torchaudio

input_dir = Path("proccessing")
if not input_dir.exists() or not input_dir.is_dir():
    raise FileNotFoundError(f"Input directory not found: {input_dir}")

output_dir = Path("processed")
output_dir.mkdir(exist_ok=True)

# Load a pre-trained Super Resolution or Auto-Enhance model (e.g., FSRCNN)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = get_model("fsrcnn", pretrained=True).to(device).eval()

# Process every file in the input directory
for video_path in sorted(input_dir.iterdir()):
    if not video_path.is_file():
        continue

    print(f"Processing: {video_path.name}")

    # 1. Video Loading and Decoding
    decoder = torchcodec.VideoDecoder(str(video_path))
    frames = decoder.get_batch(range(len(decoder)))  # Shape: (N, C, H, W)

    # 2. Frame Enhancement
    enhanced_frames = []
    transform = v2.Compose([
        v2.ToDtype(torch.float32, scale=True),
    ])

    for frame in frames:
        input_tensor = transform(frame).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(input_tensor)
        output_frame = output.squeeze(0).clamp(0, 1).cpu()
        enhanced_frames.append(output_frame)

    enhanced_video_tensor = torch.stack(enhanced_frames)

    # 3. Audio Extraction and Enhancement
    waveform, sample_rate = torchaudio.load(str(video_path))
    effects = [
        ["compand", "0.3,1", "6:-70,-60,-20", "-90", "-90", "0", "0", "0"],
        ["highpass", "200"]
    ]
    enhanced_waveform, new_sample_rate = torchaudio.sox_effects.apply_effects_tensor(
        waveform, sample_rate, effects
    )

    # 4. Save the Final Video and Audio
    output_file = output_dir / f"{video_path.stem}_enhanced{video_path.suffix}"
    print(f"Finished {video_path.name}. Enhanced output would be saved to: {output_file}")

print("Processing complete for all files in the 'proccessing' directory.")
