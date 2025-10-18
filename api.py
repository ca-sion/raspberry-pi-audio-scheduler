# api.py
from flask import Flask, request, jsonify
import subprocess
import threading
import os
import json
from functools import wraps
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env au démarrage de l'application
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Configuration de l'environnement ---
# Récupérer les variables depuis les variables d'environnement
IS_RASPBERRY_PI = os.getenv('IS_RASPBERRY_PI', 'False').lower() == 'true'
PASSWORD = os.getenv('PASSWORD', 'default_password')
PI_PROJECT_ROOT = os.getenv('PI_PROJECT_ROOT', '/home/pi/app')

# --- Chemins des fichiers ---
if IS_RASPBERRY_PI:
    AUDIO_BASE_DIR = os.path.join(PI_PROJECT_ROOT, "audio")
    PLANNER_LOG_FILE_PATH = os.path.join(PI_PROJECT_ROOT, "logs", "audio_player.log")
    SCHEDULE_FILE_PATH = os.path.join(PI_PROJECT_ROOT, "schedule.json")
else: # Environnement de développement (Mac)
    AUDIO_BASE_DIR = os.path.join(os.getcwd(), "audio")
    PLANNER_LOG_FILE_PATH = os.path.join(os.getcwd(), "temp_planner_log.log")
    SCHEDULE_FILE_PATH = os.path.join(os.getcwd(), "schedule.json")

# Assurez-vous que les répertoires nécessaires existent au démarrage
os.makedirs(AUDIO_BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PLANNER_LOG_FILE_PATH), exist_ok=True)

# Initialisation du fichier de log du planificateur sur Mac si inexistant
if not IS_RASPBERRY_PI and not os.path.exists(PLANNER_LOG_FILE_PATH):
    with open(PLANNER_LOG_FILE_PATH, 'w') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PLANNER] Fichier de log du planificateur initialisé (pour Mac).\n")


AUDIO_FILES = {
    "fr": os.path.join(AUDIO_BASE_DIR, "long-fr.mp3"),
    "en": os.path.join(AUDIO_BASE_DIR, "long-en.mp3"),
    "ar": os.path.join(AUDIO_BASE_DIR, "long-ar.mp3"),
    "ti": os.path.join(AUDIO_BASE_DIR, "long-ti.m4a"),
    "fa": os.path.join(AUDIO_BASE_DIR, "long-fa.mp3"),
    "fc_sion-fr": os.path.join(AUDIO_BASE_DIR, "fc_sion-fr.mp3"),
    "fc_sion-de": os.path.join(AUDIO_BASE_DIR, "fc_sion-de.mp3"),
    "horn": os.path.join(AUDIO_BASE_DIR, "horn.mp3"),
    "siren-alert": os.path.join(AUDIO_BASE_DIR, "siren-alert.mp3"),
    "boat-horn": os.path.join(AUDIO_BASE_DIR, "boat-horn.mp3"),
    "facility-siren": os.path.join(AUDIO_BASE_DIR, "facility-siren.mp3"),
    "chime-alert": os.path.join(AUDIO_BASE_DIR, "chime-alert.mp3"),
    "race-start-bip": os.path.join(AUDIO_BASE_DIR, "race-start-bip.mp3")
}

# Statut du lecteur automatique
auto_player_running = True 

# Variable globale pour stocker le processus de lecture en cours
current_audio_process = None 
current_audio_thread = None 

app_logs = []
MAX_APP_LOG_ENTRIES = 50 # Limite pour les logs de l'API Flask

def add_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [API] {message}"
    app_logs.append(log_entry)
    if len(app_logs) > MAX_APP_LOG_ENTRIES:
        app_logs.pop(0) 
    print(log_entry) 

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        expected_token = PASSWORD 
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            add_log("Accès non autorisé tenté : Pas d'en-tête d'autorisation.")
            return jsonify({"error": "Unauthorized: Missing Authorization header"}), 401
        try:
            scheme, token = auth_header.split(None, 1)
        except ValueError:
            add_log("Accès non autorisé tenté : Format d'en-tête non valide.")
            return jsonify({"error": "Unauthorized: Invalid Authorization header format"}), 401
        if scheme.lower() != 'bearer':
            add_log(f"Accès non autorisé tenté : Schéma d'authentification invalide '{scheme}'.")
            return jsonify({"error": "Unauthorized: Invalid authentication scheme"}), 401
        if token != expected_token:
            add_log("Accès non autorisé tenté : Token invalide.")
            return jsonify({"error": "Unauthorized: Invalid token"}), 401
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    password_attempt = data.get('password')
    if password_attempt == PASSWORD:
        token = PASSWORD 
        add_log("Connexion réussie.")
        return jsonify({"message": "Authentication successful", "token": token}), 200
    else:
        add_log("Tentative de connexion échouée : Mot de passe incorrect.")
        return jsonify({"error": "Invalid credentials"}), 401

