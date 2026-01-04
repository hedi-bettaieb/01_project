import logging
# program/controllers/audio_controller.py (Version Corrigée)
from PyQt6.QtCore import QObject, pyqtSignal, QThread # QThread est toujours nécessaire pour les types
from PyQt6.QtWidgets import QProgressBar 
from program.workers.audio_worker import AudioConversionWorker 
from program.workers.progress_worker import ProgressThread 
from program.ui.dialogs_manager import DialogsManager
import subprocess
from pathlib import Path

class AudioController(QObject):
    """
    Contrôleur responsable de l'orchestration de la conversion Vidéo -> Audio (MP3).
    Gère le Worker de conversion et le simulateur de progression.
    """
    conversionSuccess = pyqtSignal(str)
    conversionFailed = pyqtSignal(str)


    def __init__(self, dialogs_manager): 
        super().__init__()
        self.dialogs_manager = dialogs_manager
        self._conversion_worker: AudioConversionWorker | None = None
        self._progress_bar: QProgressBar | None = None 
        self._progress_thread: ProgressThread | None = None 
        

    
    def start_conversion(self, video_path: str, audio_path: str, progress_bar: QProgressBar):
        """
        Déclenche la conversion audio sur un thread séparé avec progression simulée.
        """
        
        if self._conversion_worker and self._conversion_worker.isRunning():
            logging.info("[AudioController] Conversion déjà en cours.")
            return

        self._progress_bar = progress_bar 
        self._progress_bar.setVisible(True) 
        self._progress_bar.setRange(0, 100)
        
        # 1. 🟢 Démarrage du simulateur de progression cyclique
        self._progress_thread = ProgressThread() 
        self._progress_thread.progress.connect(self._progress_bar.setValue)
        self._progress_thread.start()
        

        # 2. 🛑 SIMPLIFICATION : Créer et démarrer le Worker/Thread
        self._conversion_worker = AudioConversionWorker(video_path, audio_path)
        
        # 3. Connexions et lancement
        self._conversion_worker.finished.connect(self._on_conversion_success)
        self._conversion_worker.error.connect(self._on_conversion_error)
        # Note : Pas besoin de connecter started.connect(worker.run), car worker.start() appelle run()

        logging.info(f"[AudioController] Lancement de la conversion : {video_path} -> {audio_path}")
        self._conversion_worker.start()


    def _on_conversion_success(self, message):
        """Gère le signal de réussite du Worker."""
        
        # 1. 🔴 Arrêter et nettoyer le simulateur de progression
        if self._progress_thread:
            self._progress_thread.stop() 
            self._progress_thread.wait()
            self._progress_thread = None

        # 2. Mise à jour finale de l'UI
        if self._progress_bar:
            self._progress_bar.setValue(100) 
            self._progress_bar.setVisible(False) 
            
        # 3. Émission du signal et nettoyage du Worker
        audio_path = self._conversion_worker.audio_path
        self.conversionSuccess.emit(audio_path)
        self._cleanup_worker()
    
    
    def _on_conversion_error(self, message):
        """Gère le signal d'erreur du Worker."""
        
        # 1. 🔴 Arrêter et nettoyer le simulateur de progression
        if self._progress_thread:
            self._progress_thread.stop() 
            self._progress_thread.wait()
            self._progress_thread = None

        # 2. Mise à jour finale de l'UI
        if self._progress_bar:
            self._progress_bar.setValue(0)
            self._progress_bar.setVisible(False) 
        
        # 3. Affichage de l'erreur, émission du signal et nettoyage du Worker
        logging.info(message) 
        
        self.conversionFailed.emit(message)
        self._cleanup_worker()


    def _cleanup_worker(self):
        """Nettoyage du Worker/Thread."""
        if self._conversion_worker:
            self._conversion_worker.quit()
            self._conversion_worker.wait()
            self._conversion_worker = None