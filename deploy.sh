#!/bin/bash

# ==============================================================================
# Script de Déploiement et Mise à Jour pour Raspberry Pi
# ==============================================================================
# Ce script automatise le transfert des fichiers, l'installation des dépendances,
# et la configuration/redémarrage des services systemd sur un Raspberry Pi.
# Il utilise les variables d'environnement définies dans un fichier .env local.
#
# À exécuter depuis votre machine de développement (Mac) dans le dossier PARENT
# de votre répertoire de projet (par exemple, si votre projet est dans
# /home/user/my_app, exécutez le script depuis /home/user/).
# ==============================================================================

# --- Configuration du Script ---
# Arrêter le script si une commande échoue
set -e
# Arrêter le script si une variable non définie est utilisée
set -u
# Si un composant d'un pipeline échoue, le pipeline échoue
set -o pipefail

# --- Chemin du fichier .env local ---
LOCAL_ENV_FILE=".env"

# --- Vérification et Chargement du fichier .env local ---
if [ ! -f "$LOCAL_ENV_FILE" ]; then
    echo "ERREUR: Le fichier .env local n'a pas été trouvé à la racine du répertoire courant."
    echo "Créez un fichier '.env' en vous basant sur '.env.example' et remplissez les variables."
    exit 1
fi

# Charge les variables du .env local dans l'environnement du script
# Ceci est pour que les variables comme LOCAL_PROJECT_DIR ou PASSWORD soient disponibles dans ce script.
# Utilisez une méthode robuste pour parser le .env.
# On exclut les lignes vides et les commentaires, puis on exporte les variables.
eval $(grep -v '^#' "$LOCAL_ENV_FILE" | grep -v '^[[:space:]]*$' | awk -F'=' '{print "export " $1 "=\"" (gensub(/"/, "\\\"", $2, "g")) "\""}')

# --- Vérification que les variables essentielles du .env sont chargées ---
if [ -z "${LOCAL_PROJECT_DIR+x}" ]; then
    echo "ERREUR: La variable LOCAL_PROJECT_DIR n'est pas définie dans votre fichier .env."
    exit 1
fi
if [ -z "${PASSWORD+x}" ]; then
    echo "AVERTISSEMENT: La variable PASSWORD n'est pas définie dans votre fichier .env. Le Pi aura un mot de passe par défaut."
    # Fournir une valeur par défaut sécurisée si non spécifiée dans .env
    PASSWORD_FOR_PI="default_secure_password"
else
    PASSWORD_FOR_PI="$PASSWORD" # Utilise le mot de passe du .env local pour le Pi
fi

# --- Configuration du Déploiement (peut être écrasée par .env si défini) ---
# Adresse IP ou hostname de votre Raspberry Pi.
# Vous devez la définir dans votre fichier .env : RASPBERRY_PI_HOST="<IP_OU_HOSTNAME>"
RASPBERRY_PI_HOST="${RASPBERRY_PI_HOST:-}" # Initialise si non défini par .env

# Nom d'utilisateur SSH sur le Raspberry Pi. 'pi' est l'utilisateur par défaut.
# Peut être défini dans votre .env : RASPBERRY_PI_USER="votre_utilisateur"
RASPBERRY_PI_USER="${RASPBERRY_PI_USER:-pi}"

# Chemin ABSOLU où le projet sera stocké sur le Raspberry Pi.
# Peut être défini dans votre .env : PI_PROJECT_ROOT="/home/pi/mon_app"
PI_PROJECT_ROOT="${PI_PROJECT_ROOT:-/home/${RASPBERRY_PI_USER}/$(basename "$LOCAL_PROJECT_DIR")}"

# --- Fichiers de service Systemd ---
FLASK_SERVICE_NAME="flask-api.service"
AUDIO_PLAYER_SERVICE_NAME="audio-player.service"

# --- Dépendances Python à installer ---
PYTHON_DEPS="Flask Flask-Cors python-dotenv"

# --- Dépendances Système (paquets apt) ---
SYSTEM_DEPS="mpv python3-pip python3-venv"

