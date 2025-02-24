import yt_dlp
import customtkinter
from tkinter import filedialog
import os
from datetime import timedelta
import threading
import subprocess
import re
import wmi
import shutil
import sys
import winreg
import json
import urllib.request
import zipfile
import wave
from vosk import Model, KaldiRecognizer

# Salvo il PATH originale (per ripristino o per comporre il nuovo PATH)
original_path = os.environ["PATH"]
# Determino il percorso corrente e le risorse
current_dir = os.path.dirname(os.path.realpath(__file__))
icona_dir = os.path.join(current_dir, "images\\icona64.ico")

# Percorso di default in cui è incluso ffmpeg nell'app
default_ffmpeg_path = os.path.join(current_dir, "ffmpeg-master-latest-win64-gpl-shared\\bin")

def get_system_theme():
    if sys.platform == "win32":
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            apps_use_light_theme = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
            winreg.CloseKey(key)
            return "dark" if apps_use_light_theme == 0 else "light"
        except Exception as e:
            print("Errore nel rilevamento del tema di sistema:", e)
            return "light"
    else:
        return "dark"

def load_config():
    config_path = "config.json"
    try:
        with open(config_path, "r") as file:
            return json.load(file)
    except Exception as e:
        print("Errore nel caricamento del config, uso valori di default:", e)
        return {
            "appearance_mode": "system",
            "custom_ffmpeg_enabled": False,
            "custom_ffmpeg_path": default_ffmpeg_path
        }

config = load_config()
appaerance_mode = config["appearance_mode"]
if appaerance_mode is not None and appaerance_mode != "system":
    print("Appearance mode found in config:", config["appearance_mode"])
    system_theme = config["appearance_mode"]
else:
    print("Appearance mode not found in config. Using system theme.")
    system_theme = get_system_theme()
    print("System theme:", system_theme)

customtkinter.set_default_color_theme("dark-blue")
customtkinter.set_appearance_mode(system_theme)

if shutil.which("ffmpeg") is None:
    os.environ["PATH"] += os.pathsep + default_ffmpeg_path
    print("ffmpeg non trovato nel PATH. Utilizzo il percorso incluso nell'app.")
else:
    print("ffmpeg trovato nel PATH. Utilizzo quello di sistema.")

def detect_gpu_vendor_wmi():
    try:
        c = wmi.WMI()
        for gpu in c.Win32_VideoController():
            gpu_name = gpu.Name.lower()
            if "nvidia" in gpu_name:
                return "nvidia"
            elif "amd" in gpu_name or "radeon" in gpu_name:
                return "amd"
            elif "intel" in gpu_name:
                return "intel"
    except Exception as e:
        print(f"Errore nel rilevamento GPU: {e}")
    return "generic"

vendor = detect_gpu_vendor_wmi()
print("GPU Vendor rilevato:", vendor)

def get_codec_options():
    vendor = detect_gpu_vendor_wmi()
    codecs = ["x264", "x265"]
    if vendor == "nvidia":
        codecs += ["Nvidia x264", "Nvidia x265"]
    elif vendor == "amd":
        codecs += ["AMD x264", "AMD x265"]
    elif vendor == "intel":
        codecs += ["Intel x264", "Intel x265"]
    return codecs

# Definizione dei modelli VOSK per le lingue supportate
VOSK_MODELS = {
    "English": {
        "folder": "vosk-model-small-en-us-0.15",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    },
    "Italian": {
        "folder": "vosk-model-small-it-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip"
    }
}

