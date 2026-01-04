import logging
# program/dependencies/dependency_factory.py
from PyQt6.QtWidgets import QMainWindow
from program.utils.paths import PathManager
from program.fonts.font_registry import FontRegistry
from program.preferences.language_manager import LanguageManager
from program.fonts.ass_font_manipulator import AssFontManipulator
from program.fonts.font_manager import FontManager
from program.preferences.user_preferences import UserPreferences
from program.video.video_embedder import IncrusteurVideo
from program.controllers.embedding_controller import IncrustationController
from program.core.tasks_manager import TasksManager
from program.subtitles.model_manager import ModelManager 
from program.controllers.audio_controller import AudioController 
from program.controllers.transcription_controller import TranscriptionController
from program.utils.internet_monitor import InternetMonitor
from program.controllers.youtube_controller import YoutubeController
from program.ui.dialogs_manager import DialogsManager
from program.validation.protection_detector import ProtectionDetector
from program.validation.media_validator import MediaValidator


class DependencyFactory:
    """
    Classe Factory responsable de l'initialisation et de l'assemblage
    de toutes les dépendances de l'application.
    """

    def __init__(self, window: QMainWindow):
        """
        Initialise la Factory avec la fenêtre principale (Vue).
        """
        self.window = window


    def build_tasks_manager(self) -> TasksManager:
        """
        Construit tous les composants dans l'ordre de dépendance et retourne
        le contrôleur maître (TasksManager).
        """
        
        # 1. Classes de Base (aucune dépendance externe)
        self.path_manager = PathManager()
        self.font_registry = FontRegistry() 
        
        # 2. Classes de Support (Dépendent de PathManager ou FontRegistry)
        chemin_languages = self.path_manager.get_path("ressources/languages/languages.json")
        self.language_manager = LanguageManager(languages_file_path=chemin_languages)
        self.ass_manipulator = AssFontManipulator() 
        
        
        self.dialogs_manager = DialogsManager()
        self.protection_detector = ProtectionDetector()

        # 3. Contrôleurs de Ressources (Suite)
        self.font_manager = FontManager(parent=self.window) 
        self.user_preferences = UserPreferences(font_manager=self.font_manager)
        
        # 4. Moteurs (Dépendent des préférences)
        dossier_projet = self.path_manager.get_project_root()
        self.incrusteur_video = IncrusteurVideo(
        dossier_projet = dossier_projet, 
        user_preferences=self.user_preferences 
        )

        self.internet_monitor = InternetMonitor()
        
        
        
        # 5. Contrôleurs de Tâches (Dépendent des Moteurs et de la Fenêtre)
        self.incrustation_controller = IncrustationController(
            parent_window=self.window, 
            output_path_base="", 
            incrusteur=self.incrusteur_video,
            dialogs_manager=self.dialogs_manager,
            protection_detector=self.protection_detector,
            ass_font_manipulator=self.ass_manipulator,
            font_manager=self.font_manager, 
            user_preferences = self.user_preferences 
        )

        self.youtube_controller = YoutubeController(monitor=self.internet_monitor)
        


        # Création du ModelManager (dépend de PathManager pour les chemins)
        
        self.model_manager = ModelManager(repo_id="Systran/faster-whisper-small")
        
        # Création du AudioController (dépend de DialogsManager pour les dialogues de progression)
        self.audio_controller = AudioController(
        dialogs_manager =self.dialogs_manager 
        )


        # Création du TranscriptionController 
        # (dépend de ModelManager, UserPreferences, DialogsManager)
        self.transcription_controller = TranscriptionController(
            model_manager=self.model_manager,
            user_preferences=self.user_preferences,
            dialogs_manager=self.dialogs_manager
        )
        #Création du validateur(depends de path_manager pour ffmpeg)
        self.validator = MediaValidator(
        path_manager = self.path_manager        
        )
        
        # 6. Contrôleur Maître (TasksManager)
        self.tasks_manager = TasksManager(
        main_window=self.window,
        incrustation_controller = self.incrustation_controller,
        # Dépendances pour le workflow
        audio_controller = self.audio_controller,
        transcription_controller=self.transcription_controller,
        youtube_controller=self.youtube_controller,  
        dialogs_manager=self.dialogs_manager,
        dossier_projet = dossier_projet         ,
        user_preferences=self.user_preferences,  
        media_validator = self.validator 
        )



        return self.tasks_manager