# --- Vérification des Prérequis Locaux ---
echo "--- Vérification des prérequis locaux ---"
if ! command -v scp &> /dev/null; then
    echo "ERREUR: 'scp' non trouvé. Assurez-vous d'avoir OpenSSH client installé."
    exit 1
fi

if ! command -v ssh &> /dev/null; then
    echo "ERREUR: 'ssh' non trouvé. Assurez-vous d'avoir OpenSSH client installé."
    exit 1
fi

if [ -z "$RASPBERRY_PI_HOST" ]; then
    echo "ERREUR: La variable RASPBERRY_PI_HOST n'est pas définie."
    echo "Veuillez la configurer dans votre fichier .env (ex: RASPBERRY_PI_HOST=\"192.168.1.100\")."
    exit 1
fi

if [ ! -d "$LOCAL_PROJECT_DIR" ]; then
    echo "ERREUR: Le répertoire local du projet '$LOCAL_PROJECT_DIR' n'existe pas ou n'est pas le répertoire courant."
    echo "Assurez-vous que '$LOCAL_PROJECT_DIR' est le nom exact de votre dossier de projet,"
    echo "et que vous exécutez ce script depuis le dossier PARENT de '$LOCAL_PROJECT_DIR'."
    echo "Exemple: Si votre projet est dans /Users/user/projets/mon_app, placez ce script dans /Users/user/projets"
    echo "puis exécutez './deploy.sh'."
    exit 1
fi

echo "--- VÉRIFICATION SSH SANS MOT DE PASSE (CRITIQUE POUR L'AUTOMATISATION) ---"
echo "Veuillez vous assurer que la connexion SSH sans mot de passe est configurée entre cette machine et le Raspberry Pi."
echo "Pour configurer SSH sans mot de passe (si ce n'est pas déjà fait) :"
echo "  1. Générez une paire de clés SSH sur votre machine locale : ssh-keygen -t rsa -b 4096 (laissez la passphrase vide pour l'automatisation)"
echo "  2. Copiez la clé publique sur le Raspberry Pi : ssh-copy-id ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}"
echo "     (Vous devrez entrer le mot de passe du Pi UNE DERNIÈRE FOIS.)"
echo "Tentative de connexion SSH pour vérifier..."
ssh -o BatchMode=yes -o ConnectTimeout=5 "${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}" "exit"
if [ $? -ne 0 ]; then
    echo "ERREUR: Impossible d'établir une connexion SSH sans mot de passe vers ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}."
    echo "Veuillez configurer SSH sans mot de passe avant de continuer."
    exit 1
fi
echo "Connexion SSH sans mot de passe vérifiée avec succès."

# --- Fonctions Utilitaires ---

# Fonction pour exécuter une commande via SSH sur le Raspberry Pi
ssh_exec() {
    echo "Exécution SSH: $@"
    ssh "${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}" "$@"
    if [ $? -ne 0 ]; then
        echo "ERREUR: Échec de l'exécution de la commande SSH: $*"
        exit 1
    fi
}

# Fonction pour copier des fichiers via SCP vers le Raspberry Pi
scp_copy() {
    LOCAL_PATH=$1
    REMOTE_PATH=$2
    echo "Transfert SCP: ${LOCAL_PATH} vers ${RASPBERRY_PI_HOST}:${REMOTE_PATH}"
    scp -r "$LOCAL_PATH" "${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}:${REMOTE_PATH}"
    if [ $? -ne 0 ]; then
        echo "ERREUR: Échec du transfert SCP: $LOCAL_PATH vers $REMOTE_PATH"
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
WorkingDirectory=${PI_PROJECT_ROOT}
ExecStart=${PI_PROJECT_ROOT}/venv/bin/python3 ${EXEC_START_FILE}
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
)
    echo "--- Création/Mise à jour du service systemd: ${SERVICE_NAME} ---"
    ssh_exec "echo '${SERVICE_TEMPLATE}' | sudo tee /etc/systemd/system/${SERVICE_NAME}"
    ssh_exec "sudo systemctl daemon-reload"
    ssh_exec "sudo systemctl enable ${SERVICE_NAME}"
    ssh_exec "sudo systemctl restart ${SERVICE_NAME}"
    echo "Service ${SERVICE_NAME} redémarré avec succès."
}

