# Guide de Déploiement et Développement de l'Application Audio

Ce guide explique comment déployer l'application de lecteur audio sur un Raspberry Pi 4 ou 5, ainsi que comment la développer et la tester sur un Mac.

## 1\. Structure du Projet

Assurez-vous que votre projet a la structure suivante :

```
votre_projet/
├── api.py
├── audio_player.py
├── index.html
├── README.md
├── audio/
│   ├── long-fr.mp3
│   ├── long-en.mp3
│   ├── long-ar.mp3
│   ├── long-ti.m4a
│   ├── long-fa.mp3
│   ├── fc_sion-fr.mp3
│   └── fc_sion-de.mp3
└── (autres fichiers comme venv/ si vous utilisez des environnements virtuels)
```

## 2\. Configuration Requise

### Côté Raspberry Pi

  * **Système d'exploitation :** Raspberry Pi OS (anciennement Raspbian).
  * **Lecteur audio :** `mpv` est recommandé pour une meilleure compatibilité et gestion ALSA. Installez-le :
    ```bash
    sudo apt update
    sudo apt install mpv
    ```
  * **Droits `sudo` :** L'utilisateur (`pi` par défaut) exécutant les services doit avoir les droits `sudo` pour gérer les services `systemd` (ce qui est généralement le cas).
  * **Accès réseau :** Le Pi doit être accessible depuis votre réseau pour que l'interface web fonctionne.
  * **Dossiers :** Assurez-vous que les dossiers `/home/pi/audio` et `/home/pi/logs` existent et que l'utilisateur `pi` (ou l'utilisateur du service) a les droits d'écriture.

### Côté Mac (Développement)

  * **Lecteur audio :** `afplay` (intégré à macOS).
  * **Python :** Python 3.9+ recommandé.
  * **Dossiers :** Le dossier `./audio` (à côté de vos scripts) doit contenir vos fichiers audio. Le dossier `./temp_planner_log.log` sera créé automatiquement si inexistant.

## 3\. Préparation des Fichiers Audio

  * Placez tous vos fichiers `.mp3` ou `.m4a` dans le dossier `audio/` à la racine de votre projet.
  * Assurez-vous que les noms de fichiers dans `AUDIO_FILES` dans `api.py` et `audio_player.py` correspondent aux noms réels des fichiers.

## 4\. Configuration Spécifique à l'Environnement

C'est la partie la plus importante pour basculer entre Mac et Raspberry Pi.

### Fichier `api.py`

Ouvrez `api.py` et modifiez la variable `IS_RASPBERRY_PI` au début du fichier :

```python
# api.py

# --- Configuration de l'environnement ---
# Mettez True si vous êtes sur le Raspberry Pi, False si vous êtes en développement sur Mac
IS_RASPBERRY_PI = False # <--- MODIFIEZ CETTE LIGNE !
```

  * **`IS_RASPBERRY_PI = False` (pour Mac) :**
      * Les fichiers audio seront cherchés dans `./audio/`.
      * Les logs du planificateur seront écrits/lus dans `./temp_planner_log.log`.
      * La lecture audio utilisera `afplay`.
      * Le statut du planificateur sera simulé.
      * Les actions de démarrage/arrêt du planificateur seront simulées.
  * **`IS_RASPBERRY_PI = True` (pour Raspberry Pi) :**
      * Les fichiers audio seront cherchés dans `/home/pi/audio/`.
      * Les logs du planificateur seront écrits/lus dans `/home/pi/logs/audio_player.log`.
      * La lecture audio utilisera `mpv --ao=alsa`.
      * Le statut du planificateur sera obtenu en interrogeant le service `systemd` (`systemctl is-active audio-player.service`).
      * Les actions de démarrage/arrêt du planificateur exécuteront les commandes `sudo systemctl start/stop audio-player.service`.

### Fichier `audio_player.py`

Ouvrez `audio_player.py` et modifiez la variable `IS_RASPBERRY_PI` au début du fichier de la même manière :

