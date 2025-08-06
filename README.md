# Guide de Déploiement et Développement de l'Application Audio

Ce guide explique comment déployer l'application de lecteur audio sur un Raspberry Pi 4 ou 5, ainsi que comment la développer et la tester sur un Mac.

### 0. Prérequis

Pour que le déploiement fonctionne correctement, assurez-vous d'avoir les éléments suivants configurés sur votre Raspberry Pi :
- **SSH activé** : vous pouvez le faire via `sudo raspi-config`.
- **Authentification par clé publique SSH** : pour un déploiement sans mot de passe, générez une paire de clés SSH sur votre machine locale et copiez-la sur le Raspberry Pi (`ssh-copy-id pi@raspberrypi.local`).
- **Python 3** : Assurez-vous que Python 3 est installé.
- **Droits sudo** : L'utilisateur de déploiement (`pi` par défaut) doit avoir les droits sudo pour installer le service.

## 1\. Structure du Projet

Assurez-vous que votre projet a la structure suivante :

```
votre\_projet/
├── api.py
├── audio\_player.py
├── index.html
├── README.md
├── deploy.sh
├── .env
├── .env.example
├── audio/
│   ├── long-fr.mp3
│   ├── long-en.mp3
│   ├── long-ar.mp3
│   ├── long-ti.m4a
│   ├── long-fa.mp3
│   ├── fc\_sion-fr.mp3
│   └── fc\_sion-de.mp3
└── (autres fichiers comme venv/ si vous utilisez des environnements virtuels)

````

## 2\. Configuration Requise

### Côté Raspberry Pi

  * **Système d'exploitation :** Raspberry Pi OS (anciennement Raspbian).
  * **Lecteur audio :** `mpv` est recommandé pour une meilleure compatibilité et gestion ALSA. Le script `deploy.sh` l'installera automatiquement.
  * **Droits `sudo` :** L'utilisateur (`pi` par défaut) exécutant les services doit avoir les droits `sudo` (ce qui est généralement le cas).
  * **Accès réseau :** Le Pi doit être accessible depuis votre réseau pour que l'interface web fonctionne.
  * **Configuration SSH sans mot de passe :** **Indispensable pour l'automatisation.** Suivez les instructions dans la section "Utilisation du script `deploy.sh`" ci-dessous.

### Côté Mac (Développement)

  * **Lecteur audio :** `afplay` (intégré à macOS).
  * **Python :** Python 3.9+ recommandé.
  * **Dossiers :** Le dossier `./audio` (à côté de vos scripts) doit contenir vos fichiers audio.

## 3\. Préparation des Fichiers Audio

  * Placez tous vos fichiers `.mp3` ou `.m4a` dans le dossier `audio/` à la racine de votre projet.
  * Assurez-vous que les noms de fichiers dans `AUDIO_FILES` dans `api.py` et `audio_player.py` correspondent aux noms réels des fichiers.

## 4\. Configuration Spécifique à l'Environnement

La configuration de l'application est gérée via un fichier `.env`.

1.  **Copiez** le fichier `.env.example` à la racine de votre projet et renommez-le en `.env`.
2.  **Modifiez** le fichier `.env` avec vos valeurs spécifiques :
    * **`IS_RASPBERRY_PI`** : Mettez `False` pour le développement local sur Mac. Pour le déploiement sur le Raspberry Pi, le script `deploy.sh` s'assurera que l'environnement d'exécution de l'application est bien configuré sur `True`. Vous n'avez rien à changer dans ce fichier pour le déploiement.
    * **`PASSWORD`** : Définissez le mot de passe souhaité pour l'API.
    * **`PI_PROJECT_ROOT`** : Chemin absolu où l'application sera déployée sur le Raspberry Pi (ex: `/home/pi/app`).
    * **`PI_HOST`** et **`PI_USER`** : Informations de connexion SSH pour votre Pi.
    * **`AP_SSID`** et **`AP_WIFI_PASSWORD`** : Nom et mot de passe pour le point d'accès Wi-Fi créé par le Raspberry Pi.
    

## 5\. Déploiement et Lancement sur Raspberry Pi (Automatisé avec `deploy.sh`)

Le script `deploy.sh` automatise l'intégralité du processus de déploiement, y compris la création des dossiers, le transfert des fichiers, l'installation des dépendances Python et système, et la configuration des services `systemd`.

### 5.1. Prérequis pour le script `deploy.sh`

1.  **Fichier `.env` configuré :** Assurez-vous d'avoir créé et configuré votre fichier `.env` à la racine de votre projet avec les bonnes valeurs pour `RASPBERRY_PI_HOST`, `RASPBERRY_PI_USER`, `PI_PROJECT_ROOT` et `LOCAL_PROJECT_DIR`.
2.  **Rendre le script exécutable :** Ouvrez un terminal sur votre Mac, naviguez jusqu'au dossier parent de votre projet, et exécutez :
    ```bash
    chmod +x votre_projet/deploy.sh
    ```
    (Remplacez `votre_projet` par le nom réel de votre dossier de projet).
3.  **Configuration SSH sans mot de passe (CRITIQUE) :** C'est **indispensable** pour que le script `deploy.sh` puisse se connecter et exécuter des commandes sur votre Raspberry Pi sans intervention manuelle.
    * **Générez une paire de clés SSH** sur votre machine locale (si vous n'en avez pas déjà une) :
        ```bash
        ssh-keygen -t rsa -b 4096
        ```
        (Appuyez sur Entrée pour les options par défaut, laissez la passphrase **vide** pour l'automatisation).
    * **Copiez votre clé publique sur le Raspberry Pi** (vous devrez entrer le mot de passe du Pi pour la *dernière fois*) :
        ```bash
        ssh-copy-id ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}
        ```
        Si la commande `ssh-copy-id` n'est pas disponible, suivez un tutoriel pour le faire manuellement (cela implique de copier le contenu de `~/.ssh/id_rsa.pub` dans `~/.ssh/authorized_keys` sur le Pi).
    * Le script `deploy.sh` vérifiera que cette configuration est fonctionnelle.

### 5.2. Lancement du Déploiement :

1.  **Assurez-vous que votre projet local (`LOCAL_PROJECT_DIR`) est propre** et contient toutes les dernières modifications.
2.  **Exécutez le script depuis le répertoire *parent* de votre projet** sur votre Mac :
    Si votre dossier de projet s'appelle `mon_app_audio` et qu'il est dans `/Users/votre_nom/projets/`, ouvrez le terminal dans `/Users/votre_nom/projets/` et exécutez :
    ```bash
    ./mon_app_audio/deploy.sh
    ```
    Le script va :
    * Lire votre `.env` local pour obtenir les configurations.
    * Créer les répertoires nécessaires sur le Pi.
    * Transférer l'intégralité de votre dossier de projet vers le Raspberry Pi.
    * **Créer un fichier `.env` sur le Raspberry Pi** avec `IS_RASPBERRY_PI=True` et les autres configurations spécifiques au Pi.
    * Installer les dépendances système et Python (`python-dotenv` inclus).
    * Créer/mettre à jour les services `systemd`.
    * Redémarrer les services.

### 5.3. Accès à l'Interface Web et Débogage

* Suivez les instructions de la section "Accès à l'Interface Web" dans le `README.md` actuel.
* Pour le débogage, utilisez `journalctl` comme indiqué dans le `README.md` actuel.

### Accès à l'Interface Web

Une fois le déploiement terminé, ouvrez votre navigateur web (sur n'importe quel appareil de votre réseau) et accédez à l'adresse IP de votre Raspberry Pi, suivi du port de l'API (par défaut 5000) :

`http://<adresse_ip_du_pi>:5000/index.html`

