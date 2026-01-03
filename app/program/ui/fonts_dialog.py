# program/ui/font_dialog.py
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QLineEdit,
    QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from program.fonts.font_registry import FontRegistry
from program.ui.dialogs_manager import DialogsManager
from program.utils.paths import PathManager
from program.ui.customized_button import CustomizedButton


class FontDialog(QDialog):
    """
    Dialogue pour sélectionner ou importer une police.
    Permet de visualiser un aperçu de la police sélectionnée et de gérer l'importation de nouvelles polices.
    """

    def __init__(self, polices_disponibles: list[str], dialogs_manager: DialogsManager, parent=None, folder_name: str = "latin_fonts", context: str = "remplacement"):
        """
        Initialise le dialogue de sélection de police.

        Args:
            polices_disponibles (list[str]): Liste des polices disponibles à afficher.
            dialogs_manager (DialogsManager): Instance du gestionnaire de dialogues pour les interactions utilisateur.
            parent: Widget parent (optionnel).
            folder_name (str): Dossier de polices à utiliser (par défaut : "latin_fonts").
        """
        super().__init__(parent)



        self.folder_name = folder_name
        self.paths = PathManager()
        self.font_registry = FontRegistry()
        self.registry = self.font_registry.registry
        self.dialogs_manager = dialogs_manager
        #print(">>> DEBUG FontDialog: dialogs_manager = ", type(dialogs_manager))
        #import traceback; traceback.print_stack()

        self.police_selectionnee = None
        
        # 🔥 INITIALISATION DU CACHE
        self._cache_polices_chargees = {}

    # Titre adaptatif
        titre = "Choisir une police de remplacement" if context == "Remplacement" else "Sélectionnez la police des sous-titres"
        self.setWindowTitle(titre)

        
        self.setMinimumWidth(400)

        # --- Widgets ---
        lbl_info = QLabel("Sélectionnez une police disponible ou importez-en une :")
        self.liste_polices = QListWidget()
        self.liste_polices.addItems(polices_disponibles)

        # Zone d'aperçu de la police
        self.apercu_edit = QLineEdit("نموذج الخط الذي إخترته  Exemple de la police sélectionnée")
        self.apercu_edit.setReadOnly(True)
        self.apercu_edit.setMinimumHeight(40)

        # --- Boutons ---
        self.btn_importer = CustomizedButton("Importer...")
        self.btn_valider = CustomizedButton("Valider")
        self.btn_annuler = CustomizedButton("Annuler")

        # --- Layout des boutons ---
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_importer)
        btn_layout.addWidget(self.btn_valider)
        btn_layout.addWidget(self.btn_annuler)

        # --- Layout principal ---
        layout = QVBoxLayout()
        layout.addWidget(lbl_info)
        layout.addWidget(self.liste_polices)
        layout.addLayout(btn_layout)
        layout.addWidget(self.apercu_edit)
        self.setLayout(layout)

        # --- Connexions ---
        self.liste_polices.itemDoubleClicked.connect(self._valider_selection)
        self.btn_importer.clicked.connect(self._importer_police)
        self.btn_valider.clicked.connect(self._valider_selection)
        self.btn_annuler.clicked.connect(self.reject)
        self.liste_polices.currentItemChanged.connect(self._update_apercu)

    
    def _update_apercu(self):
        """
        Met à jour l'aperçu de la police sélectionnée.
        Charge dynamiquement la police et l'affiche dans la zone d'aperçu.
        """
        items = self.liste_polices.selectedItems()
        if not items:
            return

        nom_police = items[0].text()
        print(f">>> DEBUG: Cache size = {len(self._cache_polices_chargees)}, Police actuelle: {nom_police}")        
        
        # 🔥 VÉRIFIER LE CACHE D'ABORD
        if nom_police in self._cache_polices_chargees:
            print(f">>> DEBUG: Utilisation cache pour '{nom_police}'")
            font_famille = self._cache_polices_chargees[nom_police]
            font = QFont(font_famille, 18)
            self.apercu_edit.setFont(font)
            return

        font_path = self.font_registry.get_font_path(nom_police, self.folder_name)
        if not font_path:
            return

        # Charger la police et appliquer l'aperçu
        id_police = QFontDatabase.addApplicationFont(str(font_path))
        if id_police == -1:
            print(f"[ERREUR] Impossible de charger la police {nom_police}")
            return

        familles = QFontDatabase.applicationFontFamilies(id_police)
        if familles:
            # 🔥 METTRE EN CACHE
            self._cache_polices_chargees[nom_police] = familles[0]
            print(f">>> DEBUG: Nouvelle police ajoutée au cache: '{nom_police}'")
            font = QFont(familles[0], 18)
            self.apercu_edit.setFont(font)
        else:
            print(f"[ERREUR] Famille introuvable pour {nom_police}")

    def _cleanup_font_cache(self):
        """
        Nettoie le cache des polices chargées.
        À appeler quand le dialogue est fermé.
        """
        print(f">>> DEBUG: Cleanup called - Avant: {len(self._cache_polices_chargees)} polices en cache")
        self._cache_polices_chargees.clear()
        print(f">>> DEBUG: Cleanup terminé - Après: {len(self._cache_polices_chargees)} polices en cache")

    def closeEvent(self, event):
        """
        Surcharge pour nettoyer le cache à la fermeture.
        """
        self._cleanup_font_cache()
        super().closeEvent(event)

    def reject(self):
        """
        Surcharge pour nettoyer le cache lors de l'annulation.
        """
        self._cleanup_font_cache()
        super().reject()

    def _valider_selection(self):
        """Valide la police sélectionnée dans la liste."""
        items = self.liste_polices.selectedItems()
        if not items:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner une police.")
            return
        self.police_selectionnee = items[0].text()
        
        # 🔥 NETTOYER LE CACHE APRÈS VALIDATION
        self._cleanup_font_cache()
        self.accept()

    def selectionner_police(self, nom_police: str):
        """
        Sélectionne une police spécifique dans la liste.

        Args:
            nom_police (str): Nom de la police à sélectionner.
        """
        items = self.liste_polices.findItems(nom_police, Qt.MatchFlag.MatchExactly)
        if items:
            item = items[0]
            self.liste_polices.setCurrentItem(item)
            self.liste_polices.scrollToItem(item)
            self.liste_polices.setFocus()

                
            

            #l'erreur = chemin_police = self.dialogs_manager.select_file_for_import(self)
            #il cherche la fonction dans videoselector = fenetre au lieu de dialogsmanager !!!
    def _importer_police(self):
        """
        Ouvre un dialogue pour importer une nouvelle police.
        Gère l'importation et met à jour la liste des polices disponibles.
        """
        # 1. Sélection du fichier de police
        chemin_police = self.dialogs_manager.select_file_for_import(self)
        if not chemin_police:
            return

        nom_police = Path(chemin_police).stem.strip()
        if not nom_police:
            self.dialogs_manager.notify(self, "Erreur", "Le nom de la police n'a pas pu être extrait.", icon="warning")
            return

        # 2. Choix du dossier de destination
        dossier = self.dialogs_manager.prompt_for_font_category(self, nom_police)
        if dossier is None:
            return  # L'utilisateur a annulé

        # 3. Importation de la police
        try:
            imported_font_name = self.font_registry.import_font_file(chemin_police, dossier)
            
            # Vérifier si l'importation a réellement eu lieu
            if imported_font_name is None:
                # Police déjà existante
                self.dialogs_manager.notify(
                    self,
                    "Police déjà disponible",
                    f"La police '{nom_police}' est déjà disponible dans le dossier '{dossier}'.",
                    icon="info"
                )
                return
            
            # Importation réussie - mettre à jour l'interface
            self._refresh_fonts_list(imported_font_name, dossier)

            self.dialogs_manager.notify(
                self,
                "Importation réussie",
                f"✅ Police '{imported_font_name}' importée dans 'fonts/{dossier}'.\nRegistre mis à jour.",
                icon="info"
            )
        except Exception as e:
            self.dialogs_manager.notify(self, "Erreur", f"Échec de l'importation : {str(e)}", icon="critical")

    
    def _refresh_fonts_list(self, imported_font_name: str, folder_name: str):
        """
        Met à jour la liste des polices disponibles après une importation.
        Filtre les polices par dossier et sélectionne la nouvelle police importée.

        Args:
            imported_font_name (str): Nom de la police nouvellement importée.
            folder_name (str): Dossier de la police importée.
        """
        # Récupérer les polices de la catégorie spécifique
        category_dict = self.registry.get(folder_name, {})
        available_fonts = list(category_dict.keys())
        
        # Trier et mettre à jour l'UI
        available_fonts.sort()
        self.liste_polices.clear()
        self.liste_polices.addItems(available_fonts)

        # Sélectionner la nouvelle police importée
        self.selectionner_police(imported_font_name)
    