```python
# audio_player.py

# --- Configuration de l'environnement ---
# Mettez True si vous êtes sur le Raspberry Pi, False si vous êtes en développement sur Mac
IS_RASPBERRY_PI = False # <--- MODIFIEZ CETTE LIGNE !
```

Les comportements (chemins des fichiers, commandes de lecture) s'adapteront de manière identique à `api.py`.

## 5\. Déploiement et Lancement sur Raspberry Pi

Ces étapes doivent être effectuées directement sur votre Raspberry Pi (via SSH ou un terminal local).

### Étape 1 : Transfert des Fichiers

Transférez l'intégralité de votre dossier `votre_projet/` vers le dossier `/home/pi/` sur votre Raspberry Pi.
Par exemple, en utilisant `scp` depuis votre Mac :

```bash
scp -r /chemin/vers/votre_projet pi@<adresse_ip_du_pi>:/home/pi/
```

Assurez-vous que le dossier `/home/pi/audio/` contient bien vos fichiers MP3 et que le dossier `/home/pi/logs/` existe. S'il n'existe pas :

```bash
mkdir -p /home/pi/audio
mkdir -p /home/pi/logs
```

### Étape 2 : Installation des Dépendances

Naviguez dans le dossier de votre projet sur le Pi :

```bash
cd /home/pi/votre_projet/
```

Créez un environnement virtuel (recommandé) et installez les dépendances :

```bash
sudo apt update
sudo apt install python3-pip python3-venv # Installe pip et venv si non déjà présents
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-Cors
deactivate # Désactive l'environnement pour le moment
```

### Étape 3 : Création des Services Systemd

`systemd` permet à vos scripts de s'exécuter en arrière-plan, de démarrer automatiquement au boot et d'être gérés facilement.

Créez ces fichiers en tant que `sudo` (par exemple, avec `sudo nano /etc/systemd/system/nom_du_fichier.service`).

#### `flask-api.service`

Créez le fichier `/etc/systemd/system/flask-api.service` :

```ini
[Unit]
Description=Flask API for Audio Player
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/votre_projet/ # <--- ASSUREZ-VOUS QUE CE CHEMIN EST CORRECT !
ExecStart=/home/pi/votre_projet/venv/bin/python3 api.py # <--- Chemin complet vers l'interpréteur de l'environnement virtuel
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### `audio-player.service`

Créez le fichier `/etc/systemd/system/audio-player.service` :

```ini
[Unit]
Description=Audio Player Scheduler
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/votre_projet/ # <--- ASSUREZ-VOUS QUE CE CHEMIN EST CORRECT !
ExecStart=/home/pi/votre_projet/venv/bin/python3 audio_player.py # <--- Chemin complet vers l'interpréteur de l'environnement virtuel
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Points importants pour les services Systemd :**

  * **`WorkingDirectory` :** Doit être le chemin **absolu** vers le dossier racine de votre projet sur le Pi (ex: `/home/pi/votre_projet/`).
  * **`ExecStart` :** Doit pointer vers l'interpréteur Python **dans votre environnement virtuel** pour s'assurer que toutes les dépendances sont correctement utilisées (ex: `/home/pi/votre_projet/venv/bin/python3`).
  * **`User=pi` :** Spécifie que le service s'exécutera sous l'utilisateur `pi`.
  * **`Restart=always` :** Redémarrera automatiquement le service en cas de crash.
  * **`StandardOutput=journal` et `StandardError=journal` :** Redirigent les `print()` et les erreurs vers le journal de `systemd`, que vous pouvez consulter avec `journalctl`.

### Étape 4 : Activation et Démarrage des Services

Après avoir créé les fichiers `.service`, rechargez `systemd` et activez/démarrez les services :

```bash
sudo systemctl daemon-reload # Recharge les configurations de service
sudo systemctl enable flask-api.service # Active le service au démarrage
sudo systemctl enable audio-player.service # Active le service au démarrage

sudo systemctl start flask-api.service # Démarre le service Flask API
sudo systemctl start audio-player.service # Démarre le service Audio Player
```

### Étape 5 : Accès à l'Interface Web

