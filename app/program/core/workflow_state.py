import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class WorkflowState:
    """
    État partagé pour tous les workflows.
    Centralise les données communes entre les différentes étapes et gère la logique des chemins.
    """
    # Données d'entrée
    video_path: Optional[str] = None
    youtube_url: Optional[str] = None
    ass_path: Optional[str] = None
    
    # Données intermédiaires
    audio_path: Optional[str] = None
    downloaded_video_path: Optional[str] = None
    
    # Données de sortie
    output_base: Optional[str] = None
    
    # Métadonnées
    language: Optional[str] = None
    
    def reset(self):
        """Réinitialise l'état pour un nouveau workflow de manière propre."""
        self.video_path = None
        self.youtube_url = None
        self.ass_path = None
        self.audio_path = None
        self.downloaded_video_path = None
        self.output_base = None
        self.language = None

    def set_video(self, video_path: str):
        """
        Définit le chemin de la vidéo source.
        Calcule automatiquement le préfixe pour les fichiers de sortie.
        """
        if not video_path:
            return
            
        self.video_path = str(Path(video_path).absolute())
        video = Path(self.video_path)
        
        # On définit la base de sortie dans le même dossier que la vidéo
        self.output_base = str(video.parent / f"{video.stem}_subtitled")

    def get_output_mkv(self) -> Optional[str]:
        """Retourne le chemin complet du fichier MKV (sous-titres soft)."""
        if not self.output_base:
            return None
        return f"{self.output_base}.mkv"

    def get_output_mp4(self) -> Optional[str]:
        """Retourne le chemin complet du fichier MP4 (sous-titres hard)."""
        if not self.output_base:
            return None
        return f"{self.output_base}.mp4"

    def is_youtube(self) -> bool:
        """Vérifie si le processus en cours provient d'une URL YouTube."""
        return self.youtube_url is not None

    def has_valid_video(self) -> bool:
        """Vérifie si le fichier vidéo source existe réellement sur le disque."""
        if not self.video_path:
            return False
        return Path(self.video_path).exists()

    def get_ass_path(self) -> Optional[str]:
        """Retourne le chemin du fichier ASS, ou le génère par défaut si manquant."""
        if self.ass_path:
            return self.ass_path
        if self.video_path:
            video = Path(self.video_path)
            return str(video.parent / f"{video.stem}.ass")
        return None

    def get_audio_path(self) -> Optional[str]:
        """Retourne le chemin du fichier audio extrait (MP3)."""
        if self.audio_path:
            return self.audio_path
        if self.video_path:
            video = Path(self.video_path)
            return str(video.parent / f"{video.stem}.mp3")
        return None
