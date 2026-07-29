#!/bin/bash

echo "Auto generates subtitles and burn them into the video using ffmpeg and whisper"

python3 auto-subtitles-generate.py
python3 auto-subtitles-insert-ass.py
