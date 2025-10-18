# audio_player.py
import os
import time
import subprocess
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env au démarrage de l'application
load_dotenv()

# --- Configuration de l'environnement ---
IS_RASPBERRY_PI = os.getenv('IS_RASPBERRY_PI', 'False').lower() == 'true'
PI_PROJECT_ROOT = os.getenv('PI_PROJECT_ROOT', '/home/pi/app')
AUDIO_DEVICE = os.getenv('MPV_AUDIO_DEVICE', 'auto')

# --- Chemins des fichiers ---
if IS_RASPBERRY_PI:
    AUDIO_BASE_DIR = os.path.join(PI_PROJECT_ROOT, "audio")
    PLANNER_LOG_FILE_PATH = os.path.join(PI_PROJECT_ROOT, "logs", "audio_player.log")
    SCHEDULE_FILE_PATH = os.path.join(PI_PROJECT_ROOT, "schedule.json")
else: # Environnement de développement (Mac)
    AUDIO_BASE_DIR = os.path.join(os.getcwd(), "audio")
    PLANNER_LOG_FILE_PATH = os.path.join(os.getcwd(), "temp_planner_log.log")
    SCHEDULE_FILE_PATH = os.path.join(os.getcwd(), "schedule.json")

# Créez les dossiers audio et logs si inexistants
os.makedirs(AUDIO_BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PLANNER_LOG_FILE_PATH), exist_ok=True)

AUDIO_FILES = {
    "fr": os.path.join(AUDIO_BASE_DIR, "long-fr.mp3"),
    "en": os.path.join(AUDIO_BASE_DIR, "long-en.mp3"),
    "ar": os.path.join(AUDIO_BASE_DIR, "long-ar.mp3"),
    "ti": os.path.join(AUDIO_BASE_DIR, "long-ti.m4a"),
    "fa": os.path.join(AUDIO_BASE_DIR, "long-fa.mp3"),
    "fc_sion-fr": os.path.join(AUDIO_BASE_DIR, "fc_sion-fr.mp3"),
    "fc_sion-de": os.path.join(AUDIO_BASE_DIR, "fc_sion-de.mp3")
}

# Fonction de log pour le planificateur
def log_planner_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [PLANNER] {message}"
    try:
        with open(PLANNER_LOG_FILE_PATH, "a") as f:
            f.write(log_entry + "\n")
    except IOError as e:
        print(f"[{timestamp}] [ERROR] Impossible d'écrire dans le fichier de log ({PLANNER_LOG_FILE_PATH}): {e}")
    print(log_entry)

def load_schedule():
    """Charge la programmation depuis le fichier schedule.json."""
    try:
        with open(SCHEDULE_FILE_PATH, 'r') as f:
            data = json.load(f)
            if 'schedules' in data and isinstance(data['schedules'], list):
                log_planner_message(f"Programmation chargée avec succès depuis {SCHEDULE_FILE_PATH}.")
                return data['schedules']
            else:
                log_planner_message(f"Erreur de format dans {SCHEDULE_FILE_PATH}. Utilisation d'une programmation vide.")
                return []
    except FileNotFoundError:
        log_planner_message(f"Fichier de programmation non trouvé à {SCHEDULE_FILE_PATH}. Utilisation d'une programmation vide.")
        return []
    except json.JSONDecodeError:
        log_planner_message(f"Erreur de décodage JSON dans {SCHEDULE_FILE_PATH}. Le fichier est peut-être corrompu. Utilisation d'une programmation vide.")
        return []
    except Exception as e:
        log_planner_message(f"Erreur inattendue lors du chargement de la programmation : {e}. Utilisation d'une programmation vide.")
        return []

def play_message(lang_code):
    file_path = AUDIO_FILES.get(lang_code)
    if file_path and os.path.exists(file_path):
        log_planner_message(f"Playing message in {lang_code}: {file_path}")
        try:
            if IS_RASPBERRY_PI:
                command = ['mpv', '--no-terminal', '--really-quiet', file_path]
                if AUDIO_DEVICE != 'auto':
                    command.extend(['--audio-device', AUDIO_DEVICE])
                subprocess.run(command, check=True)
            else:
                subprocess.run(["afplay", file_path], check=True)
        except subprocess.CalledProcessError as e:
            log_planner_message(f"Erreur lors de la lecture pour {file_path}: {e}. Sortie: {e.stderr.decode().strip() if e.stderr else ''}")
        except FileNotFoundError:
            if IS_RASPBERRY_PI:
                log_planner_message("Erreur: 'mpv' n'est pas trouvé. Assurez-vous qu'il est installé sur le Pi avec 'sudo apt install mpv'.")
            else:
                log_planner_message("Erreur: 'afplay' n'est pas trouvé. (normalement présent sur Mac).")
        except Exception as e:
            log_planner_message(f"Erreur inattendue lors de la lecture audio de {file_path}: {e}")
    else:
        log_planner_message(f"Audio file not found for {lang_code}: {file_path}. Please check path and file existence.")

def main_loop():
    log_planner_message("Starting audio scheduler main loop...")
    schedule_list = load_schedule()
    last_played_times = {i: datetime.min for i in range(len(schedule_list))}

    while True:
        now = datetime.now()
        current_time = now.time()
        current_day = now.isoweekday()  # Lundi=1, Dimanche=7

        # Recharger la programmation toutes les 5 minutes pour prendre en compte les changements
        if now.minute % 5 == 0 and now.second == 0:
            new_schedule = load_schedule()
            if new_schedule != schedule_list:
                log_planner_message("Nouvelle programmation détectée, rechargement...")
                schedule_list = new_schedule
                last_played_times = {i: datetime.min for i in range(len(schedule_list))}

        for i, schedule_entry in enumerate(schedule_list):
            if not schedule_entry.get("enabled", False) or current_day not in schedule_entry.get("days", []):
                continue

            start_time_str = schedule_entry["start_time"]
            end_time_str = schedule_entry["end_time"]
            interval_minutes = schedule_entry["interval_minutes"]
            languages_to_play = schedule_entry["languages"]

            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()

            is_within_schedule = False
            if start_time <= end_time:
                if start_time <= current_time <= end_time:
                    is_within_schedule = True
            else: # Gérer les plages horaires qui chevauchent minuit (ex: 22:00-02:00)
                if current_time >= start_time or current_time <= end_time:
                    is_within_schedule = True

            if is_within_schedule:
                if now.minute % interval_minutes == 0 and now.second < 5 and last_played_times.get(i) < now.replace(second=0, microsecond=0):
                    log_planner_message(f"Déclenchement planifié pour l'intervalle {start_time_str}-{end_time_str}, toutes les {interval_minutes} minutes.")
                    for lang in languages_to_play:
                        play_message(lang)
                        time.sleep(1)
                    
                    last_played_times[i] = now.replace(second=0, microsecond=0)
                    log_planner_message(f"Messages planifiés joués à {now.strftime('%H:%M')}.")
                    time.sleep(5)

        time.sleep(1)

if __name__ == "__main__":
    log_planner_message("Audio scheduler script started.")
    main_loop()