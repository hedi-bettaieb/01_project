import logging
# outils/convertisseur_audio.py
import os
import re
import moviepy.editor as mp
import yt_dlp
from program.utils.paths import PathManager


class ConvertisseurAudio:
    """
    Convertit une vidéo locale ou YouTube en fichier audio (.mp3 ou .wav)
    """

    @staticmethod
    def nettoyer_url(url: str) -> str:
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url.strip()

    @staticmethod
    def nettoyer_titre(titre: str) -> str:
        """
        Supprime les caractères spéciaux et remplace les espaces par "_".
        """
        return re.sub(r'[\\/*?:"<>|]', "", titre).strip().replace(" ", "_")

    @staticmethod
    def simplifier_titre(titre: str, nb_mots=3, max_caracteres=30) -> str:
        def extract_first_words(text, num_words=3, separator='_'):
            pattern = r'[\s_.\-/,;:!?()[\]{}"|+=*&%$#@<>~`^\\]+|[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+'
            parts = [part for part in re.split(pattern, text) if part.strip()]
            return separator.join(parts[:num_words])

        titre = re.sub(r'[\\/*?:"<>|]', "", titre)
        resultat = extract_first_words(titre, nb_mots, '_')

        if resultat and len(resultat.split('_')) >= nb_mots:
            return resultat

        titre = re.sub(r"[\s\u00A0\u200B\u200C\u200D\u2060]+", " ", titre)
        mots = [m for m in titre.strip().split(" ") if m]

        if len(mots) >= nb_mots:
            return "_".join(mots[:nb_mots])
        elif mots:
            return mots[0][:max_caracteres]

        return titre[:max_caracteres]

    @staticmethod
    def supprimer_si_existe(chemin: str, label: str = "fichier"):
        if os.path.exists(chemin):
            try:
                os.remove(chemin)
                logging.info(f"🧹 Ancien {label} supprimé : {chemin}")
            except Exception as e:
                logging.info(f"⚠️ Impossible de supprimer l’ancien {label} :", e)
                return False
        return True

    @staticmethod
    def convertir(video_path: str, audio_path: str, format_audio="mp3") -> bool:
        if not os.path.exists(video_path):
            # ⚠️ Cette erreur devrait être gérée avant d'appeler convertir, 
            # mais la vérification ici est bonne.
            raise FileNotFoundError(f"Fichier vidéo introuvable : {video_path}") 

        # Supprimer l'ancien fichier audio (pas de changement ici)
        if not ConvertisseurAudio.supprimer_si_existe(audio_path, "audio"):
            # L'échec de la suppression est une erreur critique
            raise PermissionError(f"Impossible de supprimer l'ancien fichier audio: {audio_path}")

        codec = None
        if format_audio == "mp3":
            codec = "libmp3lame"
        elif format_audio == "wav":
            codec = "pcm_s16le"

        try:
            logging.info("🎵 Extraction de l’audio depuis :", video_path)
            clip = mp.VideoFileClip(video_path)
            # L'exception se produit souvent ici (lecture) ou sur write_audiofile (écriture/codec)
            clip.audio.write_audiofile(audio_path, codec=codec, logger=None) # logger=None pour moins de spam console
            logging.info(f"✅ Audio extrait vers : {audio_path}")
            return True
        except Exception as e:
            # 🌟 NE PAS MASQUER L'EXCEPTION ! La relancer pour le Worker.
            raise RuntimeError(f"Erreur de conversion audio via MoviePy/FFmpeg: {e}") 