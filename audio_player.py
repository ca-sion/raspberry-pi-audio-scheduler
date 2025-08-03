# audio_player.py
import os
import time
import subprocess
from datetime import datetime, timedelta

# Chemin du fichier de log
LOG_FILE_PATH = "/home/pi/logs/audio_player.log" # Chemin absolu pour les logs du planificateur
LOG_DIR = os.path.dirname(LOG_FILE_PATH) # Répertoire des logs

# Créez le dossier audio si inexistant. Pour le déploiement sur Pi, assurez-vous que ce chemin est correct.
AUDIO_DIR = "/home/pi/audio" 
os.makedirs(AUDIO_DIR, exist_ok=True) 

# Créer le répertoire des logs si inexistant
os.makedirs(LOG_DIR, exist_ok=True)

AUDIO_FILES = {
    "fr": os.path.join(AUDIO_DIR, "long-fr.mp3"),
    "en": os.path.join(AUDIO_DIR, "long-en.mp3"),
    "ar": os.path.join(AUDIO_DIR, "long-ar.mp3"),
    "ti": os.path.join(AUDIO_DIR, "long-ti.m4a"),
    "fa": os.path.join(AUDIO_DIR, "long-fa.mp3"),
}

SCHEDULE = [
# Heure de début, Heure de fin, Intervalle en minutes, Langues à jouer
    ("18:15", "20:00", 15, ["fr", "en", "ar", "ti", "fa"]),
]

last_played_times = {}
for i, (start, end, interval, langs) in enumerate(SCHEDULE):
    last_played_times[i] = datetime.min 

# Fonction de log pour le planificateur
def log_planner_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [PLANNER] {message}"
    
    # Écrit dans le fichier de log
    with open(LOG_FILE_PATH, "a") as f: # "a" pour append (ajouter à la fin)
        f.write(log_entry + "\n")
    print(log_entry) # Continue d'afficher dans le terminal aussi

def play_message(lang_code):
    file_path = AUDIO_FILES.get(lang_code)
    if file_path and os.path.exists(file_path):
        log_planner_message(f"Playing message in {lang_code}: {file_path}")
        try:
            # Utilisez 'mpv' pour une meilleure gestion sur Raspberry Pi avec ALSA.
            # Assurez-vous que mpv est installé : sudo apt install mpv
            subprocess.run(["mpv", "--ao=alsa", file_path], check=True) # check=True lèvera une erreur si la commande échoue
        except subprocess.CalledProcessError as e:
            log_planner_message(f"Erreur lors de la lecture avec mpv pour {file_path}: {e}")
        except FileNotFoundError:
            log_planner_message("Erreur: 'mpv' n'est pas trouvé. Assurez-vous qu'il est installé.")
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

            # Vérifier si l'heure actuelle est dans la plage horaire définie
            # Note: Gérer le cas où end_time est le lendemain (ex: 23:00-01:00) serait plus complexe
            # et nécessiterait une logique de date complète, pas seulement d'heure.
            is_within_schedule = False
            if start_time <= end_time:
                if start_time <= current_time <= end_time:
                    is_within_schedule = True
            else: 
                if current_time >= start_time or current_time <= end_time:
                    is_within_schedule = True

            if is_within_schedule:
                # Calculer la prochaine heure de déclenchement attendue
                # On arrondit à la minute précédente pour ne pas manquer de déclencheur
                # Si l'intervalle est 15, on cherche 18:15, 18:30, 18:45, 19:00 etc.
                
                # Obtenir la minute actuelle et la diviser par l'intervalle
                # ex: 18:22, intervalle 15 -> (22 // 15) * 15 = 15
                # La prochaine lecture serait à 18:30
                
                # On cherche la "minute planifiée" la plus récente
                minutes_since_start_of_hour = now.hour * 60 + now.minute
                
                # Trouver la minute de déclenchement la plus proche et passée ou présente
                # Exemple: 18:22, intervalle 15.
                # minutes_since_start_of_hour = 1080 + 22 = 1102
                # (1102 // 15) * 15 = 73 * 15 = 1095.  1095 minutes depuis minuit.
                # 1095 / 60 = 18.25 heures -> 18h15.
                
                # Cela garantit que la lecture se déclenche à des minutes précises (ex: :00, :15, :30, :45)
                # et non pas n'importe quand dans l'intervalle.
                
                # Calcul de la minute à laquelle le message devrait être joué dans cet intervalle
                # pour la minute actuelle
                rounded_minute = (now.minute // interval_minutes) * interval_minutes
                trigger_time = now.replace(minute=rounded_minute, second=0, microsecond=0)

                # Si l'heure actuelle est 18:22 et l'intervalle est 15, trigger_time sera 18:15.
                # Si l'heure actuelle est 18:30 et l'intervalle est 15, trigger_time sera 18:30.
                
                # S'assurer que trigger_time est au moins aussi récent que start_time (le début de la plage horaire)
                # et n'est pas trop en avance sur l'heure actuelle.
                
                # Cette logique est pour s'assurer que nous jouons seulement si l'heure est 'juste'
                # par rapport à l'intervalle, et que nous ne rejouons pas immédiatement.
                
                # On déclenche seulement si la minute actuelle correspond à une minute d'intervalle,
                # et si la dernière lecture pour cette plage horaire est plus ancienne que la prochaine lecture attendue.
                
                # La vraie condition de déclenchement est ici
                # On vérifie si la minute actuelle est une minute "ronde" de l'intervalle
                # ET que nous n'avons pas déjà joué à cette minute "ronde"
                if now.minute % interval_minutes == 0 and \
                   now.second < 5 and \
                   last_played_times[i] < now.replace(second=0, microsecond=0): # Vérifie si la dernière lecture est avant cette minute actuelle
                    
                    log_planner_message(f"Déclenchement planifié pour l'intervalle {start_time_str}-{end_time_str}, toutes les {interval_minutes} minutes.")
                    for lang in languages_to_play:
                        play_message(lang)
                        # Optionnel: petite pause entre chaque langue si vous voulez éviter la superposition stricte
                        time.sleep(1)
                    
                    last_played_times[i] = now.replace(second=0, microsecond=0) # Mettre à jour la dernière heure de lecture
                    log_planner_message(f"Messages planifiés joués à {now.strftime('%H:%M')}.")
                    time.sleep(5)  # Petite pause pour éviter de re-déclencher immédiatement si le script est très rapide

        time.sleep(1) 

if __name__ == "__main__":
    log_planner_message("Audio scheduler script started.")
    main_loop()