# ==============================================================================
# Script de Déploiement et Mise à Jour pour Raspberry Pi
# ==============================================================================
# Ce script automatise le transfert des fichiers, l'installation des dépendances,
# et la configuration/redémarrage des services systemd sur un Raspberry Pi.
#
# À exécuter depuis votre machine de développement (Mac).
# ==============================================================================

# --- Configuration du Déploiement ---
# Adresse IP ou hostname de votre Raspberry Pi.
# Vous devrez remplacer '<ADRESSE_IP_DU_PI_OU_HOSTNAME>' par l'IP réelle ou 'raspberrypi.local'
# si vous avez configuré le mDNS (accès par hostname).
RASPBERRY_PI_HOST="<ADRESSE_IP_DU_PI_OU_HOSTNAME>" # <--- À MODIFIER impérativement !

# Nom d'utilisateur SSH sur le Raspberry Pi.
# 'pi' est l'utilisateur par défaut sur un Raspberry Pi OS neuf.
RASPBERRY_PI_USER="pi"

# Chemin ABSOLU où le projet sera stocké sur le Raspberry Pi.
# Nous allons créer un dossier 'pi_audio_player_app' dans le répertoire personnel de 'pi'.
# Cela sera '/home/pi/pi_audio_player_app'.
RASPBERRY_PI_PROJECT_PATH="/home/${RASPBERRY_PI_USER}/pi_audio_player_app"

# Nom du dossier de votre projet LOCAL (sur votre Mac).
# C'est le nom du répertoire qui contient api.py, audio_player.py, index.html, et le dossier audio/.
# Si votre projet se trouve dans /Users/votre_nom/Documents/MonSuperLecteurAudio/, alors cette variable serait "MonSuperLecteurAudio".
LOCAL_PROJECT_DIR="raspberry-pi-audio-scheduler" # <--- À MODIFIER pour correspondre au nom de votre dossier de projet sur votre Mac !

# --- Fichiers de service Systemd (créés/mis à jour sur le Pi) ---
FLASK_SERVICE_NAME="flask-api.service"
AUDIO_PLAYER_SERVICE_NAME="audio-player.service"

# --- Dépendances Python à installer (si non déjà installées) ---
PYTHON_DEPS="Flask Flask-Cors"

# --- Dépendances Système (paquets apt) ---
SYSTEM_DEPS="mpv python3-pip python3-venv"

# --- Vérification des Prérequis Locaux ---
if ! command -v scp &> /dev/null; then
    echo "Erreur: 'scp' non trouvé. Assurez-vous d'avoir OpenSSH client installé."
    exit 1
fi

if ! command -v ssh &> /dev/null; then
    echo "Erreur: 'ssh' non trouvé. Assurez-vous d'avoir OpenSSH client installé."
    exit 1
fi

# Vérifie si le répertoire LOCAL_PROJECT_DIR existe bien dans le répertoire courant
# C'est crucial pour que SCP puisse copier le dossier entier.
if [ ! -d "$LOCAL_PROJECT_DIR" ]; then
    echo "Erreur: Le répertoire local du projet '$LOCAL_PROJECT_DIR' n'existe pas dans le répertoire courant."
    echo "Assurez-vous que '$LOCAL_PROJECT_DIR' est le nom exact de votre dossier de projet"
    echo "et que vous exécutez ce script depuis le dossier PARENT de '$LOCAL_PROJECT_DIR'."
    echo "Exemple: Si votre projet est dans /Users/user/projets/pi_audio_player_app, placez ce script dans /Users/user/projets"
    echo "puis exécutez './deploy.sh'."
    exit 1
fi

# --- Fonctions Utilitaires (inchangées par rapport au précédent script) ---

# Fonction pour exécuter une commande via SSH sur le Raspberry Pi
ssh_exec() {
    ssh "${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}" "$@"
    if [ $? -ne 0 ]; then
        echo "Erreur lors de l'exécution de la commande SSH: $*"
        exit 1
    fi
}

# Fonction pour copier des fichiers via SCP vers le Raspberry Pi
scp_copy() {
    LOCAL_PATH=$1
    REMOTE_PATH=$2
    scp -r "$LOCAL_PATH" "${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}:${REMOTE_PATH}"
    if [ $? -ne 0 ]; then
        echo "Erreur lors du transfert SCP: $LOCAL_PATH vers $REMOTE_PATH"
        exit 1
    fi
}

