import logging
# program/orchestrator/tasks_manager.py
import os 
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox
from pathlib import Path
from program.core.workflow_state import WorkflowState
from program.ui.customized_messages import customized_message


class TasksManager(QObject):
    """
    Orchestrateur intégral.
    Gère les workflows avec messages utilisateur (QMessageBox) et protection contre les doubles traitements.
    """
    workflowStarted = pyqtSignal()
    workflowFinished = pyqtSignal()

    def __init__(self, main_window, incrustation_controller, audio_controller,
                 transcription_controller, youtube_controller, dialogs_manager,
                 dossier_projet, user_preferences, media_validator):
        super().__init__()
        self.window = main_window

        # Contrôleurs
        self.incrustation_controller = incrustation_controller
        self.audio_controller = audio_controller
        self.transcription_controller = transcription_controller
        self.youtube_controller = youtube_controller
        # Autres injections
        self.dialogs_manager = dialogs_manager
        self.user_preferences = user_preferences
        self.validator = media_validator
        self.dossier_projet = dossier_projet

        # État et Verrous
        self.state = WorkflowState()
        self._is_running = False
        self._original_output_base = ""

        # Connexions des signaux
        self._connect_signals()

    def _connect_signals(self):
        """Connecte les signaux des contrôleurs."""
        self.transcription_controller.modelReady.connect(self._on_model_ready)
        self.transcription_controller.modelFailed.connect(self._on_error)

        self.audio_controller.conversionSuccess.connect(self._on_audio_converted)
        self.audio_controller.conversionFailed.connect(self._on_error)

        self.transcription_controller.transcriptionSuccess.connect(self._on_transcription_success)
        self.transcription_controller.transcriptionFailed.connect(self._on_error)

        self.incrustation_controller.incrustationSuccess.connect(self._on_incrustation_finished)
        self.incrustation_controller.incrustationFailed.connect(self._on_error)

        self.youtube_controller.downloadSuccess.connect(self._on_youtube_download_success)
        self.youtube_controller.downloadFailed.connect(self._on_youtube_download_error)

    # =========================================================================
    # VÉRIFICATIONS ET UTILITAIRES
    # =========================================================================

    def _can_start(self):
        """Vérifie le verrou et l'interface."""
        if self._is_running or not self.window.btn_process.isEnabled():
            QMessageBox.information(self.window, "Attention", "Un workflow est déjà en cours. Veuillez patienter.")
            return False
        return True

    def _nettoyer_fichiers_part(self, titre_video: str):
        """
        Supprime les fichiers temporaires .part en cas d'échec de téléchargement.
        """
        import os
        import glob

        dossier_data = os.path.join(self.dossier_projet, "data")
        if not os.path.exists(dossier_data):
            return

        try:
            pattern = os.path.join(dossier_data, f"{titre_video}*.part")
            fichiers_part = glob.glob(pattern)

            fichiers_supprimes = 0
            for chemin_complet in fichiers_part:
                try:
                    os.remove(chemin_complet)
                    fichiers_supprimes += 1
                except Exception as e:
                    logging.info(f"⚠️ Impossible de supprimer {os.path.basename(chemin_complet)} : {e}")

            if fichiers_supprimes > 0:
                logging.info(f"✅ Nettoyage terminé : {fichiers_supprimes} fichier(s) .part supprimé(s).")

        except Exception as e:
            logging.info(f"⚠️ Erreur lors du nettoyage des fichiers .part : {e}")

    # =========================================================================
    # WORKFLOWS
    # =========================================================================

    def run_local_auto_workflow(self, parent_widget):
        if not self._can_start():
            return

        logging.info("[TasksManager][STEP] Début workflow auto")
        self._is_running = True
        self.workflowStarted.emit()

        QMessageBox.information(self.window, "Démarrage", "Démarrage du workflow automatique...")
        
        
        
        video = self.dialogs_manager.select_video_file(parent_widget)
        if not video:
            return self._finish()

        logging.info(f"[TasksManager] Vérification intégrité vidéo: {video}")
        is_ok, msg = self.validator.verify_media(video)
        if not is_ok:
            QMessageBox.critical(self.window, "Erreur Vidéo", f"La vidéo est invalide :\n{msg}")
            logging.error(f"[TasksManager][ERROR] {msg}")
            return self._finish()

        self.state.reset()
        self.state.set_video(video)
        self.window.label_video.setText(f"Vidéo: {Path(video).name}")
        self.window.progress_bar.setVisible(True)
        self.window.progress_bar.setValue(5)

        if not self.dialogs_manager.demander_preferences_style(self.user_preferences, parent_widget):
            logging.info("[TasksManager] Configuration style annulée.")
            return self._finish()

        logging.info("[TasksManager][STEP] Fichier validé et style configuré. Chargement du modèle...")
        self.transcription_controller.verify_and_load_model(self.window, self.window.progress_bar)

    def run_manual_ass_workflow(self, parent_widget):
        """Workflow manuel avec messages."""
        if not self._can_start():
            return

        logging.info("[TasksManager][STEP] Début workflow manuel")
        self._is_running = True
        self.workflowStarted.emit()

        self.window.progress_bar.setVisible(True)
        self.window.progress_bar.setValue(0)

        QMessageBox.information(self.window, "Démarrage", "Démarrage du workflow manuel...")

        video = self.dialogs_manager.select_video_file(parent_widget)
        if not video:
            return self._finish()

        logging.info(f"[TasksManager] Vérification intégrité vidéo: {video}")
        is_ok, msg = self.validator.verify_media(video)
        if not is_ok:
            QMessageBox.critical(self.window, "Erreur Vidéo", f"La vidéo est invalide :\n{msg}")
            logging.error(f"[TasksManager][ERROR] {msg}")
            return self._finish()

        self.state.reset()
        self.state.set_video(video)
        self.window.label_video.setText(f"Vidéo: {Path(video).name}")
        self.window.progress_bar.setValue(10)

        ass = self.incrustation_controller.handle_ass_selection_and_validation(parent_widget)
        if not ass:
            return self._finish()

        logging.info(f"[TasksManager] Vérification intégrité vidéo: {video}")
        is_ok, msg = self.validator.verify_media(ass)
        if not is_ok:
            QMessageBox.critical(self.window, "Erreur ASS", f"Le fichier ASS est invalide :\n{msg}")
            logging.error(f"[TasksManager][ERROR] {msg}")
            return self._finish()

        self.state.ass_path = ass
        self.window.progress_bar.setValue(30)

        QMessageBox.information(self.window, "Validation ASS", "✅ Fichier ASS validé avec succès.\nL'incrustation commence...")

        try:
            self._original_output_base = self.incrustation_controller.output_path_base
            self.incrustation_controller.output_path_base = self.state.output_base
            self.incrustation_controller.run_incrustation(video, ass)
        except Exception as e:
            self._on_error(str(e))

    def run_youtube_workflow(self, url, parent_widget):
        """Workflow YouTube en 6 étapes avec messages."""
        if not self._can_start():
            return

        if not self.dialogs_manager.demander_preferences_style(self.user_preferences, parent_widget):
            return self._finish()

        logging.info(f"[TasksManager][STEP] Début workflow YouTube pour: {url}")

        self._is_running = True
        self.workflowStarted.emit()

        self.window.progress_bar.setVisible(True)
        self.window.progress_bar.setValue(0)
        self.window.progress_bar.setRange(0, 100)

        self.state.reset()
        self.state.youtube_url = url
        self.window.label_video.setText(f"URL: {url[:40]}...")

        QMessageBox.information(self.window, "YouTube", f"Démarrage du workflow YouTube...\n\nURL: {url[:60]}...")

        self.window.progress_bar.setValue(5)
        self.transcription_controller.verify_and_load_model(
            self.window, self.window.progress_bar
        )

    # =========================================================================
    # ÉTAPES PARTAGÉES
    # =========================================================================

    def _convert_video_to_audio(self):
        """Extraction audio."""
        if not self._is_running:
            return

        logging.info(f"[TasksManager][STEP] Extraction audio de {self.state.video_path}")
        self.window.progress_bar.setValue(50)

        video = Path(self.state.video_path)
        audio = str(video.parent / f"{video.stem}.mp3")
        self.state.audio_path = audio

        self.audio_controller.start_conversion(
            self.state.video_path, audio, self.window.progress_bar
        )

    def _download_youtube_video(self):
        """Téléchargement YouTube."""
        if not self.youtube_controller.is_internet_available():
            self._on_error("Connexion Internet indisponible")
            return

        # Vérification de sécurité
        dossier_choisi = self.user_preferences.get("dossier_youtube")
        if not dossier_choisi:
            # Fallback vers dossier Vidéos si vide
            dossier_choisi = os.path.join(os.path.expanduser("~"), "Videos")

        self.youtube_controller.start_download(
            self.state.youtube_url,
            self.window.progress_bar,
            dossier_choisi 
        )


    def _download00_youtube_video(self):
        """Téléchargement YouTube."""
        if not self.youtube_controller.is_internet_available():
            self._on_error("Connexion Internet indisponible pour le téléchargement YouTube")
            return

        self.youtube_controller.start_download(
            self.state.youtube_url,
            self.window.progress_bar
        )

    def _on_audio_converted(self, audio_path):
        """Audio prêt, message et transcription."""
        if not self._is_running:
            return

        logging.info(f"[TasksManager][STEP] Audio prêt. Lancement transcription.")
        self.window.progress_bar.setValue(70)

        QMessageBox.information(self.window, "Conversion audio", "✅ Conversion audio terminée.\nLa transcription commence...")

        video = Path(self.state.video_path)
        ass = str(video.parent / f"{video.stem}.ass")
        self.state.ass_path = ass

        self.transcription_controller.start_transcription(
            audio_path, ass, self.window.progress_bar
        )

    def _on00_incrustation_finished(self, mkv_path, mp4_path):
        """Gère la réussite de l'incrustation."""
        if not self._is_running:
            return

        msg = (f"✅ Workflow terminé avec succès !\n\n"
               f"Fichiers générés :\n"
               f"- {os.path.basename(mkv_path)}\n"
               f"- {os.path.basename(mp4_path)}")

        QMessageBox.information(self.window, "Succès", msg)
        self._finish()


    def _on_incrustation_finished(self, mkv_path, mp4_path):
        """Gère la réussite de l'incrustation et ouvre le dossier."""
        if not self._is_running:
            return

        # 1. Préparation du message avec chemins absolus
        msg = (f"✅ Workflow terminé avec succès !\n\n"
               f"Fichiers générés :\n"
               f"- {os.path.abspath(mkv_path)}\n"
               f"- {os.path.abspath(mp4_path)}")

        # 2. Affichage de l'information
        QMessageBox.information(self.window, "Succès", msg)

        # 3. Ouverture du dossier contenant les vidéos (le dossier parent de mp4_path)
        import subprocess
        output_dir = os.path.dirname(os.path.abspath(mp4_path))
        if os.path.exists(output_dir):
            subprocess.Popen(f'explorer "{output_dir}"')

        self._finish()


    def _on_model_ready(self):
        """Appelé quand le modèle est chargé via signal."""
        if not self._is_running:
            return

        logging.info("[TasksManager][SIGNAL] Modèle prêt.")
        self.window.progress_bar.setValue(20)

        if self.state.youtube_url:
            QMessageBox.information(self.window, "Modèle chargé", "✅ Modèle Whisper chargé avec succès.\nTéléchargement de la vidéo YouTube...")
            self._download_youtube_video()
        else:
            QMessageBox.information(self.window, "Modèle chargé", "✅ Modèle Whisper chargé avec succès.\nLa conversion audio commence...")
            self._convert_video_to_audio()

    def _on_transcription_success(self, ass_path):
        """Transcription finie, message et incrustation."""
        if not self._is_running:
            return

        logging.info(f"[TasksManager][STEP] Transcription réussie.")
        self.window.progress_bar.setValue(85)

        QMessageBox.information(self.window, "Transcription", "✅ Transcription terminée.\nL'incrustation commence...")

        try:
            self._original_output_base = self.incrustation_controller.output_path_base
            self.incrustation_controller.output_path_base = self.state.output_base
            self.incrustation_controller.run_incrustation(
                self.state.video_path, ass_path
            )
        except Exception as e:
            self._on_error(str(e))

    def _on_youtube_download_error(self, error_message, title=""):
        """Appelé quand le téléchargement YouTube échoue."""
        if title:
            logging.info(f"[TasksManager] Échec détecté pour '{title}'. Nettoyage des fichiers temporaires...")
            self._nettoyer_fichiers_part(title)
        self._on_error(f"Erreur YouTube ({title}): {error_message}")

    def _on_youtube_download_success(self, video_path, title):
        """Réussite téléchargement, message et passage audio."""
        if not self._is_running:
            return

        logging.info(f"[TasksManager][STEP] Téléchargement YouTube réussi: {title}")
        is_ok, msg = self.validator.verify_media(video_path)
        if not is_ok:
            self._on_error(f"Le fichier téléchargé est illisible : {msg}")
            return

        self.window.progress_bar.setValue(40)

        QMessageBox.information(self.window, "YouTube", f"✅ Téléchargement terminé: {title}\n\nLa conversion audio commence...")

        self.state.set_video(video_path)
        self.state.youtube_url = None
        self.window.label_video.setText(f"Vidéo: {title[:40]}...")

        self._convert_video_to_audio()

    # =========================================================================
    # FIN ET ERREURS
    # =========================================================================

    def _finish(self):
        """Reset complet."""
        logging.info("[TasksManager] Fin du workflow.")
        self._is_running = False
        self.window.btn_process.setEnabled(True)
        self.window.progress_bar.setVisible(False)
        self.window.progress_bar.setValue(0)
        self.window.setCursor(Qt.CursorShape.ArrowCursor)
        self.workflowFinished.emit()

    def _on_error(self, message):
        """Gère les erreurs avec QMessageBox."""
        logging.error(f"[TasksManager][ERROR] {message}")
        if hasattr(self, '_original_output_base'):
            self.incrustation_controller.output_path_base = self._original_output_base

        QMessageBox.critical(self.window, "Erreur", f"❌ {message}")
        self._finish()

    def cleanup_resources(self):
        if self.transcription_controller._whisper_model:
            del self.transcription_controller._whisper_model
            self.transcription_controller._whisper_model = None
        import gc
        gc.collect()