# program/worker/audio_worker.py
from PyQt6.QtCore import QThread, pyqtSignal
from program.audio.audio_converter import ConvertisseurAudio


class AudioConversionWorker(QThread):
    """
    Thread dédié à la conversion d'un fichier vidéo en audio.
    Émet des signaux pour indiquer la réussite ou les erreurs rencontrées.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, audio_path, format_audio="mp3"):
        """
        Initialise le worker avec les chemins et le format de sortie.

        Args:
            video_path (str): Chemin vers le fichier vidéo source.
            audio_path (str): Chemin où enregistrer le fichier audio généré.
            format_audio (str, optional): Format audio de sortie. Par défaut "mp3".
        """
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.format_audio = format_audio

    def _translate_conversion_error(self, exception_obj):
        """
        Traduit les exceptions levées lors de la conversion en messages utilisateur clairs.

        Args:
            exception_obj (Exception): Exception levée pendant la conversion.

        Returns:
            str: Message d'erreur adapté pour l'utilisateur final.
        """
        error_message = str(exception_obj).lower()
        if "no such file or directory" in error_message:
            return "❌ Fichier vidéo source introuvable."
        if ("conversion audio via moviepy/ffmpeg" in error_message or
            "ffmpeg" in error_message or
            "ioerror" in error_message or
            "memoryerror" in error_message):
            return "❌ Erreur critique de conversion audio : Fichier corrompu ou codec non supporté."
        return f"❌ Erreur inattendue lors de la conversion audio : {error_message[:150]}..."

    def run(self):
        """
        Méthode principale exécutée dans le thread.
        Convertit le fichier vidéo en audio et émet un signal de résultat.
        """
        try:
            ConvertisseurAudio.convertir(self.video_path, self.audio_path, self.format_audio)
            self.finished.emit("✅ Conversion audio terminée.")
        except Exception as e:
            self.error.emit(self._translate_conversion_error(e))
