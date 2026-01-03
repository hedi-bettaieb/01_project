# customized_button.py
"""
Bouton personnalisé compatible PyQt6 
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt
    
class CustomizedButton(QPushButton):
    """
    Bouton personnalisé qui gère :
    - Double-clic souris (converti en simple clic)
    - Touches Espace/Enter/Return
    - Compatible PyQt6 et PySide6
    """
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        # Permet d'activer Enter / Return sur ce bouton
        self.setDefault(True)
        # Permet de recevoir les touches clavier
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def mouseDoubleClickEvent(self, event):
        """Double-clic souris → on simule un clic normal"""
        self.click()
        super().mouseDoubleClickEvent(event)
    
    def keyPressEvent(self, event):
        """Espace / Enter / Return → on simule un clic normal"""
        if event.key() in (Qt.Key.Key_Space,
                           Qt.Key.Key_Return,
                           Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)