# Fonction pour créer et configurer un service systemd
create_systemd_service() {
    SERVICE_NAME=$1
    DESCRIPTION=$2
    EXEC_START_FILE=$3 # Le script Python à lancer (ex: api.py)
    SERVICE_TEMPLATE=$(cat <<EOF
[Unit]
Description=${DESCRIPTION}
After=network.target

[Service]
User=${RASPBERRY_PI_USER}
WorkingDirectory=${RASPBERRY_PI_PROJECT_PATH}
ExecStart=${RASPBERRY_PI_PROJECT_PATH}/venv/bin/python3 ${EXEC_START_FILE}
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
)
    echo "Création/Mise à jour du service systemd: ${SERVICE_NAME}..."
    ssh_exec "echo '${SERVICE_TEMPLATE}' | sudo tee /etc/systemd/system/${SERVICE_NAME}"
    ssh_exec "sudo systemctl daemon-reload"
    ssh_exec "sudo systemctl enable ${SERVICE_NAME}"
    ssh_exec "sudo systemctl restart ${SERVICE_NAME}"
    echo "Service ${SERVICE_NAME} redémarré avec succès."
}

# --- Début du Déploiement (inchangé par rapport au précédent script) ---
echo "==================================================="
echo " Déploiement sur Raspberry Pi : ${RASPBERRY_PI_HOST}"
echo "==================================================="

# 1. Mise à jour de la configuration de l'environnement sur les fichiers Python
echo "1. Mise à jour de IS_RASPBERRY_PI = True dans api.py et audio_player.py..."
# Utilisation de 'sed -i' avec une extension vide '' pour compatibilité macOS/BSD,
# ou sans extension pour Linux GNU sed.
sed -i '' 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' "${LOCAL_PROJECT_DIR}/api.py" 2>/dev/null || \
sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' "${LOCAL_PROJECT_DIR}/api.py"
sed -i '' 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' "${LOCAL_PROJECT_DIR}/audio_player.py" 2>/dev/null || \
sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' "${LOCAL_PROJECT_DIR}/audio_player.py"
echo "   Fichiers locaux mis à jour pour le déploiement sur Pi."

# 2. Création des répertoires distants si nécessaire
echo "2. Création des répertoires distants (${RASPBERRY_PI_PROJECT_PATH}, ${RASPBERRY_PI_PROJECT_PATH}/audio, /home/${RASPBERRY_PI_USER}/logs)..."
ssh_exec "mkdir -p ${RASPBERRY_PI_PROJECT_PATH}/audio"
ssh_exec "mkdir -p /home/${RASPBERRY_PI_USER}/logs" # Créer le dossier logs dans /home/pi/
echo "   Répertoires créés/vérifiés."

# 3. Transfert des fichiers du projet
echo "3. Transfert des fichiers du projet vers ${RASPBERRY_PI_PROJECT_PATH}..."
# Copie le dossier local entier (LOCAL_PROJECT_DIR) dans le répertoire parent de RASPBERRY_PI_PROJECT_PATH sur le Pi.
# Exemple: si LOCAL_PROJECT_DIR="pi_audio_player_app" et RASPBERRY_PI_PROJECT_PATH="/home/pi/pi_audio_player_app"
# alors il copie "pi_audio_player_app" dans "/home/pi/"
scp_copy "${LOCAL_PROJECT_DIR}" "$(dirname ${RASPBERRY_PI_PROJECT_PATH})" 
echo "   Fichiers transférés."

# 4. Installation des dépendances système et Python
echo "4. Installation des dépendances système (${SYSTEM_DEPS})..."
ssh_exec "sudo apt update && sudo apt install -y ${SYSTEM_DEPS}"
echo "   Dépendances système installées/mises à jour."

echo "5. Installation des dépendances Python (${PYTHON_DEPS}) dans un environnement virtuel..."
ssh_exec "
    cd ${RASPBERRY_PI_PROJECT_PATH} && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install ${PYTHON_DEPS} && \
    deactivate
"
echo "   Dépendances Python installées dans l'environnement virtuel."

# 6. Création et redémarrage des services Systemd
create_systemd_service "${FLASK_SERVICE_NAME}" "Flask API for Audio Player" "api.py"
create_systemd_service "${AUDIO_PLAYER_SERVICE_NAME}" "Audio Player Scheduler" "audio_player.py"

echo "==================================================="
echo " Déploiement TERMINÉ avec succès !"
echo "==================================================="
echo "Vous pouvez maintenant accéder à l'interface via : http://${RASPBERRY_PI_HOST}:5000/index.html"
echo "Pour vérifier les logs sur le Pi : journalctl -u ${FLASK_SERVICE_NAME} -f ou journalctl -u ${AUDIO_PLAYER_SERVICE_NAME} -f"

# --- Revenir à la configuration de développement sur les fichiers Python locaux ---
echo "6. Revenir à la configuration de IS_RASPBERRY_PI = False dans api.py et audio_player.py locaux..."
sed -i '' 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' "${LOCAL_PROJECT_DIR}/api.py" 2>/dev/null || \
sed -i 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' "${LOCAL_PROJECT_DIR}/api.py"
sed -i '' 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' "${LOCAL_PROJECT_DIR}/audio_player.py" 2>/dev/null || \
sed -i 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' "${LOCAL_PROJECT_DIR}/audio_player.py"
echo "   Fichiers locaux revenus à la configuration de développement."