# Auto Video Subtitles

Generate subtitles for all supported media files in `proccessing`, enhance video, and insert subtitle tracks into output videos.

Requires Python 3.12

## Install
```
choco install ffmpeg --version=8.1.2
cd auto_video_subtitles
python -m venv .venv
.venv\Scripts\activate.bat
python.exe -m pip install --upgrade pip
pip install -U -r requirements.txt
```

## Workflow

1. Prepare The Video File:
    Cut the video with lossless-cut (https://github.com/mifi/lossless-cut/releases/)
2. Place all source media files in the `proccessing` directory.
3. Run video enhancement for all supported files:
   ```
   python auto-enhance-video.py
   ```
4. Copy enhanced files back to "proccessing" folder
5. Generate subtitle `.srt` files for all supported files in `proccessing`:
   ```
   python auto-subtitles.py
   ```
6. Insert subtitles into video files using the YAML config:
   ```
   python auto-subtitles-insert.py
   ```

## Notes
- `auto-subtitles.py` processes all supported media files found in `proccessing` by default.
- `auto-subtitles-insert.py` looks for matching `.srt` files in the subtitle directory and outputs subtitled video files to `proccessing/with_subtitles` by default.
- `auto-subtitles.yaml` contains config for FFmpeg, burning in subtitles, and output directories.
