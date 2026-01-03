#program/fonts/fonts_manager.py
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from program.fonts.font_registry import FontRegistry
from program.fonts.ass_font_manipulator import AssFontManipulator
from program.ui.customized_messages import customized_message


class FontManager:
    """
    Orchestrateur de l'interface utilisateur pour la gestion des polices.
    Utilise `FontRegistry` pour accéder aux polices et `AssFontManipulator` pour manipuler les fichiers ASS.
    N'est plus un Singleton et ne gère plus le chargement des polices.
    """

    def __init__(self, parent=None):
        """
        Initialise l'instance avec les registres de polices et de manipulation ASS.

        Args:
            parent: Widget parent pour les dialogues UI (optionnel).
        """
        self.parent = parent
        self.font_registry = FontRegistry()
        self.ass_manipulator = AssFontManipulator()

    def get_font_path(self, font_name: str, folder_name: str) -> Path | None:
        """
        Récupère le chemin d'une police dans une catégorie donnée.

        Args:
            font_name (str): Nom de la police.
            folder_name (str): Catégorie/dossier de la police.

        Returns:
            Path | None: Chemin vers la police ou None si non trouvée.
        """
        return self.font_registry.get_font_path(font_name, folder_name)

    def get_available_fonts(self, folder_name: str) -> list[str]:
        """
        Retourne la liste des polices disponibles dans une catégorie.

        Args:
            folder_name (str): Catégorie/dossier des polices.

        Returns:
            list[str]: Liste des noms de polices disponibles.
        """
        return self.font_registry.get_available_fonts(folder_name)

    def is_font_available(self, font_name: str, folder_name: str) -> bool:
        """
        Vérifie si une police est disponible dans une catégorie.

        Args:
            font_name (str): Nom de la police.
            folder_name (str): Catégorie/dossier des polices.

        Returns:
            bool: True si la police est disponible, False sinon.
        """
        font_path = self.font_registry.get_font_path(font_name, folder_name)
        return font_path is not None


    def handle_missing_font(self, missing_font: str, ass_file: str, parent_widget=None) -> str:
        """
        Gère le scénario de police manquante : propose une sélection et remplace la police dans le fichier ASS.

        Args:
            missing_font: Nom de la police manquante.
            ass_file: Chemin vers le fichier ASS à traiter.
            parent_widget: Widget parent pour les dialogues UI (optionnel).

        Returns:
            Chemin vers le fichier ASS modifié ou original si annulé ou en cas d'erreur.
        """
        from program.ui.fonts_dialog import FontDialog
        from program.preferences.user_preferences import UserPreferences
        
        # Récupération de la langue et du dossier cible (NÉCESSAIRE DANS LES DEUX CAS : OUI ou NON)
        detected_result = self.ass_manipulator.detect_language_from_ass(ass_file)
        detected_lang_code = detected_result[1] if detected_result else 'und'
        
        # Déduction du dossier de polices en fonction de la langue détectée
        folder_name = "arabic_fonts" if detected_lang_code =='ar' else "latin_fonts"
        
        # Récupération de la liste des polices disponibles dans le dossier cible (NÉCESSAIRE DANS LES DEUX CAS)
        available_fonts = self.get_available_fonts(folder_name)

        # 1. Gestion du cas où AUCUNE police n'est disponible
        if not available_fonts:
            # Ceci couvre le cas extrême avant toute interaction utilisateur
            QMessageBox.warning(
                parent_widget,
                "Polices manquantes",
                f"Aucune police disponible dans le dossier '{folder_name}'. Le fichier ASS n'est pas modifié."
            )
            return ass_file
        
        # --- Début de la logique de remplacement ---
        
        # 2. Confirmation utilisateur
        if not self._confirm_font_replacement(missing_font, parent_widget):
            # *** CHEMIN DE SECOURS (FALLBACK) ACTIVÉ - DYNAMIQUE ***
            
            # 🎯 Définir la police de secours sur la première police disponible (index 0)
            fallback_font = available_fonts[0] # Disponible car vérifiée ci-dessus
            
            # Remplacement automatique 
            try:
                new_file = self.ass_manipulator.replace_font_in_ass(
                    missing_font, 
                    fallback_font, 
                    ass_file, 
                    folder_name
                )

                # 💡 CORRECTION: Mettre à jour les préférences de l'utilisateur avec la police de secours
                self._update_user_preferences(fallback_font) 
                msg = f"[FontManager] Remplacement de secours auto: '{missing_font}' -> '{fallback_font}' (index 0)."
                print(msg) 
                QMessageBox.information(parent_widget, "Remplacement" , msg) 
                return new_file
                
            except Exception as e:
                # Si le remplacement de secours échoue
                print(f"[ERREUR] Échec du remplacement de secours : {e}")
                return ass_file
                
        # --- CHEMIN DE SÉLECTION MANUELLE (Utilisateur a dit OUI) ---
        
        # Affichage de la boîte de dialogue pour sélectionner une nouvelle police
        # available_fonts et parent_widget sont définis ici !
        selected_font = self._show_font_selection_dialog(available_fonts, parent_widget)
        if not selected_font:
            # L'utilisateur a cliqué sur Annuler dans le dialogue de sélection
            return ass_file

        # Tentative de remplacement de la police dans le fichier ASS
        try:
            new_file = self.ass_manipulator.replace_font_in_ass(missing_font, selected_font, ass_file, folder_name)
            customized_message(
                parent_widget,
                "Succès",
                f"La police '{missing_font}' a été remplacée par '{selected_font}'."
            )
            self._update_user_preferences(selected_font)
            return new_file
        except Exception as e:
            QMessageBox.critical(
                parent_widget,
                "Erreur",
                f"Échec du remplacement de la police : {e}"
            )
            return ass_file


    

    