Remplacez `<adresse_ip_du_pi>` par l'adresse IP réelle de votre Raspberry Pi.

### Débogage sur Raspberry Pi (via SSH)

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
  * **Erreurs de permissions :** Si vous rencontrez des erreurs de permission (`Permission denied`), assurez-vous que l'utilisateur `pi` a les droits d'accès aux dossiers audio et logs. Le script de déploiement tente de les créer avec les droits appropriés.

## 6\. Développement et Test sur Mac

Ces étapes sont à effectuer sur votre machine de développement (Mac).

### 6.1. Configuration des Fichiers

Assurez-vous que votre fichier `.env` local à la racine de votre projet contient la ligne suivante :

```python
IS_RASPBERRY_PI = False
```

### 6.2. Installation des Dépendances

Naviguez dans le dossier de votre projet et installez les dépendances :

```bash
cd /chemin/vers/votre_projet/
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-Cors python-dotenv
```

### 6.3. Lancement des Scripts

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

  * Pour mettre à jour le code sur le Raspberry Pi, il suffit de relancer le script `deploy.sh`. Il transférera les fichiers modifiés et redémarrera les services.
  * Vérifiez régulièrement l'espace disque sur le Pi, surtout si les fichiers de log ne sont pas gérés (rotations de logs, limites de taille). Actuellement, la limite de 50 entrées dans l'API Flask et la lecture des 50 dernières entrées du fichier de log du planificateur aident à contrôler la taille. Pour une solution de production plus robuste, utilisez des outils de rotation de logs comme `logrotate` sur le Pi pour `/home/pi/logs/audio_player.log`.
