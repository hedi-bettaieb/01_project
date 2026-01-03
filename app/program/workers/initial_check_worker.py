#program/workers/initial_check_worker.py
from PyQt6.QtCore import QThread, pyqtSignal

class InitialCheckWorker(QThread):
    """
    Thread léger dédié à la vérification de la connectivité Internet.
    Émet un signal à la fin de la vérification pour informer de l'état de la connexion.
    """
    checkFinished = pyqtSignal(bool)  # True si la connexion est OK, False sinon

    def __init__(self, monitor, parent=None):
        """
        Initialise le worker avec un objet de monitoring de la connexion.

        Args:
            monitor: Instance de la classe responsable du monitoring de la connexion Internet.
            parent (QObject, optional): Parent Qt. Par défaut None.
        """
        super().__init__(parent)
        self.monitor = monitor

    def run(self):
        """
        Méthode principale exécutée dans le thread.
        Effectue la vérification de la connexion Internet et émet un signal avec le résultat.
        """
        is_connected = self.monitor.check_internet_connection()
        self.checkFinished.emit(is_connected)
