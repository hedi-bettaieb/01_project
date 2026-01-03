# program/workers/youtube_worker.py
import os
import threading
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
from program.audio.audio_converter import ConvertisseurAudio
from program.utils.internet_monitor import InternetMonitor
from program.utils.paths import PathManager

class YoutubeDownloadWorker(QThread):
    """
    Thread dédié au téléchargement de vidéos YouTube au format MP4.
    Émet des signaux pour la progression, les mises à jour de statut, la réussite ou les erreurs.
    """
    progress = pyqtSignal(int)
    downloadStarting = pyqtSignal()
    statusUpdate = pyqtSignal(str)
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str, str)
    stopRequested = pyqtSignal(str)

    
    def __init__(self, url, monitor: InternetMonitor, output_dir=None, parent=None):
        """
        Initialise le worker avec l'URL, le moniteur Internet et le dossier de destination choisi.

        Args:
            url (str): URL de la vidéo YouTube à télécharger.
            monitor (InternetMonitor): Instance pour surveiller la connexion Internet.
            output_dir (str, optional): Chemin complet du dossier choisi par l'utilisateur.
            parent (QObject, optional): Parent Qt. Par défaut None.
        """
        super().__init__(parent)
        self.url = url
        self.paths = PathManager()
        # On utilise directement le chemin fourni par l'utilisateur
        self.dossier = output_dir if output_dir else os.path.join(os.path.expanduser("~"), "Videos")
        
        self._video_path = ""
        self._titre = "video_youtube"
        self._last_percent = 0
        
        # Création du dossier (Garanti autorisé car choisi par l'utilisateur)
        os.makedirs(self.dossier, exist_ok=True)

        self.monitor = monitor
        self.stop_monitor_event = threading.Event()
        self.monitor_thread = None
        self.is_download_aborted = False


    def _translate_youtube_error(self, exception_obj, phase="Analyse/Téléchargement"):
        """
        Traduit les exceptions techniques de yt-dlp en messages utilisateur clairs.

        Args:
            exception_obj (Exception): Exception levée par yt-dlp.
            phase (str, optional): Phase du processus en cours. Par défaut "Analyse/Téléchargement".

        Returns:
            str: Message d'erreur adapté pour l'utilisateur.
        """
        error_message = str(exception_obj)
        if "getaddrinfo failed" in error_message or "Failed to resolve" in error_message:
            return "❌ Échec de la connexion pendant le processus : Vérifiez votre connexion Internet."
        if ("Private video" in error_message or
            "Video unavailable" in error_message or
            "Did not find any video" in error_message or
            "ERROR: Invalid URL" in error_message or
            "Incomplete YouTube ID" in error_message):
            return "❌ Vidéo non disponible : Lien invalide, vidéo privée ou supprimée."
        if "No video formats found" in error_message:
            return "❌ Aucun format vidéo compatible trouvé pour cette URL."
        return f"❌ Erreur lors de l'étape {phase} : {error_message}"

    def _hook_progress(self, d):
        """
        Callback pour yt-dlp : met à jour et émet la progression du téléchargement.

        Args:
            d (dict): Dictionnaire de progression fourni par yt-dlp.
        """
        if d['status'] == 'downloading':
            percent = 0
            if 'total_bytes' in d and 'downloaded_bytes' in d:
                percent = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
            elif '_percent_str' in d:
                try:
                    percent = int(float(d['_percent_str'].replace('%', '').strip()))
                except:
                    pass
            if percent > self._last_percent:
                self._last_percent = percent
                self.progress.emit(percent)
        elif d['status'] == 'finished':
            self.progress.emit(100)

    def _background_monitor_run(self):
        """
        Fonction exécutée en arrière-plan pour surveiller la connexion Internet.
        Émet un signal d'arrêt en cas de perte de connexion durable.
        """
        if not self.monitor.monitor_internet_connection(self.stop_monitor_event, check_interval=5, max_failures=3):
            self.is_download_aborted = True
            self.statusUpdate.emit("⚠ PERTE DE CONNEXION DURABLE DÉTECTÉE. Arrêt du téléchargement...")
            self.error.emit("Perte de connexion Internet durable. Le téléchargement ne peut pas continuer.", self._titre)
            self.stopRequested.emit(self._titre)

    def _stop_monitor(self):
        """Arrête proprement le thread de surveillance."""
        self.stop_monitor_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
            
            

    def run(self):
        """
        Exécute le téléchargement de la vidéo YouTube.
        """
        self._last_percent = 0
        self._stop_monitor()
        

        ffmpeg_local = self.paths.get_path("bin/ffmpeg.exe")
        print(f"DEBUG: FFmpeg utilisé -> {ffmpeg_local}")

        
        try:
            self.url = ConvertisseurAudio.nettoyer_url(self.url)
        except NameError:
            pass

        self.monitor_thread = threading.Thread(target=self._background_monitor_run, daemon=True)
        self.monitor_thread.start()

        try:
            ydl_opts_info = {'quiet': True, 'nocheckcertificate': True}
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(self.url, download=False)
                titre_brut = info.get('title', self._titre)
                self._titre = ConvertisseurAudio.simplifier_titre(titre_brut)
                # self.dossier est maintenant le chemin utilisateur (ex: C:/Users/Docs)
                self._video_path = str(os.path.join(self.dossier, f"{self._titre}.mp4"))                
                
        except Exception as e:
            self._stop_monitor()
            self.error.emit(self._translate_youtube_error(e, "Analyse"), self._titre)
            return

        if os.path.exists(self._video_path):
            try:
                os.remove(self._video_path)
            except Exception as e:
                self._stop_monitor()
                self.error.emit(f"❌ Impossible de supprimer l'ancienne vidéo : {e}", self._titre)
                return

        options = {
            #Réutilisation de ffmpeg_local
            'ffmpeg_location': str(ffmpeg_local),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': self._video_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'progress_hooks': [self._hook_progress],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'fr-FR,fr;q=0.9',
                'Referer': 'https://www.youtube.com/'
            },
            'geo_bypass': True,
            'nocheckcertificate': True,
            'retries': 3
        }

        try:
            self.statusUpdate.emit(f"Vidéo trouvée : '{self._titre}'. Début du téléchargement...")
            self.downloadStarting.emit()
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([self.url])

            self._stop_monitor()




            if not os.path.exists(self._video_path) or os.path.getsize(self._video_path) < 1024:
                if not self.is_download_aborted:
                    raise Exception("Fichier téléchargé vide ou incomplet.")
            else:
                self.finished.emit(self._video_path, f"✅ Téléchargement terminé : {self._titre}")

        except Exception as e:
            self._stop_monitor()
            if not self.is_download_aborted:
                self.error.emit(self._translate_youtube_error(e, "Téléchargement"), self._titre)
