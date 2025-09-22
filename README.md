# Scaricatore Di Porto – The Ganzest

A powerful desktop application to download and transcribe video and audio from various sources, featuring both online (Google Gemini) and offline (VOSK) transcription engines.

## Features

-   **Download Video & Audio:** Download videos in your desired resolution or extract audio-only tracks.
-   **Dual Transcription Engines:**
    -   **Google Gemini (Online):** High-accuracy transcription with support for translation into multiple languages and model selection (1.5 Pro/Flash).
    -   **VOSK (Offline):** Fast, private, offline transcription with no internet connection required.
-   **Encoding & Trimming:** Convert downloaded files and cut unwanted sections.
-   **Modern GUI:** User-friendly and theme-aware interface built with CustomTkinter.
-   **Auto Play:** Automatically play the file after processing is complete.

## Requirements

-   **Python 3.9+**
-   **FFmpeg:** Essential for downloading, encoding, and audio extraction.
-   Other Python dependencies are listed in `requirements.txt`.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Emanuele192/ScaricatoreDiPorto.git
    cd ScaricatoreDiPorto
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    ```
3.  **Activate the virtual environment:**
    -   **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
    -   **Linux/macOS:** `source .venv/bin/activate`
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before the first use, you need to configure a few things:

1.  **FFmpeg:** The app automatically looks for FFmpeg in your system's PATH. If not found, you must manually select the path to your FFmpeg `bin` folder in the **Settings** tab.
2.  **VOSK Models:** VOSK models are downloaded automatically on first use. The transcription process will pause until the required language model is downloaded and extracted into the application's root folder.
3.  **Gemini API Key:** To use the Gemini engine, you must provide your own Google AI API key.
    -   Get a key from **[Google AI Studio](https://aistudio.google.com/)**.
    -   Paste the key into the **Settings** tab and click **Save Settings**.

## Usage

To run the application, execute the following command from the project directory:
```bash
python ScaricatoreDiPorto.py
```
If you have downloaded a release, simply run the executable file.

## A Note on Antivirus

Antivirus software may flag the executable as a potential threat. This is a common false positive for applications built with PyInstaller, as the program is not signed. The application is safe to use, and the full source code is available here for review.

## Disclaimer

This program has been developed for educational purposes only. The author does not take any responsibility for any misuse of the software. Downloading content may violate a website's terms of service. Users are solely responsible for ensuring their actions comply with all applicable laws and website policies.
