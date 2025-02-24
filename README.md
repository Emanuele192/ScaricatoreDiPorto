# Scaricatore Di Porto – The Ganzest

This project is a Python application that downloads and transcribes YouTube (but not only) videos (or audio), with features for encoding, trimming, and auto-playing the downloaded file. It also supports offline transcription in multiple languages using VOSK.

## Features

- **YouTube Download:** Download videos at a selected resolution or download only the audio.
- **Encoding and Trimming:** Options to convert the downloaded file and trim unwanted sections.
- **Auto Play:** Automatically play the file after processing.
- **Offline Transcription:** Transcribe the entire video (or audio) in English or Italian using VOSK.
- **Modern GUI:** Built with CustomTkinter for a modern, user-friendly interface.

## Requirements

- **Python 3.7+**
- **FFMPEG**
- **Required Python packages:**  
  - yt-dlp
  - customtkinter
  - WMI
  - vosk

## Installation and Setup
- *NOTE: the program has been tested with python 3.11.9*
- **Clone the Repository:**
  ```bash
  git clone https://github.com/Emanuele192/ScaricatoreDiPorto.git
  cd ScaricatoreDiPorto
- **(Optional) Create a Virtual Environment:**
  ```bash
  python -m venv venv
  ```
  Activate the environment: 
    ```bash
  venv\Scripts\activate
- ** Install Dependencies:**
  ```bash
  pip install -r requirements.txt

## Usage
To run the application, simply execute:
  ```bash
  python ScaricatoreDiPorto.py
  ```
**If you have downloaded the release the only thing to do is to run the executable**

**The program automatically searches for a version of ffmpeg in the system path, if it is not present you must select a build (up to the bin folder) manually from the "settings" section**

## Transcription
The application supports transcription in English and Italian.
- In the Advanced tab, enable the Transcribe toggle and choose the desired language from the dropdown menu.
- If the selected VOSK model is not present, the program will download and extract it automatically. Once downloaded, the model will be stored in a folder (named according to the model) in the project directory.
- The transcription is saved in a text file with the same base name as the downloaded video (e.g., video.mp4 becomes video.txt).

## Notes
- **Virtual Environment**: It is recommended to use a virtual environment to avoid conflicts with globally installed packages.
- **Offline Transcription**: The transcription process extracts the audio (converted to WAV, 16 kHz, mono) and processes the entire file to ensure even long videos are fully transcribed.
- **Resource Considerations**: The VOSK models can be large. The program downloads the model on the first run and reuses it afterward.
- **The program automatically searches for a version of ffmpeg in the system path, if it is not present you must select a build (up to the bin folder) manually from the "settings" section**
*Antivirus may detect some components as viruses, this may be due to pyinstaller and the fact that the program is not signed, THE PROGRAM HAS NO VIRUSES and also the source code is available here.*

## Disclaimer
*This program has been developed for educational purposes only. The author does not take any responsibility for any misuse of the software. Downloading videos from websites may violate the site's policies or terms of service. Users are solely responsible for ensuring that their actions comply with all applicable laws and website policies.*