# --- Début du Déploiement ---
echo ""
echo "==================================================================="
echo " DÉPLOIEMENT DE L'APPLICATION AUDIO SUR RASPBERRY PI"
echo " Hôte cible : ${RASPBERRY_PI_HOST}"
echo " Projet local : ${LOCAL_PROJECT_DIR}"
echo " Chemin distant : ${PI_PROJECT_ROOT}"
echo "==================================================================="
echo ""

# 1. Création des répertoires distants si nécessaire
echo "--- 1. Création des répertoires distants ---"
echo "   Création de ${PI_PROJECT_ROOT}, ${PI_PROJECT_ROOT}/audio et /home/${RASPBERRY_PI_USER}/logs..."
ssh_exec "mkdir -p ${PI_PROJECT_ROOT}/audio"
ssh_exec "mkdir -p /home/${RASPBERRY_PI_USER}/logs" # Dossier logs directement dans /home/pi/
echo "   Répertoires créés/vérifiés."

# 2. Transfert des fichiers du projet
echo "--- 2. Transfert des fichiers du projet ---"
# Copie le dossier local entier (LOCAL_PROJECT_DIR) dans le répertoire parent de PI_PROJECT_ROOT sur le Pi.
# Ex: si LOCAL_PROJECT_DIR="mon_app" et PI_PROJECT_ROOT="/home/pi/mon_app"
# alors il copie "mon_app" (local) dans "/home/pi/" (distant), résultant en "/home/pi/mon_app" sur le Pi.
scp_copy "${LOCAL_PROJECT_DIR}" "$(dirname ${PI_PROJECT_ROOT})"
echo "   Fichiers du projet transférés."

# 3. Création du fichier .env sur le Raspberry Pi
echo "--- 3. Création du fichier .env sur le Raspberry Pi ---"
# Utilise les variables lues du .env local ou définies par défaut.
SSH_CREATE_ENV_COMMAND=$(cat <<EOF
echo "IS_RASPBERRY_PI=True" > ${PI_PROJECT_ROOT}/.env
echo "PASSWORD=${PASSWORD_FOR_PI}" >> ${PI_PROJECT_ROOT}/.env
echo "PI_PROJECT_ROOT=${PI_PROJECT_ROOT}" >> ${PI_PROJECT_ROOT}/.env
EOF
)
ssh_exec "${SSH_CREATE_ENV_COMMAND}"
echo "   Fichier .env créé sur le Pi avec la configuration appropriée."

# 4. Installation des dépendances système et Python
echo "--- 4. Installation des dépendances système (${SYSTEM_DEPS}) ---"
ssh_exec "sudo apt update && sudo apt install -y ${SYSTEM_DEPS}"
echo "   Dépendances système installées/mises à jour."

echo "--- 5. Installation des dépendances Python (${PYTHON_DEPS}) dans un environnement virtuel ---"
ssh_exec "
    cd ${PI_PROJECT_ROOT} && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install ${PYTHON_DEPS} && \
    deactivate
"
echo "   Dépendances Python installées dans l'environnement virtuel."

# 6. Création et redémarrage des services Systemd
create_systemd_service "${FLASK_SERVICE_NAME}" "Flask API for Audio Player" "api.py"
create_systemd_service "${AUDIO_PLAYER_SERVICE_NAME}" "Audio Player Scheduler" "audio_player.py"

echo ""
echo "==================================================================="
echo " DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !"
echo "==================================================================="
echo "Accédez à l'interface via : http://${RASPBERRY_PI_HOST}:5000/index.html"
echo "Pour vérifier les logs sur le Pi (via SSH) :"
echo "  journalctl -u ${FLASK_SERVICE_NAME} -f"
echo "  journalctl -u ${AUDIO_PLAYER_SERVICE_NAME} -f"
echo ""
echo "NOTE : Assurez-vous que votre fichier .env local a IS_RASPBERRY_PI=False pour le développement sur Mac."
echo ""