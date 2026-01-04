import logging
# program/controllers/youtube_controller.py
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from program.workers.youtube_worker import YoutubeDownloadWorker
from program.utils.internet_monitor import InternetMonitor # Assurez-vous d'avoir cet import

class YoutubeController(QObject):
    """Contrôleur responsable de la gestion des opérations YouTube (téléchargement)."""
    
    downloadSuccess = pyqtSignal(str, str) # video_path, title
    downloadFailed = pyqtSignal(str , str) # error_messag , video_title e

    def __init__(self, monitor: InternetMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.worker = None
        
        # Assurez-vous que l'InternetMonitor est injecté dans la Factory

    def is_internet_available(self) -> bool:
        """Vérifie l'état de la connexion Internet."""
        return self.monitor.check_internet_connection() 

    def start_download(self, url: str, progress_bar, output_dir: str):
        """Lance le téléchargement de la vidéo dans un thread."""
        
        # Passage du dossier de destination au Worker
        self.worker = YoutubeDownloadWorker(url, monitor=self.monitor, output_dir=output_dir)
        
        # Connexions des signaux du Worker au Controller
        self.worker.progress.connect(progress_bar.setValue)
        self.worker.statusUpdate.connect(lambda msg: logging.info(f"[YT-Controller] {msg}"))
        
        self.worker.finished.connect(self._handle_download_success)
        self.worker.error.connect(self._handle_download_error)
        
        self.worker.start()



    def start00_download(self, url: str, progress_bar):
        """Lance le téléchargement de la vidéo dans un thread."""
        
        self.worker = YoutubeDownloadWorker(url, monitor=self.monitor)
        
        # Connexions des signaux du Worker au Controller
        self.worker.progress.connect(progress_bar.setValue)
        self.worker.statusUpdate.connect(lambda msg: logging.info(f"[YT-Controller] {msg}")) # Mise à jour interne
        
        self.worker.finished.connect(self._handle_download_success)
        self.worker.error.connect(self._handle_download_error)
        
        # ⚠️ Le signal stopRequested du Worker doit être géré pour appeler worker.terminate() si nécessaire, 
        # mais pour l'instant, nous laissons le worker se terminer seul ou émettre l'erreur.
        
        self.worker.start()

    def _handle_download_success(self, video_path: str, title: str):
        """Réussite du téléchargement. Émet le signal pour le TasksManager."""
        self.downloadSuccess.emit(video_path, title)
        # Nettoyage du worker (si vous le faites manuellement)
        self.worker = None
      
    def _handle_download_error(self, message: str, title: str):
        """Échec du téléchargement. Affiche un message et signale l'erreur au TasksManager."""
        #QMessageBox.critical(None, "Erreur de Téléchargement YouTube", message)
        self.downloadFailed.emit(message, title) 
        self.worker = None