Ouvrez votre navigateur web (sur n'importe quel appareil de votre réseau) et accédez à l'adresse IP de votre Raspberry Pi, suivi du port de l'API (par défaut 5000) :

`http://<adresse_ip_du_pi>:5000/index.html`

Remplacez `<adresse_ip_du_pi>` par l'adresse IP réelle de votre Raspberry Pi.

### Débogage sur Raspberry Pi

  * **Vérifier le statut d'un service :**
    ```bash
    sudo systemctl status flask-api.service
    sudo systemctl status audio-player.service
    ```
  * **Voir les logs d'un service :**
    ```bash
    journalctl -u flask-api.service -f # Pour les logs en temps réel de l'API
    journalctl -u audio-player.service -f # Pour les logs en temps réel du planificateur
    ```
  * **Redémarrer un service :**
    ```bash
    sudo systemctl restart flask-api.service
    sudo systemctl restart audio-player.service
    ```
  * **Arrêter un service :**
    ```bash
    sudo systemctl stop flask-api.service
    sudo systemctl stop audio-player.service
    ```
  * **Erreurs de permissions :** Si vous rencontrez des erreurs de permission (`Permission denied`), assurez-vous que l'utilisateur `pi` a les droits d'accès aux dossiers audio et logs. Si vous utilisez `sudo` dans les appels `subprocess` dans `api.py` pour `systemctl`, l'utilisateur `pi` doit être dans le groupe `sudoers` (ce qui est le cas par défaut sur Raspberry Pi OS).

## 6\. Développement et Test sur Mac

Ces étapes sont à effectuer sur votre machine de développement (Mac).

### Étape 1 : Configuration des Fichiers

Ouvrez `api.py` et `audio_player.py` et assurez-vous que la variable `IS_RASPBERRY_PI` est définie sur `False` :

```python
IS_RASPBERRY_PI = False
```

### Étape 2 : Installation des Dépendances

Naviguez dans le dossier de votre projet :

```bash
cd /chemin/vers/votre_projet/
```

Créez un environnement virtuel (si ce n'est pas déjà fait) et installez les dépendances :

```bash
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-Cors
```

### Étape 3 : Lancement des Scripts

Ouvrez deux terminaux séparés, et dans chacun :

1.  Activez l'environnement virtuel :
    ```bash
    source venv/bin/activate
    ```
2.  Dans le premier terminal, lancez l'API Flask :
    ```bash
    python api.py
    ```
3.  Dans le second terminal, lancez le planificateur audio (pour simuler son comportement et générer des logs locaux) :
    ```bash
    python audio_player.py
    ```
    *(Note : Le planificateur `audio_player.py` n'a pas besoin de "piloter" l'API sur Mac ; il suffit qu'il écrive ses logs dans le fichier local `./temp_planner_log.log` que l'API lira.)*

### Étape 4 : Accès à l'Interface Web

Ouvrez votre navigateur web et accédez à l'interface locale :

`http://localhost:5000/index.html`

### Débogage sur Mac

  * **Logs API :** Les messages de `add_log` de l'API s'afficheront directement dans le terminal où `api.py` est lancé.
  * **Logs Planificateur :** Les messages de `log_planner_message` du planificateur s'afficheront dans le terminal où `audio_player.py` est lancé et seront écrits dans `./temp_planner_log.log`. L'interface web lira ce fichier.
  * **Erreurs Python :** Les erreurs Python s'afficheront dans le terminal du script concerné.

## 7\. Mises à Jour et Maintenance

  * Pour mettre à jour le code sur le Raspberry Pi, transférez simplement les fichiers modifiés par `scp` et redémarrez les services (`sudo systemctl restart <nom_du_service>`).
  * Vérifiez régulièrement l'espace disque sur le Pi, surtout si les fichiers de log ne sont pas gérés (rotations de logs, limites de taille). Actuellement, la limite de 50 entrées dans l'API Flask et la lecture des 50 dernières entrées du fichier de log du planificateur aident à contrôler la taille. Pour une solution de production plus robuste, utilisez des outils de rotation de logs comme `logrotate` sur le Pi pour `/home/pi/logs/audio_player.log`.
