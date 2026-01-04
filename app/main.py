# 2h : https://www.youtube.com/watch?v=d1W5gK9sX6E
#test  : https://www.youtube.com/watch?v=brsQ2W5ptc4
#espagnol : https://www.youtube.com/watch?v=jQY0j3lWLOM
# main_window.py
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QProgressBar, QComboBox, QLineEdit, QMessageBox
from PyQt6.QtCore import Qt
from program.dependencies.dependency_factory import DependencyFactory
from program.core.tasks_manager import TasksManager
from program.utils.paths import PathManager
from program.ui.customized_button import CustomizedButton


# Initialisation du gestionnaire de chemins
pm = PathManager()

# Configuration du système de logs
log_file = pm.get_logs_dir() / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()  # Affiche aussi dans la console
    ]
)

logging.info("--- Démarrage de l'application ---")



class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application pour l'incrustation de sous-titres vidéo.
    Gère l'interface utilisateur et les workflows disponibles.
    """
    def __init__(self):
        """
        Initialise la fenêtre principale, ses widgets et ses connexions.
        """
        super().__init__()
        self.setWindowTitle("Easy Subtitle Creator V1.0")
        self.setGeometry(100, 100, 400, 250)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.cmb_workflow = QComboBox(central_widget)
        self.cmb_workflow.addItem("1. Vidéo Locale (Auto Transcription)")
        self.cmb_workflow.addItem("2. Vidéo Locale + ASS Manuel")
        self.cmb_workflow.addItem("3. Vidéo YouTube (Auto Transcription)")
        layout.addWidget(self.cmb_workflow)

        self.input_youtube_url = QLineEdit(central_widget)
        self.input_youtube_url.setPlaceholderText("Entrez l'URL YouTube ici...")
        self.input_youtube_url.hide()
        layout.addWidget(self.input_youtube_url)

        self.label_video = QLabel("Vidéo: Non sélectionnée")
        self.label_ass = QLabel("ASS: Non sélectionné (Validation par TasksManager)")
        layout.addWidget(self.label_video)
        layout.addWidget(self.label_ass)

        self.btn_process = CustomizedButton("Lancer le Processus Complet")
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.btn_process)
        layout.addWidget(self.progress_bar)

        factory = DependencyFactory(self)
        self.tasks_manager: TasksManager = factory.build_tasks_manager()

        self.tasks_manager.workflowStarted.connect(lambda: self.set_ui_enabled(False))
        self.tasks_manager.workflowFinished.connect(lambda: self.set_ui_enabled(True))
        self.cmb_workflow.currentIndexChanged.connect(self._update_button_label)
        self.cmb_workflow.currentIndexChanged.connect(self.toggle_youtube_input)
        self.btn_process.clicked.connect(self.launch_process)

        self.toggle_youtube_input(self.cmb_workflow.currentIndex())
        self._update_button_label(self.cmb_workflow.currentIndex())

    def _update_button_label(self, index: int):
        """
        Met à jour le texte du bouton selon le workflow sélectionné.

        Args:
            index (int): Index du workflow sélectionné.
        """
        if index == 0:
            self.btn_process.setText("Lancer : Vidéo Locale (Auto)")
        elif index == 1:
            self.btn_process.setText("Lancer : Vidéo Locale + ASS")
        elif index == 2:
            self.btn_process.setText("Lancer : Vidéo YouTube")
        else:
            self.btn_process.setText("Lancer le Processus")

    def toggle_youtube_input(self, index: int):
        """
        Affiche ou masque le champ URL YouTube selon le workflow sélectionné.

        Args:
            index (int): Index du workflow sélectionné.
        """
        if index == 2:
            self.input_youtube_url.show()
            self.label_video.setText("Vidéo: Prête à être téléchargée")
        else:
            self.input_youtube_url.hide()
            self.label_video.setText("Vidéo: Non sélectionnée")

    def set_ui_enabled(self, enabled: bool):
        """
        Active ou désactive les contrôles principaux de l'interface.

        Args:
            enabled (bool): État d'activation des contrôles.
        """
        self.btn_process.setEnabled(enabled)

    def launch_process(self):
        """
        Lance le workflow sélectionné en fonction de l'index courant.
        """
        workflow_index = self.cmb_workflow.currentIndex()

        if workflow_index == 0:
            logging.info("[MainWindow] Workflow sélectionné: Auto Local.")
            self.tasks_manager.run_local_auto_workflow(self)

        elif workflow_index == 1:
            logging.info("[MainWindow] Workflow sélectionné: Manuel (ASS fourni).")
            self.tasks_manager.run_manual_ass_workflow(self)

        elif workflow_index == 2:
            url = self.input_youtube_url.text().strip()
            if not url:
                QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL YouTube valide.")
                self.btn_process.setEnabled(True)
                return

            logging.info(f"[MainWindow] Workflow sélectionné: Auto YouTube — URL: {url}")
            self.tasks_manager.run_youtube_workflow(url, self)

        else:
            QMessageBox.critical(self, "Erreur", "Choix de workflow invalide.")
            self.btn_process.setEnabled(True)

    def closeEvent(self, event):
        """
        Nettoie les ressources avant la fermeture de la fenêtre.

        Args:
            event (QCloseEvent): Événement de fermeture.
        """
        if hasattr(self, 'tasks_manager'):
            self.tasks_manager.cleanup_resources()
        event.accept()

def main():
    """
    Point d'entrée principal de l'application.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.excepthook = lambda cls, val, tb: logging.error("Unhandled Exception", exc_info=(cls, val, tb))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()