# Funzione per controllare e scaricare il modello VOSK per una determinata lingua (se non presente)
def check_and_download_model(lang):
    model_info = VOSK_MODELS.get(lang)
    if not model_info:
        print(f"Nessun modello disponibile per la lingua: {lang}")
        return
    model_dir = os.path.join(current_dir, model_info["folder"])
    if not os.path.exists(model_dir):
        print(f"Modello VOSK per {lang} non trovato. Download in corso...")
        zip_path = os.path.join(current_dir, "model.zip")
        urllib.request.urlretrieve(model_info["url"], zip_path)
        print("Estrazione del modello...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(current_dir)
        os.remove(zip_path)
        extracted_folder = os.path.join(current_dir, model_info["folder"])
        # Se il nome della cartella estratta non corrisponde, potresti doverlo gestire
        print(f"Modello VOSK per {lang} scaricato ed estratto in: {extracted_folder}")
    else:
        print(f"Modello VOSK per {lang} già presente.")

# Funzione di trascrizione che utilizza il modello in base alla lingua selezionata
def transcribe_file(file_path, lang="English", output_txt_path=None):
    check_and_download_model(lang)
    audio_file = os.path.join(current_dir, "temp_audio.wav")
    command = [
        "ffmpeg", "-y", "-i", file_path,
        "-ar", "16000", "-ac", "1", "-f", "wav", audio_file
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        wf = wave.open(audio_file, "rb")
    except Exception as e:
        print("Errore nell'apertura del file audio:", e)
        return None
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
        print("Il file audio non è nel formato richiesto.")
        wf.close()
        os.remove(audio_file)
        return None

    model_dir = os.path.join(current_dir, VOSK_MODELS[lang]["folder"])
    model = Model(model_dir)
    rec = KaldiRecognizer(model, wf.getframerate())
    
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()))
    results.append(json.loads(rec.FinalResult()))
    
    transcription = " ".join([res.get("text", "") for res in results])
    
    if output_txt_path is None:
        base, _ = os.path.splitext(file_path)
        output_txt_path = base + ".txt"
        
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)
    
    wf.close()
    os.remove(audio_file)
    return transcription

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scaricatore di porto 2.0 - The Ganzest")
        self.iconbitmap(icona_dir)
        self.geometry("450x600")
        self.minsize(400, 600)
        self.maxsize(800, 900)
        
        my_font = customtkinter.CTkFont(family="Helvetica", size=13)
        
        # Finestra principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Tabview
        self.tabview = customtkinter.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tabview.add("Download")
        self.tabview.add("Advanced")
        self.tabview.add("Settings")
        
        ###########################################
        # --- Scheda DOWNLOAD (layout invariato) ---
        self.download_tab = self.tabview.tab("Download")
        self.download_tab.grid_columnconfigure(0, weight=1)
        self.download_tab.grid_columnconfigure(1, weight=1)
        self.download_tab.grid_rowconfigure(0, weight=1)
        
        self.my_label = customtkinter.CTkLabel(
            self.download_tab, text="YouTube Video Downloader", font=("Impact",28)
        )
        self.my_label.grid(row=1, column=0, columnspan=2, pady=10, sticky="n")
        
        self.url_bar = customtkinter.CTkEntry(
            self.download_tab, font=my_font, placeholder_text="URL"
        )
        self.url_bar.grid(row=2, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        
        self.dir_frame = customtkinter.CTkFrame(self.download_tab, fg_color="transparent")
        self.dir_frame.grid(row=3, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        self.dir_frame.grid_columnconfigure(0, weight=1)
        self.folder = customtkinter.CTkEntry(
            self.dir_frame, font=my_font, placeholder_text="Default: internal/output"
        )
        self.folder.grid(row=0, column=0, padx=8, sticky="ew")
        self.ask_dir = customtkinter.CTkButton(
            self.dir_frame, text="Browse Folder", command=self.browse_folder, font=my_font
        )
        self.ask_dir.grid(row=0, column=1, padx=8)
        
        self.combo_frame = customtkinter.CTkFrame(self.download_tab, fg_color="transparent")
        self.combo_frame.grid(row=4, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        self.combo_frame.grid_columnconfigure(0, weight=1)
        self.combo = customtkinter.CTkComboBox(self.combo_frame, font=my_font, values=["Select Resolution"])
        self.combo.grid(row=0, column=0, padx=15, sticky="ew")
        self.audio_var = customtkinter.BooleanVar()
        self.audio_check = customtkinter.CTkSwitch(
            self.combo_frame, text="Audio Only", font=my_font,
            onvalue=True, offvalue=False, variable=self.audio_var
        )
        self.audio_check.grid(row=0, column=1, padx=10)
        self.audio_var.trace('w', self.on_audio_var_change)
        
        self.button_frame = customtkinter.CTkFrame(self.download_tab, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_load = customtkinter.CTkButton(
            self.button_frame, text="Load", font=my_font, command=self.init_submit
        )
        self.button_load.grid(row=0, column=0, padx=10, sticky="ew")
        self.clear_button = customtkinter.CTkButton(
            self.button_frame, text="Clear", command=self.clear_bar, font=my_font
        )
        self.clear_button.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.download_button = customtkinter.CTkButton(
            self.download_tab, text="Download", font=my_font, command=self.init_download
        )
        self.download_button.grid(row=6, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        self.download_button.configure(state='disabled')
        
        self.error_label = customtkinter.CTkLabel(
            self.download_tab, text="", text_color="red", font=my_font
        )
        self.error_label.grid(row=7, column=0, columnspan=2, pady=5, padx=20, sticky="w")
        
        # Stato download: due label affiancate (sinistra: percentuale, destra: velocità)
        self.status_frame = customtkinter.CTkFrame(self.download_tab, fg_color="transparent")
        self.status_frame.grid(row=8, column=0, columnspan=2, pady=5, padx=20, sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_columnconfigure(1, weight=1)
        self.download_label = customtkinter.CTkLabel(self.status_frame, text="", text_color="green", font=my_font)
        self.download_label.grid(row=0, column=0, sticky="w")
        self.speed_label = customtkinter.CTkLabel(self.status_frame, text="", text_color="blue", font=my_font)
        self.speed_label.grid(row=0, column=1, sticky="e")
        
        self.progress_bar = customtkinter.CTkProgressBar(self.download_tab)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=9, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        
        self.download_tab.grid_rowconfigure(10, weight=1)
        
        ###########################################
        # --- Scheda ADVANCED (layout riorganizzato) ---
        self.advanced_tab = self.tabview.tab("Advanced")
        self.advanced_tab.grid_columnconfigure(0, weight=1)
        self.advanced_tab.grid_rowconfigure(8, weight=1)  # Spacer inferiore
        
        # Encode section
        self.encode_switch_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.encode_switch_frame.grid(row=1, column=0, padx=20, pady=(10,5), sticky="ew")
        self.encode_switch_frame.grid_columnconfigure(0, weight=1)
        self.encode = customtkinter.BooleanVar()
        self.encode_button = customtkinter.CTkSwitch(
            self.encode_switch_frame, text="Encode", font=my_font,
            variable=self.encode, onvalue=True, offvalue=False, command=self.on_encode_change
        )
        self.encode_button.grid(row=0, column=0, sticky="w")
        
        # Codec options (menu per codec video e audio) – sempre visibili
        self.codec_options_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.codec_options_frame.grid(row=2, column=0, padx=20, pady=(5,10), sticky="ew")
        self.codec_options_frame.grid_columnconfigure(0, weight=1)
        self.codec_options_frame.grid_columnconfigure(1, weight=1)
        self.encode_box = customtkinter.CTkComboBox(self.codec_options_frame, font=my_font, values=get_codec_options())
        self.encode_box.grid(row=0, column=0, padx=10, sticky="ew")
        self.encode_audio_box = customtkinter.CTkComboBox(self.codec_options_frame, font=my_font, values=["aac", "mp3", "opus"])
        self.encode_audio_box.grid(row=0, column=1, padx=10, sticky="ew")
        
        # Trim section
        self.trim_switch_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.trim_switch_frame.grid(row=3, column=0, padx=20, pady=(10,5), sticky="ew")
        self.trim_switch_frame.grid_columnconfigure(0, weight=1)
        self.trim = customtkinter.BooleanVar()
        self.trim_button = customtkinter.CTkSwitch(
            self.trim_switch_frame, text="Trim", font=my_font,
            variable=self.trim, onvalue=True, offvalue=False, command=self.on_trim_change
        )
        self.trim_button.grid(row=0, column=0, sticky="w")
        
        # Trim options (start ed end) – disposte orizzontalmente
        self.trim_options_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.trim_options_frame.grid(row=4, column=0, padx=20, pady=(5,10), sticky="ew")
        self.trim_options_frame.grid_columnconfigure(0, weight=1)
        self.trim_options_frame.grid_columnconfigure(1, weight=1)
        self.trim_start = customtkinter.CTkEntry(self.trim_options_frame, font=my_font, placeholder_text="Start: 00:00:00.000")
        self.trim_start.grid(row=0, column=0, padx=10, sticky="ew")
        self.trim_end = customtkinter.CTkEntry(self.trim_options_frame, font=my_font, placeholder_text="End: 00:00:00.000")
        self.trim_end.grid(row=0, column=1, padx=10, sticky="ew")
        
        # Auto Play section
        self.auto_play_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.auto_play_frame.grid(row=5, column=0, padx=20, pady=(10,5), sticky="ew")
        self.auto_play_frame.grid_columnconfigure(0, weight=1)
        self.play = customtkinter.BooleanVar()
        self.play_check = customtkinter.CTkSwitch(self.auto_play_frame, text="Auto Play", font=my_font,
                                                    variable=self.play, onvalue=True, offvalue=False)
        self.play_check.grid(row=0, column=0, sticky="w")
        
        # Transcribe section (toggle)
        self.transcribe = customtkinter.BooleanVar()
        self.transcribe_switch = customtkinter.CTkSwitch(self.advanced_tab, text="Transcribe", font=my_font,
                                                         variable=self.transcribe, onvalue=True, offvalue=False)
        self.transcribe_switch.grid(row=6, column=0, padx=20, pady=(10,5), sticky="w")
        # Transcription language selection
        self.transcription_language_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.transcription_language_frame.grid(row=7, column=0, padx=20, pady=(5,10), sticky="ew")
        self.transcription_language_frame.grid_columnconfigure(0, weight=1)
        self.transcription_language_frame.grid_columnconfigure(1, weight=1)
        self.transcription_language_label = customtkinter.CTkLabel(self.transcription_language_frame, text="Transcription Language:", font=my_font)
        self.transcription_language_label.grid(row=0, column=0, sticky="w")
        self.transcription_language_combo = customtkinter.CTkComboBox(self.transcription_language_frame, font=my_font, values=list(VOSK_MODELS.keys()))
        self.transcription_language_combo.grid(row=0, column=1, sticky="e")
        
        ###########################################
        # --- Scheda SETTINGS (invariata) ---
        self.settings_tab = self.tabview.tab("Settings")
        self.settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_tab.grid_columnconfigure(1, weight=1)
        self.settings_tab.grid_rowconfigure(5, weight=1)
        
        self.custom_ffmpeg_enabled = customtkinter.BooleanVar(value=config.get("custom_ffmpeg_enabled", False))
        self.custom_ffmpeg_check = customtkinter.CTkCheckBox(
            self.settings_tab,
            text="Custom ffmpeg path",
            font=my_font,
            variable=self.custom_ffmpeg_enabled
        )
        self.custom_ffmpeg_check.grid(row=1, column=0, columnspan=2, padx=10, pady=(10,5), sticky="w")
        
        self.custom_ffmpeg_entry = customtkinter.CTkEntry(
            self.settings_tab,
            font=my_font,
            placeholder_text="Percorso a ffmpeg",
            width=300
        )
        self.custom_ffmpeg_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.custom_ffmpeg_entry.insert(0, config.get("custom_ffmpeg_path", default_ffmpeg_path))
        self.custom_ffmpeg_browse = customtkinter.CTkButton(
            self.settings_tab,
            text="Browse",
            font=my_font,
            command=self.browse_custom_ffmpeg
        )
        self.custom_ffmpeg_browse.grid(row=2, column=1, padx=10, pady=5, sticky="e")
        
        self.appearance_label = customtkinter.CTkLabel(
            self.settings_tab, text="Appearance Mode:", font=my_font
        )
        self.appearance_label.grid(row=3, column=0, padx=10, pady=(10,5), sticky="w")
        self.appearance_mode_combo = customtkinter.CTkComboBox(
            self.settings_tab, font=my_font, values=["System", "Dark", "Light"]
        )
        self.appearance_mode_combo.grid(row=3, column=1, padx=10, pady=(10,5), sticky="e")
        
        self.apply_theme_button = customtkinter.CTkButton(
            self.settings_tab, text="Apply Theme", font=my_font, command=self.apply_theme
        )
        self.apply_theme_button.grid(row=4, column=0, columnspan=2, padx=10, pady=(10,5))
    
    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        self.folder.delete(0, 'end')
        self.folder.insert(0, folder_path)
        print("Cartella download scelta:", folder_path)
    
    def browse_custom_ffmpeg(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.custom_ffmpeg_entry.delete(0, 'end')
            self.custom_ffmpeg_entry.insert(0, folder_path)
            print("Percorso custom ffmpeg scelto:", folder_path)
            config = load_config()
            config["custom_ffmpeg_enabled"] = self.custom_ffmpeg_enabled.get()
            config["custom_ffmpeg_path"] = folder_path
            with open("config.json", "w") as file:
                json.dump(config, file, indent=4)
            print("Configurazione aggiornata con il percorso custom di ffmpeg.")
    
    def get_ffmpeg_path(self):
        if self.custom_ffmpeg_enabled.get():
            custom_path = self.custom_ffmpeg_entry.get().strip()
            os.environ["PATH"] = custom_path + os.pathsep + original_path
            return custom_path
        else:
            if shutil.which("ffmpeg") is None:
                os.environ["PATH"] = default_ffmpeg_path + os.pathsep + original_path
                return default_ffmpeg_path
            else:
                return shutil.which("ffmpeg")
    
    def apply_theme(self):
        mode = self.appearance_mode_combo.get().lower()
        customtkinter.set_appearance_mode(mode)
        self.update_idletasks()
        config = load_config()
        config["appearance_mode"] = mode
        with open("config.json", "w") as file:
            json.dump(config, file, indent=4)
        print(f"Applied appearance mode: {mode}")
    
    # Se "Trim" viene attivato, forzo l'attivazione di "Encode"; se "Encode" viene disattivato, disattivo anche "Trim".
    def on_trim_change(self, *args):
        if self.trim.get():
            if not self.encode.get():
                self.encode.set(True)
    
    def on_encode_change(self, *args):
        if not self.encode.get():
            self.trim.set(False)
    
    def on_audio_var_change(self, *args):
        print("Audio Only:", self.audio_var.get())
        if self.audio_var.get() and self.url_bar.get() != "":
            self.combo.configure(state='disabled')
            self.download_button.configure(state='normal')
        elif (self.combo.get() == "Select Resolution" or self.url_bar.get() == ""):
            self.combo.configure(state='normal')
            self.download_button.configure(state='disabled')
    
    def clear_bar(self):
        self.url_bar.delete(0, 'end')
        self.combo.configure(values=["Select Resolution"])
        self.combo.set("Select Resolution")
        self.download_button.configure(state='disabled')
        self.error_label.configure(text="")
        self.download_label.configure(text="")
        self.speed_label.configure(text="")
        self.progress_bar.set(0)
        self.combo.configure(state='normal')
        self.audio_var.set(False)
        self.encode.set(False)
        self.trim.set(False)
        print("Cleared")
    
    def init_submit(self):
        threading.Thread(target=submit).start()
    
    def init_download(self):
        self.error_label.configure(text="")
        self.download_label.configure(text="")
        self.speed_label.configure(text="")
        self.progress_bar.set(0)
        if self.audio_var.get():
            threading.Thread(target=download_audio).start()
        else:
            threading.Thread(target=download_completo).start()

app = App()
video_title = r""
video_ext = r""

def auto_play(percorso):
    os.startfile(percorso)
    print("File opened:", percorso)

def get_available_resolutions(video_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'simulate': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'skip_download': True,
        'outtmpl': 'dummy'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            global video_title
            video_title = info_dict.get('title', None)
            video_ext = info_dict.get('ext', None)
            print("Titolo:", video_title)
            print("Estensione:", video_ext)
            formats = info_dict.get('formats', None)
            if not formats:
                raise Exception("Nessuna risoluzione disponibile. Verifica la correttezza del link")
            resolutions = set()
            for f in formats:
                if f.get('height') and f['height'] >= 144:
                    resolutions.add(f['height'])
            sorted_resolutions = sorted(resolutions, reverse=True)
            resolutions_with_p = [f"{resolution}p" for resolution in sorted_resolutions]
            return resolutions_with_p
    except Exception as e:
        print(f"Errore: {str(e)}")

def submit():
    try:
        if app.audio_check.get():
            app.combo.configure(state='disabled')
        else:
            app.combo.configure(state='normal')
        url = app.url_bar.get()
        print("URL:", url)
        available_resolutions = get_available_resolutions(url)
        app.combo.configure(values=available_resolutions)
        app.download_button.configure(state='normal')
    except Exception as e:
        app.error_label.configure(text=f"Errore: {e}")

def download_completo():
    try:
        ffmpeg_used = app.get_ffmpeg_path()
        print("DOWNLOAD COMPLETO")
        print("Using ffmpeg from:", ffmpeg_used)
        
        global video_title, video_ext
        url = app.url_bar.get()
        resolution = app.combo.get()
        resolution = resolution[:-1]
        percorso = app.folder.get()
        video_title_clean = re.sub('[^a-zA-Z0-9_. -]', '-', video_title)
        print("Clean title:", video_title_clean)
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                if total:
                    progress = downloaded / total
                    percentage = int(progress * 100)
                    app.progress_bar.set(progress)
                    left_text = f"Downloading video... {percentage}%"
                else:
                    left_text = "Downloading video..."
                speed = d.get('speed')
                if speed is not None:
                    speed_mbps = speed * 8 / (1024*1024)
                    right_text = f"Speed: {speed_mbps:.2f} Mbps"
                else:
                    right_text = "Speed: -"
                app.download_label.configure(text=left_text)
                app.speed_label.configure(text=right_text)
                app.download_button.configure(state='disabled')
            elif d['status'] == 'error':
                app.error_label.configure(text="Download failed!")
                app.download_button.configure(state='normal')
            elif d['status'] == 'finished':
                app.progress_bar.set(1.0)
                app.download_label.configure(text="Download completed!")
                app.speed_label.configure(text="")
                app.download_button.configure(state='normal')
        ydl_opts = {
            'outtmpl': f"{percorso}/{video_title_clean}.%(ext)s",
            'format': f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]',
            'progress_hooks': [progress_hook],
            'ffmpeg_location': ffmpeg_used
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            info_dict = ydl.extract_info(url, download=False)
            video_ext = info_dict.get('ext', None)
            print("Estensione:", video_ext)
        title = f"{percorso}/{video_title_clean}.{video_ext}"
        print("Downloaded file:", title)
        if app.encode.get():
            title = encode_video(title)
        if app.play.get():
            auto_play(title)
        if app.transcribe.get():
            app.download_label.configure(text="Transcription started...")
            lang = app.transcription_language_combo.get()
            base, _ = os.path.splitext(title)
            output_txt = base + ".txt"
            transcription = transcribe_file(title, lang=lang, output_txt_path=output_txt)
            app.download_label.configure(text="Download and transcription completed!")
    except Exception as e:
        app.error_label.configure(text=f"Errore: {e}")
        app.download_label.configure(text="")
        app.download_button.configure(state='normal')
        return

def video_format():
    match app.encode_box.get():
        case "x264":
            codec = "libx264"
        case "x265":
            codec = "libx265"
        case "AMD x264":
            codec = "h264_amf"
        case "AMD x265":
            codec = "hevc_amf"
        case "Nvidia x264":
            codec = "h264_nvenc"
        case "Nvidia x265":
            codec = "hevc_nvenc"
        case "Intel x264":
            codec = "h264_qsv"
        case "Intel x265":
            codec = "hevc_qsv"
        case _:
            codec = 'copy'
    return codec

def audio_format():
    match app.encode_audio_box.get():
        case "aac":
            audio_codec = "aac"
            ext = audio_codec
        case "mp3":
            ext = "mp3"
            audio_codec = "libmp3lame"
        case "opus":
            ext = "ogg"
            audio_codec = "libopus"
        case _:
            audio_codec = "copy"
    return audio_codec, ext

def encode_video(file):
    start, end = cut_time()
    audio_codec = audio_format()[0]
    video_codec = video_format()
    output_file = file[:-4] + "-encoded.mp4"
    print("File to encode:", file)
    if shutil.which("ffmpeg") is None:
        custom_path = app.get_ffmpeg_path()
        os.environ["PATH"] += os.pathsep + custom_path
        print("Updated PATH with custom ffmpeg:", custom_path)
    command = [
        'ffmpeg',
        '-i', file,
        '-ss', start,
        '-to', end,
        '-c:v', video_codec,
        '-c:a', audio_codec,
        output_file
    ]
    subprocess.run(command)
    os.remove(file)
    return output_file

def cut_time():
    url = app.url_bar.get()
    start = app.trim_start.get()
    end = app.trim_end.get()
    if start == "":
        start = "00:00:00.000"
    if end == "":
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            end_sec = info_dict.get('duration')
            end = str(timedelta(seconds=end_sec))
            print("Duration:", end)
    return start, end

def download_audio():
    try:
        url = app.url_bar.get()
        percorso = app.folder.get()
        title = None
        def progress_hook(d):
            nonlocal title
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                if total:
                    progress = downloaded / total
                    percentage = int(progress * 100)
                    app.progress_bar.set(progress)
                    left_text = f"Downloading audio... {percentage}%"
                else:
                    left_text = "Downloading audio..."
                speed = d.get('speed')
                if speed is not None:
                    speed_mbps = speed * 8 / (1024*1024)
                    right_text = f"Speed: {speed_mbps:.2f} Mbps"
                else:
                    right_text = "Speed: -"
                app.download_label.configure(text=left_text)
                app.speed_label.configure(text=right_text)
                app.download_button.configure(state='disabled')
            elif d['status'] == 'error':
                app.error_label.configure(text="Download failed!")
                app.download_button.configure(state='normal')
            elif d['status'] == 'finished':
                app.progress_bar.set(1.0)
                app.download_label.configure(text="Download completed!")
                app.speed_label.configure(text="")
                app.download_button.configure(state='normal')
                title = d.get('filename', '').split('/')[-1]
        ydl_opts = {
            'outtmpl': f"{percorso}/%(title)s.opus",
            'format': 'bestaudio/worst',
            'progress_hooks': [progress_hook],
            'ffmpeg_location': app.get_ffmpeg_path()
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if app.encode.get():
            title = encode_audio(title)
        if app.play.get():
            auto_play(title)
        if app.transcribe.get():
            app.download_label.configure(text="Transcription started...")
            lang = app.transcription_language_combo.get()
            base, _ = os.path.splitext(title)
            output_txt = base + ".txt"
            transcription = transcribe_file(title, lang=lang, output_txt_path=output_txt)
            app.download_label.configure(text="Download and transcription completed!")
    except Exception as e:
        app.error_label.configure(text=f"Errore: {e}")
        app.download_label.configure(text="")
        app.download_button.configure(state='normal')
        return

def encode_audio(file):
    start, end = cut_time()
    audio_codec, ext = audio_format()
    output_file = file[:-4] + "-encoded." + ext
    if shutil.which("ffmpeg") is None:
        custom_path = app.get_ffmpeg_path()
        os.environ["PATH"] += os.pathsep + custom_path
        print("Updated PATH with custom ffmpeg:", custom_path)
    command = [
        'ffmpeg',
        '-i', file,
        '-ss', start,
        '-to', end,
        '-c:a', audio_codec,
        output_file
    ]
    subprocess.run(command)
    os.remove(file)
    return output_file

app.mainloop()
