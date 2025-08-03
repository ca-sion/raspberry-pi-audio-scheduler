# audio_player.py
import os
import time
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv # <--- NOUVEAU !

# Charger les variables d'environnement depuis .env au démarrage de l'application
load_dotenv()

# --- Configuration de l'environnement ---
# Récupérer les variables depuis les variables d'environnement
IS_RASPBERRY_PI = os.getenv('IS_RASPBERRY_PI', 'False').lower() == 'true'
PI_PROJECT_ROOT = os.getenv('PI_PROJECT_ROOT', '/home/pi/pi_audio_player_app')

# --- Chemins des fichiers audio et logs ---
if IS_RASPBERRY_PI:
    AUDIO_BASE_DIR = os.path.join(PI_PROJECT_ROOT, "audio")
    PLANNER_LOG_FILE_PATH = os.path.join("/home/pi/logs", "audio_player.log") # Le dossier logs est directement dans /home/pi
else: # Environnement de développement (Mac)
    AUDIO_BASE_DIR = os.path.join(os.getcwd(), "audio")
    PLANNER_LOG_FILE_PATH = os.path.join(os.getcwd(), "temp_planner_log.log")

# Créez les dossiers audio et logs si inexistants
# Utilisez AUDIO_BASE_DIR et PLANNER_LOG_FILE_PATH qui sont désormais correctement définis
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

SCHEDULE = [
    # Heure de début, Heure de fin, Intervalle en minutes, Langues à jouer
    # Exemple pour le club d'athlétisme:
    ("18:15", "20:00", 15, ["fr", "en", "ar", "ti", "fa"]), 
    # Ajoutez d'autres plages horaires si nécessaire
    # ("20:00", "21:00", 30, ["fc_sion-fr", "fc_sion-de"]), # Exemple de messages spécifiques
]

last_played_times = {}
for i, (start, end, interval, langs) in enumerate(SCHEDULE):
    last_played_times[i] = datetime.min 

# Fonction de log pour le planificateur
def log_planner_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [PLANNER] {message}"
    
    # Écrit dans le fichier de log
    try:
        with open(PLANNER_LOG_FILE_PATH, "a") as f: 
            f.write(log_entry + "\n")
    except IOError as e:
        # Afficher l'erreur si l'écriture du log échoue
        print(f"[{timestamp}] [ERROR] Impossible d'écrire dans le fichier de log ({PLANNER_LOG_FILE_PATH}): {e}")
    print(log_entry) # Continue d'afficher dans le terminal aussi

def play_message(lang_code):
    file_path = AUDIO_FILES.get(lang_code)
    if file_path and os.path.exists(file_path):
        log_planner_message(f"Playing message in {lang_code}: {file_path}")
        try:
            if IS_RASPBERRY_PI:
                # Sur le Raspberry Pi, utilisez 'mpv' pour une meilleure gestion audio.
                # Assurez-vous que mpv est installé : sudo apt install mpv
                subprocess.run(["mpv", "--ao=alsa", file_path], check=True)
            else:
                # Sur Mac, utilisez 'afplay' pour la lecture audio.
                subprocess.run(["afplay", file_path], check=True) 
        except subprocess.CalledProcessError as e:
            log_planner_message(f"Erreur lors de la lecture pour {file_path}: {e}. Sortie: {e.stderr.decode().strip()}")
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
    while True:
        now = datetime.now()
        current_time = now.time()

        for i, (start_time_str, end_time_str, interval_minutes, languages_to_play) in enumerate(SCHEDULE):
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()

            is_within_schedule = False
            # Gérer les plages horaires qui chevauchent minuit
            if start_time <= end_time: 
                # Cas simple: 18:00 - 20:00
                if start_time <= current_time <= end_time:
                    is_within_schedule = True
            else: 
                # Cas chevauchant minuit: 22:00 - 02:00
                if current_time >= start_time or current_time <= end_time:
                    is_within_schedule = True

            if is_within_schedule:
                # Déclenchement basé sur la minute courante et l'intervalle
                if now.minute % interval_minutes == 0 and \
                   now.second < 5 and \
                   last_played_times[i] < now.replace(second=0, microsecond=0):
                    
                    log_planner_message(f"Déclenchement planifié pour l'intervalle {start_time_str}-{end_time_str}, toutes les {interval_minutes} minutes.")
                    for lang in languages_to_play:
                        play_message(lang)
                        time.sleep(1) # Petite pause entre chaque langue
                    
                    last_played_times[i] = now.replace(second=0, microsecond=0) 
                    log_planner_message(f"Messages planifiés joués à {now.strftime('%H:%M')}.")
                    time.sleep(5)  # Pause pour éviter des déclenchements multiples trop rapides

        time.sleep(1) 

if __name__ == "__main__":
    log_planner_message("Audio scheduler script started.")
    main_loop()