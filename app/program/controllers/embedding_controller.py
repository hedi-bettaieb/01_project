# incrusteur_controller.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox
from program.workers.video_subtitle_worker import VideoSubtitlesWorker
from program.workers.progress_worker import ProgressThread
import shutil
import os
from pathlib import Path


class IncrustationController(QObject):
    """
    Contrôleur pour l'orchestration du processus d'incrustation et 
    la validation métier des fichiers ASS.
    """
    incrustationSuccess = pyqtSignal(str, str)
    incrustationFailed = pyqtSignal(str)

    def __init__(self, parent_window, output_path_base, incrusteur,
                 dialogs_manager, protection_detector, 
                 ass_font_manipulator, font_manager, user_preferences):
        super().__init__()
        self.window = parent_window
        self.output_path_base = output_path_base
        self.incrusteur = incrusteur
        self.dialogs_manager = dialogs_manager
        self.protection_detector = protection_detector
        self.ass_font_manipulator = ass_font_manipulator
        self.font_manager = font_manager
        self.user_preferences = user_preferences
        self.incrustation_worker = None
        self.progress_thread = None

    def handle_ass_selection_and_validation(self, parent_widget):
        file_path = self.dialogs_manager.select_ass_file(parent_widget)
        if not file_path:
            return None
        protection_status = self.protection_detector.check(file_path)
        if "🔒" in protection_status:
            msg = f"{protection_status}\n\nVeuillez choisir un autre fichier modifiable."
            self.dialogs_manager.notify(parent_widget, "Accès Refusé", msg, icon="critical")
            return None
        detected_font = self.ass_font_manipulator.detect_font_in_ass(file_path)
        detected_result = self.ass_font_manipulator.detect_language_from_ass(file_path)
        lang_code = detected_result[1] if detected_result else 'und'
        if detected_font:
            folder_name = "arabic_fonts" if lang_code.startswith('ar') else "latin_fonts"
            if self.font_manager.is_font_available(detected_font, folder_name):
                self.dialogs_manager.notify_font_available(parent_widget, detected_font)
                return file_path
            else:
                return self.font_manager.handle_missing_font(detected_font, file_path, parent_widget)
        return file_path

    def check_disk_space(self, video_path: str):
        try:
            path = Path(video_path)
            drive = path.anchor
            size = os.path.getsize(video_path)
            req_size = size * 4
            usage = shutil.disk_usage(drive)
            print(f"[Disk] Drive: {drive} | Required: {req_size/(1024**3):.2f} GB | Available: {usage.free/(1024**3):.2f} GB")
            if usage.free < req_size:
                msg = f"Disk {drive} nearly full."
                QMessageBox.critical(None, "Disk Space", msg)
                return False, usage.free, req_size
            return True, usage.free, req_size
        except Exception as e:
            print(f"[Disk] Error: {e}")
            return True, 0, 0

    def run_incrustation(self, video_path, ass_path):
        succes, libre, requis = self.check_disk_space(video_path)
        if not succes:
            return
        self.user_preferences.valider_configuration()
        self.window.btn_process.setEnabled(False)
        self.window.progress_bar.show()
        self.window.progress_bar.setValue(0)
        self.progress_thread = ProgressThread()
        self.progress_thread.progress.connect(self.window.progress_bar.setValue)
        self.progress_thread.start()
        self._cleanup_worker()
        self.incrustation_worker = VideoSubtitlesWorker(video_path, ass_path, self.output_path_base, self.incrusteur)
        self.incrustation_worker.finished.connect(self._on_incrustation_finished)
        self.incrustation_worker.error.connect(self._on_incrustation_error)
        self.incrustation_worker.start()

    def _stop_progress_thread(self):
        if self.progress_thread:
            self.progress_thread.stop()
            self.progress_thread.quit()
            self.progress_thread.wait(500)
            self.progress_thread = None

    def _cleanup_worker(self):
        if self.incrustation_worker:
            try:
                self.incrustation_worker.quit()
                self.incrustation_worker.wait(500)
                self.incrustation_worker = None
            except:
                pass

    def _on_incrustation_finished(self, mkv_path, mp4_path):
        self._stop_progress_thread()
        self.incrustationSuccess.emit(mkv_path, mp4_path)
        self._cleanup_worker()

    def _on_incrustation_error(self, error_message):
        self._stop_progress_thread()
        self.incrustationFailed.emit(error_message)
        self._cleanup_worker()