# --- Routes API pour la programmation ---
@app.route('/api/schedule', methods=['GET'])
@authenticate
def get_schedule():
    try:
        with open(SCHEDULE_FILE_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        add_log(f"Le fichier de programmation {SCHEDULE_FILE_PATH} est introuvable.")
        return jsonify({"error": "Schedule file not found."}), 404
    except Exception as e:
        add_log(f"Erreur lors de la lecture du fichier de programmation : {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route('/api/schedule', methods=['POST'])
@authenticate
def set_schedule():
    new_data = request.get_json()
    if not new_data or 'schedules' not in new_data:
        return jsonify({"error": "Invalid data format."}), 400
    
    try:
        with open(SCHEDULE_FILE_PATH, 'w') as f:
            json.dump(new_data, f, indent=2)
        add_log("La programmation a été mise à jour avec succès.")
        return jsonify({"status": "success", "message": "Schedule updated successfully."})
    except Exception as e:
        add_log(f"Erreur lors de l'écriture du fichier de programmation : {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500

# --- Routes API (le reste reste inchangé) ---
@app.route('/play/<lang>', methods=['POST'])
@authenticate
def play_now(lang):
    global current_audio_process, current_audio_thread
    
    if current_audio_process and current_audio_process.poll() is None:
        add_log("Arrêt de la lecture précédente pour lancer une nouvelle.")
        try:
            current_audio_process.terminate()
            current_audio_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            current_audio_process.kill()
        current_audio_process = None
        current_audio_thread = None

    file_path = AUDIO_FILES.get(lang)
    if file_path and os.path.exists(file_path):
        add_log(f"Tentative de lecture audio pour {lang} : {file_path}")
        
        def _play_audio_target(path):
            global current_audio_process
            try:
                if IS_RASPBERRY_PI:
                    mpv_command = ["mpv"]
                    audio_device = os.getenv('MPV_AUDIO_DEVICE')
                    if audio_device:
                        mpv_command.extend([f"--audio-device={audio_device}"])
                    else:
                        mpv_command.extend(["--ao=alsa"])
                    mpv_command.append(path)
                    current_audio_process = subprocess.Popen(mpv_command)
                else:
                    current_audio_process = subprocess.Popen(["afplay", path]) 
                current_audio_process.wait()
                add_log(f"Lecture de {path} terminée.")
            except Exception as e:
                if isinstance(e, FileNotFoundError):
                    add_log(f"Erreur: Lecteur audio non trouvé. Sur Pi, vérifiez l'installation de 'mpv'. Sur Mac, 'afplay' devrait être présent. Erreur: {e}")
                else:
                    add_log(f"Erreur lors de la lecture audio de {path}: {e}")
            finally:
                if current_audio_process and current_audio_process.poll() is not None:
                    current_audio_process = None 

        current_audio_thread = threading.Thread(target=_play_audio_target, args=(file_path,))
        current_audio_thread.start()
        
        return jsonify({"status": "Playing", "lang": lang}), 200
    
    add_log(f"Erreur: Fichier audio non trouvé pour {lang} : {file_path}")
    return jsonify({"error": "File not found or language not supported"}), 404

@app.route('/api_logs', methods=['GET'])
@authenticate
def get_api_logs():
    return jsonify({"logs": app_logs}), 200

@app.route('/planner_logs', methods=['GET'])
@authenticate
def get_planner_logs():
    try:
        with open(PLANNER_LOG_FILE_PATH, "r") as f:
            logs = f.readlines()
            recent_logs = [line.strip() for line in logs[-MAX_APP_LOG_ENTRIES:]] 
        return jsonify({"logs": recent_logs}), 200
    except FileNotFoundError:
        add_log(f"Erreur: Fichier de log du planificateur non trouvé à {PLANNER_LOG_FILE_PATH}. Assurez-vous que audio_player.py est lancé et configuré pour le bon chemin de log.")
        return jsonify({"logs": [f"Erreur: Fichier de log du planificateur ({PLANNER_LOG_FILE_PATH}) non trouvé ou non accessible. Sur Pi, vérifiez le chemin et les permissions. Sur Mac, assurez-vous que audio_player.py est lancé."]}) , 404
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
    global auto_player_running
    if IS_RASPBERRY_PI:
        try:
            result = subprocess.run(["systemctl", "is-active", "pi-audio-player.service"], capture_output=True, text=True, check=True)
            auto_player_running = ("active" in result.stdout.strip())
            add_log(f"Statut réel du service audio-player : {result.stdout.strip()}")
        except FileNotFoundError:
            add_log("Erreur: 'systemctl' n'est pas trouvé. Êtes-vous sûr d'être sur un système Linux avec systemd ?")
            auto_player_running = False 
        except subprocess.CalledProcessError as e:
            add_log(f"Le service 'pi-audio-player.service' n'est pas actif ou a échoué. Erreur: {e.stderr.strip()}")
            auto_player_running = False
        except Exception as e:
            add_log(f"Erreur inattendue lors de la vérification du statut systemd : {e}")
            auto_player_running = False

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
        if IS_RASPBERRY_PI:
            add_log("Démarrage réel du service audio-player sur Raspberry Pi.")
            try:
                subprocess.run(["sudo", "systemctl", "start", "pi-audio-player.service"], check=True)
                auto_player_running = True 
                return jsonify({"status": "Auto player started on Pi"}), 200
            except FileNotFoundError:
                add_log("Erreur: 'systemctl' non trouvé. Assurez-vous que systemd est disponible.")
                return jsonify({"error": "Commande systemctl non trouvée."}), 500
            except subprocess.CalledProcessError as e:
                add_log(f"Erreur lors du démarrage du service systemd : {e.stderr.strip()}")
                return jsonify({"error": f"Impossible de démarrer le service : {e.stderr.strip()}"}), 500
            except Exception as e:
                add_log(f"Erreur inattendue lors du démarrage du service : {e}")
                return jsonify({"error": f"Erreur inattendue : {e}"}), 500
        else:
            add_log("SIMULATION: Démarrage du service auto-player sur Mac.")
            auto_player_running = True
            return jsonify({"status": "Auto player started (Simulated on Mac)"}), 200
    elif action == "stop":
        if IS_RASPBERRY_PI:
            add_log("Arrêt réel du service audio-player sur Raspberry Pi.")
            try:
                subprocess.run(["sudo", "systemctl", "stop", "pi-audio-player.service"], check=True)
                auto_player_running = False 
                return jsonify({"status": "Auto player stopped on Pi"}), 200
            except FileNotFoundError:
                add_log("Erreur: 'systemctl' non trouvé. Assurez-vous que systemd est disponible.")
                return jsonify({"error": "Commande systemctl non trouvée."}), 500
            except subprocess.CalledProcessError as e:
                add_log(f"Erreur lors de l'arrêt du service systemd : {e.stderr.strip()}")
                return jsonify({"error": f"Impossible d'arrêter le service : {e.stderr.strip()}"}), 500
            except Exception as e:
                add_log(f"Erreur inattendue lors de l'arrêt du service : {e}")
                return jsonify({"error": f"Erreur inattendue : {e}"}), 500
        else:
            add_log("SIMULATION: Arrêt du service auto-player sur Mac.")
            auto_player_running = False
            return jsonify({"status": "Auto player stopped (Simulated on Mac)"}), 200
    add_log(f"Erreur: Action invalide pour auto-player : {action}")
    return jsonify({"error": "Invalid action"}), 400

if __name__ == '__main__':
    add_log("API Flask démarrée.")
    if not IS_RASPBERRY_PI:
        os.makedirs(AUDIO_BASE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(PLANNER_LOG_FILE_PATH), exist_ok=True)
        if not os.path.exists(PLANNER_LOG_FILE_PATH):
            with open(PLANNER_LOG_FILE_PATH, 'w') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PLANNER] Fichier de log du planificateur initialisé (pour Mac).\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)