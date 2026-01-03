# program/ui/dialogs_manager.py
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtGui import QColor
from pathlib import Path
from program.ui.color_selector import ColorSelectorDialog
from program.preferences.user_preferences import UserPreferences
from program.ui.customized_messages import customized_message


class DialogsManager:
    """
    Classe de service dédiée à la gestion des dialogues d'interaction utilisateur (I/O).
    Responsabilités :
      - Sélection de fichiers (vidéo, sous-titres, polices).
      - Gestion des préférences utilisateur (langue, police, couleur, taille, accessibilité).
      - Affichage de notifications et de dialogues de confirmation.
    """

    def __init__(self):
        """Initialise le gestionnaire de dialogues."""
        pass


    def _select_file(self, parent_widget, dialog_title: str, file_filter: str, initial_dir: str = "") -> str | None:
        """
        Méthode générique avec support du dossier initial.
        """
        chemin, _ = QFileDialog.getOpenFileName(
            parent_widget,
            dialog_title,
            initial_dir,  # Utilise le chemin passé en argument
            file_filter
        )
        return chemin if chemin else None


    def select_video_file(self, parent_widget) -> str | None:
        """
        Ouvre un dialogue pointant par défaut sur le dossier Vidéos de l'utilisateur.
        """
        # Cible C:\Users\Nom\Videos
        default_path = os.path.expanduser("~/Videos")
        
        return self._select_file(
            parent_widget,
            "Choisir une vidéo locale",
            "Vidéos (*.mp4 *.mkv *.avi *.mov)",
            initial_dir=default_path
        )


    def select_ass_file(self, parent_widget) -> str | None:
        """
        Ouvre un dialogue pour choisir un fichier de sous-titres .ass.

        Args:
            parent_widget: Widget parent pour le dialogue.

        Returns:
            str | None: Chemin du fichier .ass sélectionné ou None si annulé.
        """
        return self._select_file(
            parent_widget,
            "Choisir un fichier de sous-titres .ass",
            "Fichiers ASS (*.ass)"
        )

    # --- Méthodes de notification ---
    def notify(self, parent_widget, title: str, message: str, icon: str = "info"):
        """
        Affiche une notification à l'utilisateur.

        Args:
            parent_widget: Widget parent pour la boîte de dialogue.
            title (str): Titre de la notification.
            message (str): Message à afficher.
            icon (str): Type d'icône ("info", "warning", "critical").
        """
        # Mapping de l'icône
        if icon == "warning":
            q_icon = QMessageBox.Icon.Warning
        elif icon == "critical":
            q_icon = QMessageBox.Icon.Critical
        else:
            q_icon = QMessageBox.Icon.Information

        msg = QMessageBox(parent_widget)
        msg.setIcon(q_icon)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    def notify_font_available(self, parent_widget, font_name: str):
        """
        Affiche une notification indiquant qu'une police est disponible.

        Args:
            parent_widget: Widget parent pour la boîte de dialogue.
            font_name (str): Nom de la police disponible.
        """
        self.notify(
            parent_widget,
            "Police disponible",
            f"La police '{font_name}' est disponible.",
            icon="info"
        )

    # --- Méthodes de sélection des préférences ---
    def _choisir_langue(self, user_preferences: UserPreferences, parent) -> tuple[str, str] | tuple[None, None]:
        """
        Ouvre un dialogue pour choisir la langue des sous-titres.

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent: Widget parent pour le dialogue.

        Returns:
            tuple[str, str] | tuple[None, None]: (Nom complet de la langue, code ISO-639-2) ou (None, None) si annulé.
        """
        # Récupération de la liste des langues supportées
        liste_langues = sorted(user_preferences.language_manager.get_supported_language_names())

        # Détermination de la langue par défaut
        langue_nom_defaut = user_preferences.get("langue", "English")
        if langue_nom_defaut not in liste_langues:
            index_defaut = 0
        else:
            index_defaut = liste_langues.index(langue_nom_defaut)

        # Affichage du dialogue de sélection
        langue_nom, ok = QInputDialog.getItem(
            parent,
            "Langue des sous-titres",
            "Choisissez la langue :",
            liste_langues,
            editable=False,
            current=index_defaut
        )

        if not ok:
            return None, None

        # Récupération du code ISO-639-2 correspondant
        code_iso = user_preferences.language_manager.get_code(langue_nom, code_type='iso639_2')
        return langue_nom, code_iso

    def _choisir_couleur(self, user_preferences: UserPreferences, parent) -> str | None:
        """
        Ouvre un dialogue pour choisir la couleur du texte.

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent: Widget parent pour le dialogue.

        Returns:
            str | None: Couleur sélectionnée (format hexadécimal) ou None si annulé.
        """
        couleur_actuelle = user_preferences.get("couleur", user_preferences.VALEURS_DEFAUT["couleur"])
        dialog_couleur = ColorSelectorDialog(parent=parent, couleur_actuelle=couleur_actuelle)
        if not dialog_couleur.exec():
            return None
        return dialog_couleur.couleur_selectionnee

    def _choisir_taille(self, user_preferences: UserPreferences, parent) -> int | None:
        """
        Ouvre un dialogue pour choisir la taille de la police.

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent: Widget parent pour le dialogue.

        Returns:
            int | None: Taille de police sélectionnée ou None si annulé.
        """
        taille_actuelle = int(user_preferences.get("taille_police", user_preferences.VALEURS_DEFAUT["taille_police"]))
        taille, ok = QInputDialog.getInt(
            parent,
            "Taille de police",
            "Entrez la taille de police :",
            taille_actuelle,
            8, 200, 1
        )
        return taille if ok else None

    def _gerer_accessibilite(self, user_preferences: UserPreferences, parent) -> tuple[bool, int, int]:
        """
        Gère les paramètres d'accessibilité (opacité du fond, épaisseur de la bordure).

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent: Widget parent pour le dialogue.

        Returns:
            tuple[bool, int, int]: (accessibilité activée, opacité du fond, épaisseur de la bordure).
        """
        prefs = user_preferences
        defaults = prefs.VALEURS_DEFAUT

        # Sélection du mode d'accessibilité
        acces_actuel = prefs.get("accessibilite", defaults["accessibilite"])
        activer_access, ok = QInputDialog.getItem(
            parent,
            "Accessibilité",
            "Activer le mode haute visibilité :",
            ["Désactivé", "Activé"],
            current=1 if acces_actuel else 0,
            editable=False
        )

        if not ok:
            return (
                acces_actuel,
                prefs.get("opacite_fond", defaults["opacite_fond"]),
                prefs.get("epaisseur_bordure", defaults["epaisseur_bordure"])
            )

        accessibilite = (activer_access == "Activé")

        # Paramètres d'opacité et de bordure si l'accessibilité est activée
        opacite = prefs.get("opacite_fond", defaults["opacite_fond"])
        bordure = prefs.get("epaisseur_bordure", defaults["epaisseur_bordure"])

        if accessibilite:
            opacite_current = int(prefs.get("opacite_fond", defaults["opacite_fond"]))
            opacite, ok_opacite = QInputDialog.getInt(
                parent,
                "Opacité du fond",
                "Opacité du fond noir (%) :",
                opacite_current,
                10, 100, 5
            )
            if not ok_opacite:
                opacite = opacite_current

            bordure_current = int(prefs.get("epaisseur_bordure", defaults["epaisseur_bordure"]))
            bordure, ok_bordure = QInputDialog.getInt(
                parent,
                "Épaisseur de la bordure",
                "Épaisseur de la bordure (pixels) :",
                bordure_current,
                0, 10, 1
            )
            if not ok_bordure:
                bordure = bordure_current

        return accessibilite, opacite, bordure

    def demander_preferences_style(self, user_preferences: UserPreferences, parent_widget=None) -> bool:
        """
        Ouvre une série de dialogues pour configurer les préférences de style (langue, police, couleur, etc.).

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent_widget: Widget parent pour les dialogues.

        Returns:
            bool: True si les préférences ont été mises à jour, False si annulé.
        """
        # 1. Sélection de la langue
        langue_nom, langue_code = self._choisir_langue(user_preferences, parent_widget)
        if not langue_nom:
            return False

        # 2. Sélection de la police
        police_selectionnee = self._choisir_police(user_preferences, parent_widget, langue_nom)
        if not police_selectionnee:
            return False

        # 3. Sélection de la couleur
        couleur = self._choisir_couleur(user_preferences, parent_widget)
        if not couleur:
            return False

        # 4. Sélection de la taille de police
        taille = self._choisir_taille(user_preferences, parent_widget)
        if not taille:
            return False

        # 5. Configuration de l'accessibilité
        accessibilite, opacite, bordure = self._gerer_accessibilite(user_preferences, parent_widget)



        # 6. Dossier YouTube : Uniquement si cmb_workflow est sur l'index 2
        dossier_yt = user_preferences.config.get("dossier_youtube", "")
        
        if parent_widget.cmb_workflow.currentIndex() == 2:
            dossier_yt = QFileDialog.getExistingDirectory(
                parent_widget, 
                "Choisir le dossier d'enregistrement YouTube",
                dossier_yt if dossier_yt else os.path.expanduser("~\\Videos")
            )
            if not dossier_yt: return False # Annulation globale si dossier non choisi

        # 7. Mise à jour
        collected_data = {
            "langue": langue_nom,
            "police": police_selectionnee,
            "taille_police": taille,
            "couleur": couleur,
            "accessibilite": accessibilite,
            "opacite_fond": opacite,
            "epaisseur_bordure": bordure,
            "dossier_youtube": dossier_yt
        }
        user_preferences.update_config_from_ui(collected_data)
        return True

    

    # --- Méthodes de gestion des polices ---
    def select_file_for_import(self, parent_widget) -> str | None:
        """
        Ouvre un dialogue pour importer un fichier de police (.ttf ou .otf).

        Args:
            parent_widget: Widget parent pour le dialogue.

        Returns:
            str | None: Chemin du fichier de police sélectionné ou None si annulé.
        """
        chemin, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Importer une police",
            "",
            "Fichiers de police (*.ttf *.otf)"
        )
        return chemin

    def prompt_for_font_category(self, parent_widget, font_name: str) -> str | None:
        """
        Ouvre un dialogue pour choisir la catégorie d'une police importée.

        Args:
            parent_widget: Widget parent pour le dialogue.
            font_name (str): Nom de la police à catégoriser.

        Returns:
            str | None: Catégorie sélectionnée ("arabic_fonts" ou "latin_fonts") ou None si annulé.
        """
        dossier, ok = QInputDialog.getItem(
            parent_widget,
            "Catégorie de police",
            f"Dans quelle catégorie classer '{font_name}' ?",
            ["arabic_fonts", "latin_fonts"],
            0,
            False
        )
        return dossier if ok else None

    def _choisir_police(self, user_preferences: UserPreferences, parent, langue_nom_complet: str) -> str | None:
        """
        Ouvre un dialogue pour choisir une police en fonction de la langue sélectionnée.

        Args:
            user_preferences (UserPreferences): Instance des préférences utilisateur.
            parent: Widget parent pour le dialogue.
            langue_nom_complet (str): Nom complet de la langue sélectionnée.

        Returns:
            str | None: Nom de la police sélectionnée ou None si annulé.
        """
        from program.ui.fonts_dialog import FontDialog

        # Déduction du dossier en fonction de la langue
        langue_nom_lower = langue_nom_complet.strip().lower()
        folder_name = "arabic_fonts" if langue_nom_lower == 'arabic' else "latin_fonts"

        # Récupération des polices disponibles
        polices_disponibles = user_preferences.font_manager.get_available_fonts(folder_name)
        if not polices_disponibles:
            self.notify(parent, "Avertissement", f"Aucune police trouvée pour la catégorie '{folder_name}'.", icon="warning")
            return None

        # Affichage du dialogue de sélection de police
        dialog_police = FontDialog(
            polices_disponibles=polices_disponibles,
            dialogs_manager=self,
            parent=parent,
            folder_name=folder_name, 
                context = "Initial"  
        )

        # Sélection de la police actuelle si elle existe
        police_actuelle = Path(user_preferences.get("police", "")).stem
        if police_actuelle:
            dialog_police.selectionner_police(police_actuelle)

        if not dialog_police.exec():
            return None

        return dialog_police.police_selectionnee
