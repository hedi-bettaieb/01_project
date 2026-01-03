#program/workers/progress_worker.py
from PyQt6.QtCore import QThread, pyqtSignal, QMutex

class ProgressThread(QThread):
    """
    Thread dédié à la simulation d'une progression (exemple : barre de chargement).
    Émet un signal de progression périodique entre 0 et 100.
    """
    progress = pyqtSignal(int)

    def __init__(self):
        """
        Initialise le thread et son état de fonctionnement.
        """
        super().__init__()
        self._running = True
        self._mutex = QMutex()

    def run(self):
        """
        Boucle principale du thread : émet un signal de progression cyclique entre 0 et 100.
        """
        value = 0
        while self._is_running():
            value = (value + 1) % 100
            self.progress.emit(value)
            self.msleep(100)

    def _is_running(self):
        """
        Vérifie de manière thread-safe si le thread doit continuer à s'exécuter.

        Returns:
            bool: True si le thread doit continuer, False sinon.
        """
        self._mutex.lock()
        running = self._running
        self._mutex.unlock()
        return running

    def stop(self):
        """
        Arrête le thread de manière sécurisée en modifiant l'état de fonctionnement.
        """
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
