# api.py
from flask import Flask, request, jsonify
import subprocess
import threading
import os
from functools import wraps
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Protection par mot de passe (simple, pour usage local)
PASSWORD = "1950casion" 

# --- Chemin du fichier de log du planificateur automatique ---
PLANNER_LOG_FILE_PATH = "/home/pi/logs/audio_player.log" # Doit correspondre à celui dans audio_player.py
# --- ATTENTION : Sur votre Mac, ce fichier n'existera pas forcément ou ne sera pas pertinent.
# Vous pourriez vouloir un chemin temporaire pour le développement Mac si vous ne voulez pas d'erreur.
# Par exemple:
# PLANNER_LOG_FILE_PATH = "./temp_planner_log.log" # Pour le développement local sur Mac
# if not os.path.exists(os.path.dirname(PLANNER_LOG_FILE_PATH)):
#    os.makedirs(os.path.dirname(PLANNER_LOG_FILE_PATH), exist_ok=True)
# if not os.path.exists(PLANNER_LOG_FILE_PATH):
#     with open(PLANNER_LOG_FILE_PATH, 'w') as f:
#         f.write("Fichier de log du planificateur initialisé (pour Mac).\n")


AUDIO_FILES = {
    "fr": "./audio/long-fr.mp3",
    "en": "./audio/long-en.mp3",
    "ar": "./audio/long-ar.mp3",
    "ti": "./audio/long-ti.m4a",
    "fa": "./audio/long-fa.mp3",
    "fc_sion-fr": "./audio/fc_sion-fr.mp3",
    "fc_sion-de": "./audio/fc_sion-de.mp3"
}

# Statut du lecteur automatique
# Cette variable globale est une simulation.
# Sur le Pi, le statut serait vérifié via `systemctl is-active audio-player.service`
auto_player_running = True 

# Variable globale pour stocker le processus de lecture en cours
# Initialisez-la à None
current_audio_process = None 
current_audio_thread = None 

app_logs = []
MAX_APP_LOG_ENTRIES = 50 # Limite pour les logs de l'API Flask

def add_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [API] {message}" # Ajout du préfixe [API]
    app_logs.append(log_entry)
    if len(app_logs) > MAX_APP_LOG_ENTRIES:
        app_logs.pop(0) # Supprime l'entrée la plus ancienne si la limite est atteinte
    print(log_entry) 

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Vérifie si l'en-tête Authorization contient le mot de passe correct
        if request.headers.get('Authorization') != f'Bearer {PASSWORD}':
            add_log("Accès non autorisé tenté.")
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper

@app.route('/play/<lang>', methods=['POST'])
@authenticate
def play_now(lang):
    global current_audio_process, current_audio_thread
    
    # Arrêtez toute lecture en cours avant d'en lancer une nouvelle
    if current_audio_process and current_audio_process.poll() is None: # Si un processus est actif
        add_log("Arrêt de la lecture précédente pour lancer une nouvelle.")
        try:
            current_audio_process.terminate() # Envoie un signal de terminaison (SIGTERM)
            current_audio_process.wait(timeout=1) # Attend un peu la terminaison
        except subprocess.TimeoutExpired:
            current_audio_process.kill() # Tue le processus si la terminaison ne marche pas (SIGKILL)
        current_audio_process = None
        current_audio_thread = None

    file_path = AUDIO_FILES.get(lang)
    if file_path and os.path.exists(file_path):
        add_log(f"Tentative de lecture audio pour {lang} : {file_path}")
        
        def _play_audio_target(path):
            global current_audio_process
            try:
                # Utilisez 'afplay' pour macOS. Pour le Raspberry Pi, utilisez 'mpv' ou 'omxplayer'.
                # Pour mpv (recommandé pour le Pi, meilleure gestion audio) :
                # current_audio_process = subprocess.Popen(["mpv", "--ao=alsa", path])
                # Pour omxplayer (léger sur le Pi) :
                # current_audio_process = subprocess.Popen(["omxplayer", "-o", "local", path])
                current_audio_process = subprocess.Popen(["afplay", path]) 
                current_audio_process.wait()
                add_log(f"Lecture de {path} terminée.")
            except Exception as e:
                add_log(f"Erreur lors de la lecture audio de {path}: {e}")
            finally:
                # Réinitialise current_audio_process une fois la lecture terminée (ou si erreur)
                if current_audio_process and current_audio_process.poll() is not None:
                    current_audio_process = None 

        # Lance la lecture dans un thread séparé
        current_audio_thread = threading.Thread(target=_play_audio_target, args=(file_path,))
        current_audio_thread.start()
        
        return jsonify({"status": "Playing", "lang": lang}), 200
    
    add_log(f"Erreur: Fichier audio non trouvé pour {lang} : {file_path}")
    return jsonify({"error": "File not found or language not supported"}), 404

