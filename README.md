# Guide de Déploiement et Développement de l'Application Audio

Ce guide explique comment déployer l'application de lecteur audio sur un Raspberry Pi 4 ou 5, ainsi que comment la développer et la tester sur un Mac.

## 1\. Structure du Projet

Assurez-vous que votre projet a la structure suivante :

```
votre\_projet/
├── api.py
├── audio\_player.py
├── index.html
├── README.md
├── deploy.sh
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

C'est la partie la plus importante pour basculer entre Mac et Raspberry Pi et garantir la cohérence des chemins.

### Fichiers `api.py` et `audio_player.py`

Ouvrez `api.py` et `audio_player.py` et modifiez les variables au début des fichiers comme suit. Ces modifications garantissent que les chemins d'accès aux fichiers audio et aux logs s'adaptent automatiquement à l'environnement.

```python
# Dans api.py et audio_player.py

IS_RASPBERRY_PI = False # <--- MODIFIEZ CETTE LIGNE !
PI_PROJECT_ROOT = "/home/pi/raspberry-pi-audio-scheduler" 
````

  * **`IS_RASPBERRY_PI = False` (pour Mac) :**
      * Les fichiers audio seront cherchés dans `./audio/` (relatif au répertoire d'exécution du script).
      * Les logs du planificateur seront écrits/lus dans `./temp_planner_log.log`.
      * La lecture audio utilisera `afplay`.
      * Le statut du planificateur et les actions de démarrage/arrêt seront simulés.
  * **`IS_RASPBERRY_PI = True` (pour Raspberry Pi) :**
      * Les fichiers audio seront cherchés dans `/home/pi/raspberry-pi-audio-scheduler/audio/`.
      * Les logs du planificateur seront écrits/lus dans `/home/pi/logs/audio_player.log`.
      * La lecture audio utilisera `mpv --ao=alsa`.
      * Le statut du planificateur et les actions de démarrage/arrêt interrogeront/contrôleront les services `systemd` réels.

## 5\. Déploiement et Lancement sur Raspberry Pi (Automatisé)

Pour déployer ou mettre à jour votre application sur le Raspberry Pi, vous utiliserez le script `deploy.sh`.

### Prérequis pour le script `deploy.sh` :

1.  **Copiez** le contenu du script `deploy.sh` fourni dans un fichier nommé `deploy.sh` à la racine de votre projet (au même niveau que `api.py`).
2.  **Rendez-le exécutable** : Ouvrez un terminal sur votre Mac, naviguez jusqu'au dossier parent de votre projet (par exemple, si votre projet est dans `/Users/votre_nom/projets/mon_app_audio`, naviguez jusqu'à `/Users/votre_nom/projets/`) et exécutez :
    ```bash
    chmod +x mon_app_audio/deploy.sh
    ```
    (Remplacez `mon_app_audio` par le nom réel de votre dossier de projet).
3.  **Modifiez les variables de configuration** au début de `deploy.sh` :
      * **`RASPBERRY_PI_HOST="<ADRESSE_IP_DU_PI_OU_HOSTNAME>"`** : Remplacez par l'adresse IP de votre Raspberry Pi (ex: `192.168.1.100`) ou son hostname (ex: `raspberrypi.local` si mDNS est activé).
      * **`LOCAL_PROJECT_DIR="raspberry-pi-audio-scheduler"`** : **Très important \!** Remplacez `"raspberry-pi-audio-scheduler"` par le nom exact de votre dossier de projet local sur votre Mac.
      * `RASPBERRY_PI_USER` et `RASPBERRY_PI_PROJECT_PATH` peuvent généralement rester par défaut pour un Pi neuf.
4.  **Configurez SSH sans mot de passe** entre votre Mac et le Raspberry Pi. C'est essentiel pour que le script fonctionne sans interaction :
      * Sur votre Mac, générez une paire de clés SSH (si vous n'en avez pas déjà une) :
        ```bash
        ssh-keygen -t rsa -b 4096
        ```
        (Appuyez sur Entrée pour les options par défaut, laissez la passphrase vide pour l'automatisation).
      * Copiez votre clé publique sur le Raspberry Pi (vous devrez entrer le mot de passe du Pi pour la *dernière fois*) :
        ```bash
        ssh-copy-id pi@<adresse_ip_du_pi>
        ```
        Si la commande `ssh-copy-id` n'est pas disponible, vous pouvez le faire manuellement :
        ```bash
        cat ~/.ssh/id_rsa.pub | ssh pi@<adresse_ip_du_pi> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        ```

### Lancement du Déploiement :

1.  **Assurez-vous que votre projet local (`LOCAL_PROJECT_DIR`) est propre** et contient toutes les dernières modifications.
2.  **Exécutez le script depuis le répertoire *parent* de votre projet** sur votre Mac :
    Si votre dossier de projet s'appelle `mon_app_audio` et qu'il est dans `/Users/votre_nom/projets/`, ouvrez le terminal dans `/Users/votre_nom/projets/` et exécutez :
    ```bash
    ./mon_app_audio/deploy.sh
    ```
    Le script va :
      * Mettre à jour `IS_RASPBERRY_PI = True` dans vos fichiers locaux `api.py` et `audio_player.py`.
      * Créer les répertoires nécessaires sur le Pi (`/home/pi/raspberry-pi-audio-scheduler/audio`, `/home/pi/logs`).
      * Transférer l'intégralité de votre dossier de projet vers le Raspberry Pi.
      * Installer les dépendances système (`mpv`, `python3-pip`, `python3-venv`).
      * Créer un environnement virtuel sur le Pi et installer les dépendances Python (`Flask`, `Flask-Cors`).
      * Créer les services `systemd` (`flask-api.service` et `audio-player.service`) avec les chemins corrects pointant vers l'environnement virtuel.
      * Recharger `systemd`, activer et démarrer les services.
      * Remettre `IS_RASPBERRY_PI = False` dans vos fichiers locaux sur Mac pour le développement.

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

  * Pour mettre à jour le code sur le Raspberry Pi, il suffit de relancer le script `deploy.sh`. Il transférera les fichiers modifiés et redémarrera les services.
  * Vérifiez régulièrement l'espace disque sur le Pi, surtout si les fichiers de log ne sont pas gérés (rotations de logs, limites de taille). Actuellement, la limite de 50 entrées dans l'API Flask et la lecture des 50 dernières entrées du fichier de log du planificateur aident à contrôler la taille. Pour une solution de production plus robuste, utilisez des outils de rotation de logs comme `logrotate` sur le Pi pour `/home/pi/logs/audio_player.log`.
