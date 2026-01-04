import logging
# program/workers/model_worker.py
import os
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from huggingface_hub import snapshot_download
from program.utils.internet_monitor import InternetMonitor
from program.utils.paths import PathManager

import os
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from huggingface_hub import snapshot_download
from program.utils.internet_monitor import InternetMonitor
from program.utils.paths import PathManager

class ModelDownloadWorker(QThread):
    """Thread dédié au téléchargement d'un modèle depuis Hugging Face."""
    
    statusChanged = pyqtSignal(str)
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)
    stopRequested = pyqtSignal()
    
    def __init__(self, repo_id, local_dir, monitor):
        super().__init__()  # ⚠️ PAS de parent !
        self.repo_id = repo_id
        self.local_dir = local_dir
        self.monitor = monitor
        self.is_download_aborted = False
        self.monitor_thread = None
        self._monitor_running = False
    
    def run(self):
        """Télécharge le modèle depuis Hugging Face."""
        logging.info("🔵 [DEBUG] ModelDownloadWorker.run() DÉMARRÉ")
        
        try:
            pm = PathManager()
            models_folder = pm.get_path("ressources/models")
            local_dir = os.path.join(models_folder, "faster_whisper/small")
            os.makedirs(local_dir, exist_ok=True)
            
            os.environ["HF_HOME"] = str(models_folder)
            os.environ["HUGGINGFACE_HUB_CACHE"] = str(models_folder)
            os.environ["HF_HUB_CACHE"] = str(models_folder)
            
            self.statusChanged.emit(f"Dossier du modèle : {local_dir}")
            self.statusChanged.emit("Vérification de la connexion Internet...")
            
            if not self.monitor.check_internet_connection():
                self.error.emit("Erreur : Connexion Internet indisponible.")
                return
            
            # Démarrer la surveillance
            self._monitor_running = True
            self.monitor_thread = threading.Thread(
                target=self._background_monitor_run, 
                daemon=True
            )
            self.monitor_thread.start()
            
            self.statusChanged.emit("Téléchargement du modèle depuis Hugging Face...")
            
            # Téléchargement
            snapshot_download(
                repo_id=self.repo_id,
                local_dir=str(local_dir),
                cache_dir=str(models_folder),
                force_download=False,
                ignore_patterns=["*.msgpack"],
                tqdm_class=None
            )
            
            logging.info("🟢 [DEBUG] snapshot_download() TERMINÉ")
            
            # Arrêter la surveillance
            self._stop_monitor()
            
            logging.info("🟢 [DEBUG] Monitor arrêté")
            
            # Émettre le signal de fin
            message = f"Le modèle '{self.repo_id}' a été téléchargé avec succès."
            if self.is_download_aborted:
                message += " MAIS une instabilité de connexion a été détectée."
            
            self.statusChanged.emit("Téléchargement terminé.")
            
            logging.info(f"🟢 [DEBUG] Émission du signal finished: {local_dir}")
            self.finished.emit(local_dir, message)
            logging.info("🟢 [DEBUG] Signal finished ÉMIS")
            
        except Exception as e:
            logging.error(f"🔴 [DEBUG] Exception capturée: {e}")
            self._stop_monitor()
            self.error.emit(f"Erreur lors du téléchargement : {str(e)}")
        
        logging.info("🔵 [DEBUG] ModelDownloadWorker.run() TERMINÉ")
    
    def _stop_monitor(self):
        """Arrête le thread de surveillance."""
        self._monitor_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
    
    def _background_monitor_run(self):
        """Surveille la connexion Internet en arrière-plan."""
        import time
        while self._monitor_running:
            if not self.monitor.check_internet_connection():
                logging.info("⚠️ Connexion perdue pendant le téléchargement")
                self.is_download_aborted = True
            time.sleep(5)