# --- Méthodes internes ---
    def _confirm_font_replacement(self, missing_font: str, parent_widget) -> bool:
        """
        Affiche une boîte de dialogue pour confirmer le remplacement de la police.

        Args:
            missing_font (str): Police manquante.
            parent_widget: Widget parent pour la boîte de dialogue.

        Returns:
            bool: True si l'utilisateur confirme, False sinon.
        """
        response = QMessageBox.question(
            parent_widget,
            "Police manquante ou incompatible",
            f"La police '{missing_font}' est introuvable ou incompatible avec la langue détectée.\n"
            "Souhaitez-vous en choisir une autre ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return response == QMessageBox.StandardButton.Yes
        
        
        
    def _show_font_selection_dialog(self, available_fonts: list, parent_widget) -> str:
        """
        Affiche un dialogue pour sélectionner une police parmi celles disponibles.

        Args:
            available_fonts (list): Liste des polices disponibles.
            parent_widget: Widget parent pour le dialogue.

        Returns:
            str: Police sélectionnée ou None si annulé.
        """
        from program.ui.fonts_dialog import FontDialog
        from program.ui.dialogs_manager import DialogsManager

        dialogs_manager = DialogsManager()
        dialog = FontDialog(
            polices_disponibles=available_fonts,
            dialogs_manager=dialogs_manager,
            parent=parent_widget
        )

        ##faux : dialog = FontDialog(available_fonts, parent_widget)
        if dialog.exec() and dialog.police_selectionnee:
            return dialog.police_selectionnee
        return None

    def _update_user_preferences(self, selected_font: str):
        """
        Met à jour les préférences utilisateur avec la police sélectionnée.

        Args:
            selected_font (str): Police sélectionnée.
        """
        from program.preferences.user_preferences import UserPreferences
        try:
            # Passer self (FontManager) au constructeur
            prefs = UserPreferences(self)
            prefs.config["police"] = f"{selected_font}.ttf"
            prefs.sauvegarder_preferences()
            print(f"[FontManager] Configuration mise à jour vers : {selected_font}")
        except Exception as e:
            print(f"[ERREUR] Mise à jour des préférences : {e}")
