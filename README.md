# Auto Video SAubtitles

Generates subtitles in a video using Whisper to generate and XX to input inside the video file

# Install
```
choco install ffmpeg
python -m venv .venv
.venv\Scripts\activate.bat
python.exe -m pip install --upgrade pip
pip install -U openai-whisper
pip install torch torchvision torchcodec torchaudio
pip install opencv-python basicsr realesrgan


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
