import logging
#program/ui/color_selector.py
from PyQt6.QtWidgets import (
    QApplication, QDialog, QListWidget, QListWidgetItem,
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt
import sys


class ColorSelectorDialog(QDialog):
    """
    Boîte de dialogue simple pour choisir une couleur de texte parmi une liste prédéfinie.
    """
    COULEURS_DISPONIBLES = [
        "black", "white", "red", "green", "blue",
        "yellow", "magenta", "cyan", "orange",
        "purple", "brown", "gray", "pink" , "hotpink"
    ]

    def __init__(self, parent=None, couleur_actuelle="white"):
        super().__init__(parent)
        self.setWindowTitle("Choisir une couleur de texte")
        self.setMinimumWidth(300)
        self.couleur_selectionnee = couleur_actuelle

        layout = QVBoxLayout()

        self.liste = QListWidget()
        for couleur in self.COULEURS_DISPONIBLES:
            item = QListWidgetItem(couleur.capitalize())
            item.setForeground(QBrush(QColor(couleur)))
            item.setBackground(QColor("black") if couleur.lower() == "white" else QColor("white"))
            item.setData(Qt.ItemDataRole.UserRole, couleur)
            self.liste.addItem(item)
            if couleur == couleur_actuelle:
                item.setSelected(True)

        layout.addWidget(QLabel("Sélectionnez une couleur :"))
        layout.addWidget(self.liste)

        boutons = QHBoxLayout()
        ok_btn = QPushButton("Valider")
        cancel_btn = QPushButton("Annuler")
        boutons.addWidget(ok_btn)
        boutons.addWidget(cancel_btn)
        layout.addLayout(boutons)

        self.setLayout(layout)

        ok_btn.clicked.connect(self.valider)
        cancel_btn.clicked.connect(self.reject)

    def valider(self):
        items = self.liste.selectedItems()
        if items:
            self.couleur_selectionnee = items[0].data(Qt.ItemDataRole.UserRole)
        self.accept()


#TEST UNITAIRE SEUL ---
# if __name__ == "__main__":
    # app = QApplication(sys.argv)
    # dlg = ColorSelectorDialog()
    # if dlg.exec():
        # logging.info(f"✅ Couleur choisie : {dlg.couleur_selectionnee}")
    # else:
        # logging.info("❌ Annulé")