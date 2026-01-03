#program/subtitle/model_manager.py
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QMessageBox 
from program.utils.paths import PathManager
from program.ui.customized_messages import customized_message
from faster_whisper import WhisperModel
from program.workers.progress_worker import ProgressThread
from program.workers.model_worker import ModelDownloadWorker 
from program.utils.internet_monitor import InternetMonitor

class ModelManager(QObject):
    """Gère le téléchargement et chargement du modèle Whisper."""
    
    modelReady = pyqtSignal(object)
    downloadFailed = pyqtSignal(str) # 🎯 NOUVEAU SIGNAL pour informer l'Orchestrateur de l'échec du téléchargement
    
    def __init__(self, repo_id="Systran/faster-whisper-small", parent=None):
        super().__init__(parent)
        self.repo_id = repo_id
        self.pm = PathManager()
        self.local_dir = os.path.join(
            self.pm.get_path("ressources/models"), 
            "faster_whisper/small"
        )
        self.download_worker = None
        self.progress_thread = None
        self.progress_bar = None
        self.btn = None
        self.parent_window = None

    def start_download(self, monitor):
        """Démarre le téléchargement avec barre de progression et surveillance internet."""
        if self.progress_bar:
            self.progress_bar.setValue(0)
        
        # Créer et démarrer le thread de progression (pour l'UI)
        self.progress_thread = ProgressThread()
        if self.progress_bar:
            self.progress_thread.progress.connect(self.progress_bar.setValue)
        self.progress_thread.start()
        
        # Créer et démarrer le worker de téléchargement
        self.download_worker = ModelDownloadWorker(
            repo_id=self.repo_id, 
            local_dir=self.local_dir,
            monitor=monitor, 
            parent=self
        )
        
        # Connexion du nouveau signal d'arrêt forcé
        self.download_worker.stopRequested.connect(self._on_stop_requested) 
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_download_error)
        self.download_worker.statusChanged.connect(
            lambda msg: print(f"[Download Status] {msg}")
        )
        self.download_worker.start()
    
    def _stop_progress(self):
        """Arrête proprement le thread de progression"""
        if self.progress_thread and self.progress_thread.isRunning():
            self.progress_thread.stop()
            self.progress_thread.wait()
            self.progress_thread = None
    
    def _on_download_finished(self, path, message):
        """Appelé quand le téléchargement réussit."""
        self._stop_progress()
        if self.progress_bar:
            self.progress_bar.setValue(100)
        
        customized_message(self.parent_window, "Succès", f"{message}")
        
        # Charger et émettre le modèle
        model = self._load_model()
        if model:
            self.modelReady.emit(model)
    
    def _on_download_error(self, message):
        """Appelé en cas d'erreur de téléchargement."""
        self._stop_progress()
        if self.progress_bar:
            self.progress_bar.setValue(0)
        print(message)
        # 🎯 CHANGEMENT : Émettre le signal d'échec vers l'Orchestrateur
        self.downloadFailed.emit(message)
        # QMessageBox.critical(self.parent_window, "Erreur", f"{message}") # Supprimé, l'orchestrateur gère l'UI

    def is_model_complete(self):
        """Vérifie si le modèle existe et est valide."""
        model_file = os.path.join(self.local_dir, "model.bin")
        return (os.path.exists(model_file) and 
                os.path.getsize(model_file) > 1024 * 1024)
    
    def get_model(self, progress_bar, parent_window, monitor):
        """
        Point d'entrée principal - lance le téléchargement si nécessaire.
        Retourne le modèle chargé ou None.
        """
        self.progress_bar = progress_bar
        self.parent_window = parent_window
        
        if self.is_model_complete():
            print(f"Modèle disponible.\n\nChemin : {self.local_dir}" )
            # La notification est gérée par l'orchestrateur ou l'appelant s'il le souhaite
            return self._load_model()
        
        # Modèle absent
        
        # Vérification immédiate de la connexion Internet
        if not monitor.check_internet_connection():
            error_msg = "❌ Connexion Internet indisponible. Impossible de télécharger le modèle."
            self._on_download_error(error_msg) # Émet downloadFailed
            return None
            
        # Modèle absent et Internet OK : on démarre le téléchargement
        print("Modèle absent, téléchargement en cours...")
        # QMESSAGE AVANT TÉLÉCHARGEMENT
        QMessageBox.information(
            parent_window, # Utilisation du parent_window fourni pour la modalité
            "Modèle Indisponible",
            "Le modèle de transcription est absent de votre système. Il sera téléchargé immédiatement."
        )

        if self.progress_bar:
            self.progress_bar.setVisible(True) 
        self.start_download(monitor)
        return None

    
    def _load_model(self, parent_window=None):
        """Charge le modèle avec fallback GPU → CPU."""
        target_window = parent_window or getattr(self, 'parent_window', None)
        # [...] (Logique de chargement de modèle inchangée) [...]
        try:
            # 1) Essai GPU
            try:
                model = WhisperModel(self.local_dir, device="cuda", compute_type="float16")
                print("Modèle chargé (GPU - FP16).")
                return model
            except Exception:
                pass 
            # 2) CPU int8 (optimisé)
            try:
                model = WhisperModel(self.local_dir, device="cpu", compute_type="int8")
                print("Modèle chargé (CPU - INT8 optimisé)." )
                return model
            except Exception:
                pass
            # 3) CPU float32 (compatibilité max)
            model = WhisperModel(self.local_dir, device="cpu", compute_type="float32")
            print("Model chargé (CPU - FLOAT32 compatibilité maximale)." )
            return model
            
        except Exception as e:
            QMessageBox.critical(target_window, "model manager-ligne 150-Erreur chargement", f"❌ {e}")
            return None


    def _on_stop_requested(self):
        """Appelé lorsque le thread de surveillance détecte une perte de connexion durable."""
        print("❌ Nettoyage forcé suite à une perte de connexion Internet.")
        self._stop_progress()
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.terminate()
            self.download_worker.wait()
        
