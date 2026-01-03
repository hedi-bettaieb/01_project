# program/workers/model_worker.py
import os
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from huggingface_hub import snapshot_download
from program.utils.internet_monitor import InternetMonitor
from program.utils.paths import PathManager


class ModelDownloadWorker(QThread):
    """
    Thread dédié au téléchargement d'un modèle depuis Hugging Face.
    Émet des signaux pour les mises à jour de statut, la réussite ou les erreurs.
    """
    statusChanged = pyqtSignal(str)
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)
    stopRequested = pyqtSignal()

    def __init__(self, repo_id, local_dir, monitor: InternetMonitor, parent=None):
        """
        Initialise le worker avec les informations du modèle et le moniteur Internet.

        Args:
            repo_id (str): Identifiant du dépôt Hugging Face.
            local_dir (str): Dossier local de destination.
            monitor (InternetMonitor): Instance pour surveiller la connexion Internet.
            parent (QObject, optional): Parent Qt. Par défaut None.
        """
        super().__init__(parent)
        self.repo_id = repo_id
        self.local_dir = local_dir
        self.monitor = monitor
        self.stop_monitor_event = threading.Event()
        self.monitor_thread = None
        self.is_download_aborted = False

    def _background_monitor_run(self):
        """
        Fonction exécutée en arrière-plan pour surveiller la connexion Internet.
        Émet un signal en cas de perte de connexion durable.
        """
        if not self.monitor.monitor_internet_connection(self.stop_monitor_event, check_interval=5, max_failures=3):
            self.is_download_aborted = True
            self.statusChanged.emit("⚠ PERTE DE CONNEXION DURABLE DÉTECTÉE. Le téléchargement pourrait échouer.")
            self.error.emit("Perte de connexion Internet durable. Le téléchargement ne peut pas continuer.")
            self.stopRequested.emit()

    def _stop_monitor(self):
        """Arrête proprement le thread de surveillance."""
        self.stop_monitor_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)

    def run(self):
        """
        Télécharge le modèle depuis Hugging Face et gère les signaux de statut.
        """
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
                self.error.emit("Erreur : Connexion Internet indisponible. Veuillez vous connecter pour télécharger le modèle.")
                return

            self.monitor_thread = threading.Thread(target=self._background_monitor_run, daemon=True)
            self.monitor_thread.start()

            self.statusChanged.emit("Téléchargement du modèle depuis Hugging Face...")
            snapshot_download(
                repo_id=self.repo_id,
                local_dir=str(local_dir),
                cache_dir=str(models_folder),
                force_download=False,
                ignore_patterns=["*.msgpack"],
                tqdm_class=None
            )

            self._stop_monitor()

            if self.is_download_aborted:
                self.finished.emit(local_dir, f"Le modèle '{self.repo_id}' a été téléchargé avec succès MAIS une instabilité de connexion a été détectée.")
            else:
                self.statusChanged.emit("Téléchargement terminé.")
                self.finished.emit(local_dir, f"Le modèle '{self.repo_id}' a été téléchargé avec succès.")

        except Exception as e:
            self._stop_monitor()
            self.error.emit(f"Erreur lors du téléchargement du modèle : {str(e)}")
