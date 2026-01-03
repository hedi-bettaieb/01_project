#program/video/incrusteur_video.py
from pathlib import Path
import traceback
import json
import subprocess
import shutil
import sys
#from program.preferences.user_preferences import UserPreferences
from program.utils.paths import PathManager
from program.fonts.ass_font_manipulator import AssFontManipulator 

class IncrusteurVideo:
    """
    Classe responsable de l'incrustation de sous-titres .ass dans une vidéo .mp4 à l'aide de ffmpeg.
    Les paramètres (police, couleur, etc.) sont récupérés depuis les préférences utilisateur.
    """
    def __init__(self, dossier_projet, user_preferences): 
        self.user_preferences = user_preferences 
        self.paths = PathManager()
        self.dossier_projet = Path(dossier_projet).resolve()
        self.chemin_ffmpeg = str(self.paths.get_path("bin/ffmpeg.exe"))
        
        
    def _preparer_chemin_filtre(self, chemin: Path) -> str:
        """
        Prépare un chemin de fichier pour être utilisé dans un filtre FFmpeg (vf ass=...).
        Echappe les caractères spéciaux comme l'apostrophe et les deux-points.
        """
        # 1. On utilise des slashs / même sur Windows
        p = str(chemin.resolve()).replace('\\', '/')
        # 2. On échappe les deux-points (ex: C\:/)
        p = p.replace(':', '\\:')
        # 3. On échappe l'apostrophe (très complexe pour libass)
        p = p.replace("'", "'\\\\\\''")
        return p

    def incruster(self, video_entree: str, ass_path: str, sortie: str) -> bool:
        try:
            video_path = Path(video_entree)
            ass_file = Path(ass_path)
            output_path_mkv = Path(sortie).with_suffix('.mkv')  
            output_path_mp4 = Path(sortie).with_suffix('.mp4')


# Vérifications
            if not video_path.exists():
                print(f"❌ Fichier vidéo introuvable: {video_path}")
                return False
                
            if not ass_file.exists():
                print(f"❌ Fichier ASS introuvable: {ass_file}")
                return False

            

            # FFmpeg path
            ffmpeg_path = Path(self.paths.get_path("bin/ffmpeg.exe"))
            if not ffmpeg_path.exists():
                print(f"❌ FFmpeg introuvable: {ffmpeg_path}")
                return False



            
            working_dir = video_path.parent
            
            # Détection langue , obtenir (Nom, ISO-1, ISO-2)
            manipulator = AssFontManipulator()
            resultat_langue = manipulator.detect_language_from_ass(str(ass_file))
            if resultat_langue:
                _, _, langue_code_ffmpeg = resultat_langue # Récupère le code ISO 639-2 (ex: 'ara')
                print(f"[Incrusteur] Code ISO-2 ASS détecté et utilisé : {langue_code_ffmpeg}")
            else:
                langue_code_ffmpeg = "und" # Fallback si la lecture échoue
                print(f"[Incrusteur] ⚠ Langue ASS non détectée, utilisation de : {langue_code_ffmpeg}")
            

            #manipulator = AssFontManipulator()
            #resultat_langue = manipulator.detect_language_from_ass(str(ass_file))
            #langue_code_ffmpeg = resultat_langue[2] if resultat_langue else "und"

            # =========================================================================
            # 1. GÉNÉRATION DU MKV (Toujours OK car c'est du multiplexage)
            # =========================================================================
            commande_mkv = [
                str(ffmpeg_path), "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_path),
                "-i", str(ass_file),
                "-c:v", "copy", "-c:a", "copy", "-c:s", "ass",
                "-metadata:s:s:0", f"language={langue_code_ffmpeg}",
                "-disposition:s:0", "default",
                str(output_path_mkv)
            ]
            subprocess.run(commande_mkv, cwd=working_dir, check=True)

            # =========================================================================
            # 2. MP4- Préparation du chemin pour le filtre
            # =========================================================================
            # On prépare le chemin ASS pour qu'il soit blindé contre les apostrophes
            ass_path_securise = self._preparer_chemin_filtre(ass_file)
            
            commande_mp4 = [
                str(ffmpeg_path), "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_path),
                # Utilisation du chemin sécurisé avec des guillemets simples internes
                "-vf", f"ass='{ass_path_securise}'", 
                "-c:a", "copy", "-c:v", "libx264",
                "-preset", "fast", "-crf", "23",
                str(output_path_mp4)
            ]
            
            subprocess.run(commande_mp4, cwd=working_dir, check=True)
            
            print("🎉 Génération terminée avec succès !")
            
            print(f"✅ MP4 généré: {output_path_mp4}")
            
            # RÉSUMÉ FINAL
            print("🎉 Génération terminée avec succès !")
            print(f"📁 MKV (sous-titres désactivables) : {output_path_mkv}")
            print(f"📁 MP4 (sous-titres incrustés)     : {output_path_mp4}")
            print(f"Langue : {langue_code_ffmpeg}")
            
            return True, "Génération terminée avec succès." 
                
        except subprocess.CalledProcessError as e:
            return False, f"Erreur FFmpeg: {e.stderr}" # 👈 Échec FFmpeg
        