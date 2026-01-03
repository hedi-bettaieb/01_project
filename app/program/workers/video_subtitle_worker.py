# program/workers/video_subtitle_worker.py
from PyQt6.QtCore import QThread, pyqtSignal
from program.video.video_embedder import IncrusteurVideo

class VideoSubtitlesWorker(QThread):
    """
    Thread dédié à l'incrustation de sous-titres dans une vidéo.
    Génère deux formats de sortie : MKV (sous-titres soft) et MP4 (sous-titres hardcoded).
    Émet des signaux pour indiquer la réussite ou les erreurs.
    """
    finished = pyqtSignal(str, str)  # Émet (chemin_mkv, chemin_mp4)
    error = pyqtSignal(str)          # Émet le message d'erreur

    def __init__(self, video_path, ass_path, output_path_base, incrusteur):
        """
        Initialise le worker avec les chemins et l'incrusteur de sous-titres.

        Args:
            video_path (str): Chemin vers la vidéo source.
            ass_path (str): Chemin vers le fichier de sous-titres ASS.
            output_path_base (str): Chemin de base pour les fichiers de sortie.
            incrusteur (IncrusteurVideo): Instance de l'incrusteur de sous-titres.
        """
        super().__init__()
        self.video_path = video_path
        self.ass_path = ass_path
        self.output_path_base = output_path_base
        self.incrusteur = incrusteur

    def run(self):
        """
        Incruste les sous-titres dans la vidéo et génère les fichiers MKV et MP4.
        Émet un signal de réussite ou d'erreur selon le résultat.
        """
        try:
            result = self.incrusteur.incruster(
                self.video_path,
                self.ass_path,
                self.output_path_base
            )

            if isinstance(result, tuple) and len(result) == 2:
                success, message = result
            else:
                success = result
                message = "Génération terminée" if success else "Échec de l'incrustation"

            if success:
                mkv_path = self.output_path_base + ".mkv"
                mp4_path = self.output_path_base + ".mp4"
                self.finished.emit(mkv_path, mp4_path)
            else:
                self.error.emit(f"❌ Échec de l'incrustation: {message}")

        except Exception as e:
            self.error.emit(f"❌ Erreur critique lors de l'incrustation : {e}")
