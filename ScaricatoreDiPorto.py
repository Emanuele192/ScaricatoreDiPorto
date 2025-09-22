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
import google.generativeai as genai
import time

'''print("--- DIAGNOSTICA AMBIENTE ---")
print("Python Executable:", sys.executable)
print("Versione yt-dlp:", yt_dlp.version.__version__)
print("--------------------------")'''
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
    # Definiamo una struttura di default completa
    default_config = {
        "appearance_mode": "system",
        "custom_ffmpeg_enabled": False,
        "custom_ffmpeg_path": default_ffmpeg_path,
        "gemini_api_key": "" # Aggiungiamo il campo per la chiave API
    }
    try:
        with open(config_path, "r") as file:
            # Carica la configurazione e la unisce a quella di default
            # per assicurare che tutte le chiavi siano presenti
            loaded = json.load(file)
            default_config.update(loaded)
            return default_config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print("File di configurazione non trovato o corrotto, uso valori di default:", e)
        return default_config

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

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scaricatore di porto 2.1 - The Ganzest")
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
                                                 variable=self.transcribe, onvalue=True, offvalue=False,
                                                 command=self.on_transcribe_change) # Aggiungiamo un comando qui
        self.transcribe_switch.grid(row=6, column=0, padx=20, pady=(10,5), sticky="w")
        # Frame per la scelta del motore e della lingua
        self.transcription_options_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.transcription_options_frame.grid(row=7, column=0, padx=20, pady=(5,0), sticky="ew")
        self.transcription_options_frame.grid_columnconfigure(0, weight=1)
        self.transcription_options_frame.grid_columnconfigure(1, weight=1)

        # ComboBox per scegliere il motore di trascrizione (VOSK o Gemini)
        self.engine_label = customtkinter.CTkLabel(self.transcription_options_frame, text="Engine:", font=my_font)
        self.engine_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.transcription_engine_combo = customtkinter.CTkComboBox(self.transcription_options_frame, font=my_font, 
                                                            values=["VOSK", "Gemini"],
                                                            command=self.on_engine_change)
        self.transcription_engine_combo.set("VOSK") # Imposta VOSK come default
        self.transcription_engine_combo.grid(row=0, column=1, sticky="ew")

        # ComboBox per la lingua (specifico per VOSK)
        self.language_label = customtkinter.CTkLabel(self.transcription_options_frame, text="Language (VOSK):", font=my_font)
        self.language_label.grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 10))
        self.transcription_language_combo = customtkinter.CTkComboBox(self.transcription_options_frame, font=my_font, 
                                                                values=list(VOSK_MODELS.keys()))
        self.transcription_language_combo.grid(row=1, column=1, sticky="ew", pady=(10, 0))

        self.gemini_options_frame = customtkinter.CTkFrame(self.advanced_tab, fg_color="transparent")
        self.gemini_options_frame.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.gemini_options_frame.grid_columnconfigure(1, weight=1)

        # ComboBox per la scelta del modello Gemini
        self.gemini_model_label = customtkinter.CTkLabel(self.gemini_options_frame, text="Gemini Model:", font=my_font)
        self.gemini_model_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(5,0))
        self.gemini_model_combo = customtkinter.CTkComboBox(self.gemini_options_frame, font=my_font, 
                                                            values=["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-1.5-flash"])
        self.gemini_model_combo.set("gemini-2.5-flash")
        self.gemini_model_combo.grid(row=0, column=1, sticky="ew", pady=(5,0))

        # ComboBox per la scelta della lingua di output
        self.gemini_lang_label = customtkinter.CTkLabel(self.gemini_options_frame, text="Output Language:", font=my_font)
        self.gemini_lang_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5,0))
        self.gemini_language_combo = customtkinter.CTkComboBox(self.gemini_options_frame, font=my_font, 
                                                            values=["Original Language", "Italian", "English", "French", "German", "Spanish"])
        self.gemini_language_combo.set("Original Language")
        self.gemini_language_combo.grid(row=1, column=1, sticky="ew", pady=(5,0))
        # Inizializza lo stato dei widget
        self.on_transcribe_change() 

        # --- Scheda SETTINGS--- #
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
        self.gemini_api_key_label = customtkinter.CTkLabel(
            self.settings_tab, text="Gemini API Key:", font=my_font
        )
        self.gemini_api_key_label.grid(row=5, column=0, columnspan=2, padx=10, pady=(15, 5), sticky="w")

        self.gemini_api_key_entry = customtkinter.CTkEntry(
            self.settings_tab,
            font=my_font,
            placeholder_text="Inserisci la tua chiave API di Google AI",
            show="*"
        )
        self.gemini_api_key_entry.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Popola il campo con la chiave salvata dal file config.json
        self.gemini_api_key_entry.insert(0, config.get("gemini_api_key", ""))

        # Pulsante per salvare tutte le impostazioni
        self.save_settings_button = customtkinter.CTkButton(
            self.settings_tab,
            text="Save Settings",
            font=my_font,
            command=self.save_settings # Collega il comando alla nuova funzione
        )
        self.save_settings_button.grid(row=7, column=0, columnspan=2, padx=10, pady=(20, 5))

        # Etichetta per confermare il salvataggio
        self.save_confirm_label = customtkinter.CTkLabel(self.settings_tab, text="", font=my_font, text_color="green")
        self.save_confirm_label.grid(row=8, column=0, columnspan=2, padx=10, pady=5)
        self.settings_tab.grid_rowconfigure(9, weight=1) # Aggiorna lo spacer

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

    def on_transcribe_change(self):
        if self.transcribe.get():
            self.transcription_engine_combo.configure(state="normal")
            self.engine_label.configure(state="normal")
            # Chiama on_engine_change per impostare lo stato corretto dei widget figli
            self.on_engine_change()
        else:
            self.transcription_engine_combo.configure(state="disabled")
            self.engine_label.configure(state="disabled")
            self.transcription_language_combo.configure(state="disabled")
            self.language_label.configure(state="disabled")


    def on_engine_change(self, choice=None):
        """Mostra/nasconde le opzioni specifiche per il motore di trascrizione scelto."""
        if not self.transcribe.get(): return

        engine = self.transcription_engine_combo.get()
        if engine == "VOSK":
            # Mostra opzioni VOSK e nascondi opzioni Gemini
            self.transcription_language_combo.grid()
            self.language_label.grid()
            self.gemini_options_frame.grid_remove()
        elif engine == "Gemini":
            # Mostra opzioni Gemini e nascondi opzioni VOSK
            self.transcription_language_combo.grid_remove()
            self.language_label.grid_remove()
            self.gemini_options_frame.grid()

    def save_settings(self):
        """
        Raccoglie tutti i valori dalla scheda Impostazioni e li salva in config.json.
        """
        print("Saving settings...")
        try:
            # Carica la configurazione corrente per non perdere eventuali dati non gestiti dall'UI
            current_config = load_config()

            # Aggiorna i valori con quelli presenti nell'interfaccia
            current_config["appearance_mode"] = self.appearance_mode_combo.get().lower()
            current_config["custom_ffmpeg_enabled"] = self.custom_ffmpeg_enabled.get()
            current_config["custom_ffmpeg_path"] = self.custom_ffmpeg_entry.get()
            current_config["gemini_api_key"] = self.gemini_api_key_entry.get()

            # Scrive il file di configurazione aggiornato
            with open("config.json", "w") as file:
                json.dump(current_config, file, indent=4)
            
            print("Settings saved successfully.")
            
            # Mostra un messaggio di conferma all'utente
            self.save_confirm_label.configure(text="Settings saved successfully!")
            # Fa scomparire il messaggio dopo 3 secondi
            self.save_confirm_label.after(3000, lambda: self.save_confirm_label.configure(text=""))

        except Exception as e:
            print(f"Error saving settings: {e}")
            self.save_confirm_label.configure(text="Error saving settings!", text_color="red")
            self.save_confirm_label.after(3000, lambda: self.save_confirm_label.configure(text=""))

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
            engine = app.transcription_engine_combo.get()
            print(f"Starting transcription with {engine}...")
            
            base, _ = os.path.splitext(title)
            output_txt = base + ".txt"

            if engine == "VOSK":
                app.download_label.configure(text="Transcription with VOSK started...")
                lang = app.transcription_language_combo.get()
                # Chiama la funzione originale di VOSK
                transcription = transcribe_file(title, lang=lang, output_txt_path=output_txt)
                app.download_label.configure(text="Download and VOSK transcription completed!")

            elif engine == "Gemini":
                app.download_label.configure(text="Transcription with Gemini started...")
                api_key = app.gemini_api_key_entry.get()
                if not api_key:
                    app.error_label.configure(text="Errore: Inserire la chiave API di Gemini nelle Impostazioni.")
                    return

                # Recupera i nuovi valori dall'interfaccia
                model_name = app.gemini_model_combo.get()
                target_language = app.gemini_language_combo.get()

                # Chiama la funzione aggiornata con i nuovi argomenti
                transcription = transcribe_file_gemini(
                    title, 
                    api_key=api_key, 
                    model_name=model_name,
                    target_language=target_language,
                    output_txt_path=output_txt
                )
                if transcription and "Errore" in transcription:
                    app.download_label.configure(text="Download completed. Transcription failed.")
                    app.error_label.configure(text=transcription)
                else:
                    app.download_label.configure(text="Download and Gemini transcription completed!")

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
        file_info = {'path': None}

        def progress_hook(d):
            if d['status'] == 'finished':
                # Salva il percorso completo del file quando il download è finito
                file_info['path'] = d.get('filename')
                app.progress_bar.set(1.0)
                app.download_label.configure(text="Download completed!")
                app.speed_label.configure(text="")
                app.download_button.configure(state='normal')

            elif d['status'] == 'downloading':
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

        # Otteniamo il titolo pulito prima del download per un nome file consistente
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'audio_file')
            clean_title = re.sub('[^a-zA-Z0-9_. -]', '-', title)

        ydl_opts = {
            'outtmpl': f"{percorso}/{clean_title}.%(ext)s",
            'format': 'bestaudio/best',
            'progress_hooks': [progress_hook],
            'ffmpeg_location': app.get_ffmpeg_path()
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Ora file_info['path'] contiene il percorso del file scaricato
        final_file_path = file_info['path']
        if not final_file_path:
            # Fallback nel caso in cui il nome file non sia stato catturato
            print("WARNING: Could not determine exact filename from hook. Reconstructing.")
            # Questa parte è un fallback, ma l'hook dovrebbe funzionare
            ext = ydl.extract_info(url, download=False).get('ext', 'opus')
            final_file_path = f"{percorso}/{clean_title}.{ext}"


        if app.encode.get():
            final_file_path = encode_audio(final_file_path)

        if app.play.get():
            auto_play(final_file_path)

        if app.transcribe.get():
            engine = app.transcription_engine_combo.get()
            print(f"Starting transcription with {engine}...")
            
            base, _ = os.path.splitext(final_file_path)
            output_txt = base + ".txt"

            if engine == "VOSK":
                app.download_label.configure(text="Transcription with VOSK started...")
                lang = app.transcription_language_combo.get()
                # Chiama la funzione di VOSK
                transcribe_file(final_file_path, lang=lang, output_txt_path=output_txt)
                app.download_label.configure(text="Download and VOSK transcription completed!")

            elif engine == "Gemini":
                app.download_label.configure(text="Transcription with Gemini started...")
                api_key = app.gemini_api_key_entry.get()
                if not api_key:
                    app.error_label.configure(text="Errore: Inserire la chiave API di Gemini nelle Impostazioni.")
                    return

                # Recupera i nuovi valori dall'interfaccia
                model_name = app.gemini_model_combo.get()
                target_language = app.gemini_language_combo.get()

                # Chiama la funzione aggiornata con i nuovi argomenti
                transcription = transcribe_file_gemini(
                    title, 
                    api_key=api_key, 
                    model_name=model_name,
                    target_language=target_language,
                    output_txt_path=output_txt
                )
                
                if transcription and "Errore" in transcription:
                    app.download_label.configure(text="Download completed. Transcription failed.")
                    app.error_label.configure(text=transcription)
                else:
                    app.download_label.configure(text="Download and Gemini transcription completed!")
                    
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

def extract_audio_for_transcription(video_path):
    """
    Estrae la traccia audio da un file video usando ffmpeg.
    Copia lo stream audio senza ricodificarlo per massima velocità e qualità.
    Restituisce il percorso del file audio temporaneo.
    """
    try:
        base, _ = os.path.splitext(video_path)
        # Usiamo .opus perché è un formato audio efficiente e di alta qualità
        audio_output_path = base + "_temp_audio.opus"
        
        print(f"Extracting audio from '{video_path}' to '{audio_output_path}'...")

        command = [
            'ffmpeg',
            '-y',             # Sovrascrive il file di output se esiste
            '-i', video_path,
            '-vn',            # -vn: No Video, ignora lo stream video
            '-acodec', 'copy', # -acodec copy: Copia lo stream audio senza ricodificarlo
            audio_output_path
        ]
        
        # Usiamo Popen per nascondere l'output di ffmpeg e non sporcare la console
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()

        if process.returncode != 0:
            # Se 'copy' fallisce (es. formato audio non supportato nel container .opus),
            # proviamo a ricodificare. È più lento ma più robusto.
            print("Audio copy failed, trying re-encoding to libopus...")
            command[-3] = '-c:a'
            command[-2] = 'libopus'
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed to extract audio: {stderr.decode('utf-8')}")

        print("Audio extracted successfully.")
        return audio_output_path
    
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        return None
# --- FUNZIONE DI TRASCRIZIONE CON GEMINI ---

def transcribe_file_gemini(file_path, api_key, model_name, target_language, output_txt_path=None):
    """
    Trascrive un file audio/video con Gemini. Se è un video, estrae solo l'audio
    prima dell'upload per efficienza.
    """
    # Determina se il file è un video (puoi aggiungere altre estensioni se necessario)
    is_video = file_path.lower().endswith(('.mp4', '.webm', '.mkv', '.mov', '.avi'))
    
    temp_audio_path = None
    path_to_upload = file_path

    try:
        if is_video:
            # Se è un video, estrai l'audio in un file temporaneo
            temp_audio_path = extract_audio_for_transcription(file_path)
            if not temp_audio_path:
                return "Errore: impossibile estrarre l'audio dal file video."
            path_to_upload = temp_audio_path
        
        
        genai.configure(api_key=api_key)

        print(f"Uploading file: {path_to_upload}")
        audio_file = genai.upload_file(path=path_to_upload)

        while audio_file.state.name == "PROCESSING":
            print("File processing, waiting 5s...")
            time.sleep(5)
            audio_file = genai.get_file(name=audio_file.name)

        if audio_file.state.name != "ACTIVE":
            raise ValueError(f"File could not be processed. State: {audio_file.state.name}")
        
        print(f"File is ACTIVE. Using model '{model_name}'...")
        
        prompt_parts = []
        if target_language == "Original Language":
            prompt_parts.append("Transcribe the following audio file into its original language. Include accurate punctuation.")
        else:
            prompt_parts.append(f"Transcribe the following audio file, and then translate the entire transcription into {target_language}.")
        
        prompt_parts.append(audio_file)

        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt_parts)
        genai.delete_file(audio_file.name)

        transcription = response.text
        
        # Salviamo il file .txt con il nome del file originale, non quello temporaneo
        if output_txt_path is None:
            base, _ = os.path.splitext(file_path) # Usa file_path originale qui
            output_txt_path = base + f"_gemini_{target_language}.txt"
        
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(transcription)

        print("Gemini transcription successful.")
        return transcription

    except Exception as e:
        print(f"ERROR during Gemini transcription: {e}")
        return f"Errore durante la trascrizione con Gemini: {e}"

    finally:
        # --- BLOCCO DI PULIZIA ---
        # Questo codice viene eseguito SEMPRE, anche se ci sono errori.
        if temp_audio_path and os.path.exists(temp_audio_path):
            print(f"Cleaning up temporary audio file: {temp_audio_path}")
            os.remove(temp_audio_path)

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



app.mainloop()
