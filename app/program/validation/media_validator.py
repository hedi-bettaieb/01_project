#media_validator.py 
from pathlib import Path
import subprocess
import traceback
import os


class MediaValidator:
    """
    Validation indépendante des fichiers multimédia.
    Thread-safe (aucune dépendance Qt).
    """

    AUDIO_EXT = {".mp3", ".wav", ".aac", ".flac", ".ogg"}
    VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

    def __init__(self, path_manager):
        self.paths = path_manager
        self.ffmpeg_exe = str(self.paths.get_path("bin/ffmpeg.exe"))

    # ==================================================
    # ✅ SEULE MÉTHODE PUBLIQUE
    # ==================================================
    def verify_media(self, media_path: str) -> tuple[bool, str]:
        try:
            path = self.paths.get_path(media_path)

            if not path.exists():
                return False, f"Fichier introuvable : {path}"

            if not path.is_file():
                return False, f"Chemin invalide : {path}"

            ext = path.suffix.lower()

            # 📝 ASS → PAS FFmpeg
            if ext == ".ass":
                return self._verify_ass(path)

            # 🎧 / 🎞️ AUDIO + VIDÉO → FFmpeg
            if ext in self.AUDIO_EXT | self.VIDEO_EXT:
                ok, msg = self._verify_with_ffmpeg(path)
                if not ok:
                    return False, msg
                return True, "Audio valide" if ext in self.AUDIO_EXT else "Vidéo valide"

            return False, f"Type de fichier non supporté : {ext}"

        except Exception as e:
            return False, self._format_exception(e)

    # ==================================================
    # 🔒 MÉTHODES INTERNES
    # ==================================================
    def _verify_with_ffmpeg(self, path: Path) -> tuple[bool, str]:
        if not Path(self.ffmpeg_exe).exists():
            return False, f"FFmpeg introuvable : {self.ffmpeg_exe}"

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        cmd = [
            self.ffmpeg_exe,
            "-v", "error",
            "-i", str(path),
            "-t", "0.1",
            "-f", "null", "-"
        ]

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags
        )

        if res.returncode != 0:
            if "Invalid data found" in res.stderr:
                return False, "Fichier multimédia invalide ou corrompu"
            return False, f"Erreur FFmpeg : {res.stderr.strip()}"

        return True, "OK"

    def _verify_ass(self, path: Path) -> tuple[bool, str]:
        try:
            with path.open("r", encoding="utf-8-sig", errors="strict") as f:
                content = f.read()
        except UnicodeDecodeError:
            return False, "Encodage ASS invalide (UTF-8 requis)"

        if "[Script Info]" not in content:
            return False, "ASS invalide : section [Script Info] absente"

        if "[Events]" not in content:
            return False, "ASS invalide : section [Events] absente"

        return True, "ASS valide"

    @staticmethod
    def _format_exception(e: Exception) -> str:
        tb = traceback.format_exc()
        return f"Exception inattendue : {e}\n\nTraceback:\n{tb}"
