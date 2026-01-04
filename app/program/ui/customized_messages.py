import logging
#program/ui/customized_message.py 
from PyQt6.QtCore import QTimer, Qt 
from PyQt6.QtWidgets import QMessageBox

def customized_message(parent, titre, texte, timeout = 4000):
    """
    Affiche une QMessageBox non bloquante qui se ferme automatiquement après 'timeout' millisecondes.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(titre)
    box.setText(texte)
    box.setIcon(QMessageBox.Icon.Information)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setWindowModality(Qt.WindowModality.NonModal)
    box.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

    # Timer de fermeture
    QTimer.singleShot(timeout, box.accept)

    box.show()