# Route pour récupérer les logs de l'API Flask
@app.route('/api_logs', methods=['GET']) # Renommée pour être plus spécifique
@authenticate
def get_api_logs():
    return jsonify({"logs": app_logs}), 200

# --- NOUVEAU : Route pour récupérer les logs du planificateur ---
@app.route('/planner_logs', methods=['GET'])
@authenticate
def get_planner_logs():
    try:
        with open(PLANNER_LOG_FILE_PATH, "r") as f:
            # Lire les 50 dernières lignes pour éviter de surcharger
            logs = f.readlines()
            # Supprimer les éventuels caractères de nouvelle ligne
            recent_logs = [line.strip() for line in logs[-MAX_APP_LOG_ENTRIES:]] 
        return jsonify({"logs": recent_logs}), 200
    except FileNotFoundError:
        add_log(f"Erreur: Fichier de log du planificateur non trouvé à {PLANNER_LOG_FILE_PATH}")
        return jsonify({"logs": [f"Erreur: Fichier de log du planificateur ({PLANNER_LOG_FILE_PATH}) non trouvé ou non accessible."]}) , 404
    except Exception as e:
        add_log(f"Erreur lors de la lecture du fichier de log du planificateur : {e}")
        return jsonify({"logs": [f"Erreur lors de la lecture du log du planificateur : {e}"]}), 500


@app.route('/stop_audio', methods=['POST'])
@authenticate
def stop_audio():
    global current_audio_process, current_audio_thread
    if current_audio_process and current_audio_process.poll() is None:
        add_log("Requête d'arrêt reçue. Arrêt de la lecture en cours.")
        try:
            current_audio_process.terminate()
            current_audio_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            current_audio_process.kill()
        current_audio_process = None
        current_audio_thread = None
        return jsonify({"status": "Stopped"}), 200
    else:
        add_log("Aucune lecture en cours à arrêter.")
        return jsonify({"status": "No audio playing"}), 200

@app.route('/status', methods=['GET'])
@authenticate
def get_status():
    # Sur le Pi, vous pourriez vouloir interroger le statut réel du service systemd :
    # result = subprocess.run(["systemctl", "is-active", "audio-player.service"], capture_output=True, text=True)
    # is_running = "active" in result.stdout.strip()
    # return jsonify({"auto_player_running": is_running}), 200
    
    # Pour le développement sur Mac, nous utilisons la variable globale simulée
    
    # Vérifie si une lecture manuelle est en cours
    is_manual_audio_playing = False
    if current_audio_process and current_audio_process.poll() is None:
        is_manual_audio_playing = True
    
    return jsonify({
        "auto_player_running": auto_player_running,
        "manual_audio_playing": is_manual_audio_playing
    }), 200

@app.route('/auto_player/<action>', methods=['POST'])
@authenticate
def manage_auto_player(action):
    global auto_player_running
    if action == "start":
        add_log("SIMULATION: Démarrage du service auto-player.")
        # Sur le Raspberry Pi, décommenter cette ligne :
        # subprocess.run(["sudo", "systemctl", "start", "audio-player.service"])
        auto_player_running = True
        return jsonify({"status": "Auto player started"}), 200
    elif action == "stop":
        add_log("SIMULATION: Arrêt du service auto-player.")
        # Sur le Raspberry Pi, décommenter cette ligne :
        # subprocess.run(["sudo", "systemctl", "stop", "audio-player.service"])
        auto_player_running = False
        return jsonify({"status": "Auto player stopped"}), 200
    add_log(f"Erreur: Action invalide pour auto-player : {action}")
    return jsonify({"error": "Invalid action"}), 400

if __name__ == '__main__':
    add_log("API Flask démarrée.")
    # Si vous êtes sur Mac et que vous voulez simuler le fichier de log du planificateur:
    # try:
    #     if not os.path.exists(os.path.dirname(PLANNER_LOG_FILE_PATH)):
    #         os.makedirs(os.path.dirname(PLANNER_LOG_FILE_PATH), exist_ok=True)
    #     if not os.path.exists(PLANNER_LOG_FILE_PATH):
    #         with open(PLANNER_LOG_FILE_PATH, 'w') as f:
    #             f.write("Fichier de log du planificateur initialisé (pour Mac).\n")
    # except Exception as e:
    #     add_log(f"Avertissement: Impossible de créer/initialiser le fichier de log du planificateur sur Mac: {e}")

    app.run(host='0.0.0.0', port=5000, debug=True)