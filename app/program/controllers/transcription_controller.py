# program/controllers/transcription_controller.py
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QProgressBar, QMessageBox  
from program.subtitles.model_manager import ModelManager
from program.preferences.user_preferences import UserPreferences
from program.ui.dialogs_manager import DialogsManager
from program.workers.ass_generation_worker import ASSGenerationWorker 
from program.workers.progress_worker import ProgressThread 
from program.utils.internet_monitor import InternetMonitor 

class TranscriptionController(QObject):
    """
    Contrôleur responsable de la séquence complète de transcription :
    1. Gérer le chargement/téléchargement du modèle (via ModelManager).
    2. Orchestrer la transcription réelle (via ASSGenerationWorker).
    3. Gérer les signaux de succès/échec vers le TasksManager.
    """
    
    transcriptionSuccess = pyqtSignal(str) # Émet le chemin du fichier ASS généré
    transcriptionFailed = pyqtSignal(str)  # Émet le message d'erreur

    modelReady = pyqtSignal()  # Émis quand modèle chargé (sync ou async)
    modelFailed = pyqtSignal(str)  # Émis quand échec

    def __init__(self, model_manager: ModelManager, user_preferences: UserPreferences, dialogs_manager: DialogsManager):
        super().__init__()
        
        self.model_manager = model_manager
        self.user_preferences = user_preferences
        self.dialogs_manager = dialogs_manager
        
        self._whisper_model = None # Stocke l'objet modèle Whisper chargé (faster_whisper.WhisperModel)
        self._transcription_worker = None
        self._transcription_thread = None
        self._progress_bar = None 
        self._progress_thread = None  # AJOUT pour la progression audible
        
        # Connexion des signaux de fin d'opération du ModelManager
        self.model_manager.modelReady.connect(self._on_model_loaded_ready)
        self.model_manager.downloadFailed.connect(self._on_model_load_failed)


    def verify_and_load_model(self, parent_widget, progress_bar):
        """
        Déclenche le chargement ou le téléchargement du modèle Whisper.
        Retourne True si le modèle est chargé de manière synchrone (déjà sur disque).
        """
        print("[TranscriptionController] Vérification/Chargement du modèle...")
        
        # InternetMonitor est utilisé ici pour la vérification immédiate avant téléchargement
        monitor = InternetMonitor() 
        
        # Le ModelManager gère l'UI (progress_bar, parent_window) et émet modelReady/downloadFailed
        model = self.model_manager.get_model(
            progress_bar=progress_bar, 
            parent_window=parent_widget,
            monitor=monitor
        )
        
        if model:
            # Cas synchrone : Modèle déjà présent et chargé.
            self._whisper_model = model
            print("[TranscriptionController] Modèle Whisper chargé synchrone.")
            self.modelReady.emit()  
            return True
            
        # Sinon, le ModelManager est en cours de téléchargement/chargement asynchrone.
        return False


    def _on_model_loaded_ready(self, model):
        """Déclenché par ModelManager.modelReady (fin de chargement/téléchargement asynchrone)."""
        self._whisper_model = model
        print("[TranscriptionController] Modèle Whisper prêt (via signal ModelReady).")
        # Le TasksManager doit écouter ce signal 
        self.modelReady.emit()

    def _on_model_load_failed(self, message):
        """Déclenché par ModelManager.downloadFailed."""
        # Émettre l'échec vers le TasksManager pour arrêter le workflow
        self.modelFailed.emit(message)


    def start_transcription(self, audio_path: str, ass_path: str, progress_bar: QProgressBar):
        """
        Démarre le processus de transcription réel en arrière-plan.
        Utilise la barre de progression fournie.
        """
        if not self._whisper_model:
            error_msg = "Modèle non chargé. Impossible de lancer la transcription."
            self.transcriptionFailed.emit(error_msg)
            return

        if self._transcription_thread and self._transcription_thread.isRunning():
            print("[TranscriptionController] Une transcription est déjà en cours. Opération annulée.")
            return

        self._progress_bar = progress_bar 
        
        # 1. Préparation de la barre (elle va de 0 à 99 et recommence)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 100)
        
        # 2. Démarrage du simulateur de progression cyclique
        self._progress_thread = ProgressThread() 
        self._progress_thread.progress.connect(self._progress_bar.setValue)
        self._progress_thread.start()
        

        print(f"[TranscriptionController] Préparation de la transcription pour : {audio_path}")
            
        # 1. Créer le Worker de transcription/génération ASS
        self._transcription_worker = ASSGenerationWorker(
            audio_path=audio_path,
            ass_path=ass_path,
            user_preferences=self.user_preferences,
            modele=self._whisper_model # L'objet modèle chargé (faster_whisper.WhisperModel)
        )
        
        # 2. Créer le Thread pour l'exécution
        self._transcription_thread = QThread()
        self._transcription_worker.moveToThread(self._transcription_thread)

        # 3. Connexion des signaux
        self._transcription_thread.started.connect(self._transcription_worker.run)
        self._transcription_worker.finished.connect(self._on_transcription_success)
        self._transcription_worker.error.connect(self._on_transcription_error)
        
        # 4. Lancement asynchrone
        self._transcription_thread.start()
        
        
    def _on_transcription_success(self, message):
        """Appelé lorsque le Worker a terminé avec succès (ASS généré)."""
        if self._progress_thread:
            self._progress_thread.stop() # Utilise la méthode stop() définie dans ProgressThread
            self._progress_thread.wait()
            self._progress_thread = None

        if self._progress_bar:
            # Forcer la valeur finale de 100% après l'arrêt du cycle 0-99
            self._progress_bar.setValue(100) 
            self._progress_bar.setVisible(False)


        # Le chemin ASS est connu via le constructeur ou l'attribut du Worker
        ass_path = self._transcription_worker.ass_path
        print(f"[TranscriptionController] {message} Fichier : {ass_path}")
        
        self.transcriptionSuccess.emit(ass_path)
        self._cleanup_thread()


    def _on_transcription_error(self, message):
        """Appelé lorsque le Worker rencontre une erreur."""
        if self._progress_thread:
            self._progress_thread.stop() 
            self._progress_thread.wait()
            print(f"[Debug] Thread de progression vivant : {self._progress_thread.isRunning()}")
            self._progress_thread = None


                # Masquer la barre de progression 
        if self._progress_bar:
            self._progress_bar.setVisible(False)
        

        # Emit de l'erreur 
        self.transcriptionFailed.emit(message)
        self._cleanup_thread()


    def _cleanup_thread(self):
        """Arrête et nettoie le thread de transcription."""
        if self._transcription_thread:
            self._transcription_thread.quit()
            self._transcription_thread.wait()
            print(f"[Debug] Thread vivant : {self._transcription_thread.isRunning()}")
            self._transcription_thread = None
            self._transcription_worker = None
