# Moniteur de latence et de bande passante en temps réel

Ce script Python fournit une interface graphique (GUI) sous PyQt5 pour surveiller en continu :

* **La latence** (ping vers 8.8.8.8 toutes les 5 secondes)
* **Le débit** (download et upload toutes les 60 secondes)
* **L’historique** des mesures, enregistré dans un CSV
* **Un indicateur de statut** (✅ OK / ⚠️ / ❌) pour détecter rapidement les anomalies

---

## Fonctionnalités principales

1. **Surveillance du ping** via `ping3`
2. **Tests de débit** via :

   * Librairie Python `speedtest`
   * CLI `speedtest-cli` ou `speedtest` (fallback)
   * Téléchargement/upload HTTP manuel si les deux précédents échouent
3. **Graphiques dynamiques** avec `pyqtgraph`
4. **Journalisation automatique** dans `network_history.csv`
5. **Indicateur visuel de statut** (vert/rouge) dans l’interface
6. **Nettoyage** de l’historique via un bouton
7. **Patching** interne pour compatibilité .exe PyInstaller (alias `__builtin__`, `fileno()`)

---

## Prérequis

* Python **3.7+**
* Modules Python :

  ```bash
  pip install ping3 speedtest-cli speedtest pyqt5 pyqtgraph requests
  ```
* (Optionnel) Serveur HTTP pour fallback : accès à `http://speedtest.tele2.net/1MB.zip` et `https://httpbin.org/post`

---

## Installation et exécution

1. **Cloner** ou copier ce dépôt / le fichier `moniteur.py` dans un dossier.
2. **Installer** les dépendances (voir ci‑dessus).
3. **Lancer** l’interface :

   ```bash
   python moniteur.py
   ```
4. L’interface s’ouvre sans console (mode GUI) si vous avez exécuté le script directement.

---

## Génération d’un exécutable Windows (.exe)

1. **Installer** PyInstaller :

   ```bash
   pip install pyinstaller
   ```
2. **Compiler** sans console et en un fichier unique :

   ```bash
   pyinstaller \
     --onefile \
     --windowed \
     --hidden-import speedtest \
     --hidden-import requests \
     moniteur.py
   ```
3. Récupérer l’exécutable dans `dist/moniteur.exe`.

> **Note** : le script inclut un patch en début de fichier pour fournir :
>
> * Un alias `__builtin__` (module Python2 attendu par Speedtest API)
> * Un objet `stdin/stdout` muni d’une méthode `fileno()` pour éviter les erreurs en mode windowed

---

## Fichier de log

* Les `print()` et erreurs internes sont redirigés vers **moniteur.log** si vous remplacez les `print()` par `logging` (voir section ci‑dessus).
* Le CSV `network_history.csv` contient :

  ```csv
  timestamp,ping_ms,download_mbps,upload_mbps
  2025-05-14 13:42:01,10.23,50.12,10.45
  ...
  ```

---

## Personnalisation

* **Intervalle de ping** : modifier `self.timer_ping.start(5000)` (en ms)
* **Intervalle de débit** : modifier `self.timer_speed.start(60000)` (en ms)
* **Serveur de ping** : remplacer `8.8.8.8` par une autre IP/DNS
* **URLs de fallback HTTP** : adapter si vos serveurs internes sont plus fiables
* **Seuils de statut** : ajuster la méthode `update_status()` pour tenir compte de valeurs spécifiques

---

## Dépannage

1. **`ModuleNotFoundError: No module named '__builtin__'`**

   * Vous utilisez un exécutable PyInstaller sans patch : renommez votre script s’il s’appelle `speedtest.py`, ou intégrez le code de patch en début de `moniteur.py`.

2. **`AttributeError: 'NoneType' object has no attribute 'fileno'`**

   * En mode `--windowed`, activez le patch qui redirige `sys.stdin`/`sys.stdout` vers un `TextIOBase` avec `fileno()`.

3. **Debits toujours à 0**

   * Vérifiez que vous avez accès à Internet et que `speedtest-cli` (ou `speedtest`) est installé.
   * Contrôlez les imports de `requests` pour le fallback HTTP.

---

## Licence

Ce projet est distribué sous licence MIT. N’hésitez pas à forker et adapter !

---

*Script développé pour détecter et documenter automatiquement les dégradations de service réseau.*
