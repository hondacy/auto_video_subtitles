# Auto Video SAubtitles

Generates subtitles in a video using Whisper to generate and XX to input inside the video file
Requires Python 3.12


# Install
```
choco install ffmpeg --version=8.1.2
python -m venv .venv
.venv\Scripts\activate.bat
python.exe -m pip install --upgrade pip
pip install -U -r ./requirements.txt

```


# Prepare The Video File
    * Cut the video with lossless-cut (https://github.com/mifi/lossless-cut/releases/)
    * Put the file in proccessing folder (Proccessing)
    * Auto Enhance the video (Brigtnest, ...) with torchvision torchaudio:
    ```
    cd auto_video_subtitles
    python auto-enhance-video.py
    ```
    * Create subtitles:
    ```
    python auto-subtitles.py
    ```
