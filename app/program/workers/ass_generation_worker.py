import logging
# program/workers/ass_generation_worker.py
import os
from PyQt6.QtCore import QThread, pyqtSignal

from program.subtitles.ass_generator import GenerateurASS
from program.preferences.user_preferences import UserPreferences
from program.audio.silence_detector import detect_silence

class ASSGenerationWorker(QThread):
    """
    Thread dédié à la génération de sous-titres au format ASS à partir d'un fichier audio.
    Émet des signaux pour indiquer la réussite ou les erreurs rencontrées.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path, ass_path, user_preferences: UserPreferences, modele=None):
        """
        Initialise le worker avec les chemins et préférences nécessaires.

        Args:
            audio_path (str): Chemin vers le fichier audio source.
            ass_path (str): Chemin où enregistrer le fichier ASS généré.
            user_preferences (UserPreferences): Préférences utilisateur pour la génération.
            modele (optional): Modèle de transcription à utiliser. Defaults to None.
        """
        super().__init__()
        self.audio_path = audio_path
        self.ass_path = ass_path
        self.modele = modele
        self.user_preferences = user_preferences

    def _translate_whisper_error(self, e: Exception) -> str:
        """
        Traduit les exceptions levées lors de la transcription en messages utilisateur clairs.

        Args:
            e (Exception): Exception levée pendant la transcription.

        Returns:
            str: Message d'erreur adapté pour l'utilisateur final.
        """
        error_message = str(e)
        if "TRANSCRIPTION_FAILED_QUICK_SILENCE_CHECK" in error_message:
            return "❌ La piste audio est silencieuse ou vide."
        if "TRANSCRIPTION_FAILED_NO_SPEECH" in error_message:
            return "❌ Aucun discours significatif détecté dans l'audio."
        if isinstance(e, FileNotFoundError):
            return f"❌ Fichier audio introuvable : {self.audio_path}"
        if "cuda" in error_message.lower():
            return "❌ Erreur GPU : Configuration CUDA ou carte graphique non compatible."
        return f"Erreur survenue lors de la transcription : {error_message[:150]}"

    def run(self):
        """
        Méthode principale exécutée dans le thread.
        Génère les sous-titres ASS à partir du fichier audio et émet un signal de résultat.
        """
        try:
            if self.modele is None:
                raise ValueError("Aucun modèle fourni.")
            if not os.path.exists(self.audio_path):
                raise FileNotFoundError(f"Fichier audio introuvable : {self.audio_path}")

            detect_silence(self.audio_path)
            assgen = GenerateurASS(self.modele, self.user_preferences)
            assgen.generer(self.audio_path, self.ass_path)
            self.finished.emit("✅ Transcription terminée.")
        except Exception as e:
            self.error.emit(self._translate_whisper_error(e))
