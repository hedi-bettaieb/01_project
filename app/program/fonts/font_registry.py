import logging
#program/fonts/fonts_registry.py
import os
import json
from pathlib import Path
import shutil
from fontTools.ttLib import TTFont
from program.utils.paths import PathManager

class FontRegistry:
    """
    Singleton pour la gestion centralisée des polices.
    Charge, valide, scanne et sauvegarde le registre des polices disponibles.
    """

    _instance = None
    _is_initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FontRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if FontRegistry._is_initialized:
            return
        self._initialize_once()
        FontRegistry._is_initialized = True

    def _initialize_once(self):
        """Initialise les chemins et charge le registre des polices."""
        self.path_manager = PathManager()
        self.fonts_dir = self.path_manager.get_path("ressources/fonts")
        self.registry_file = self.fonts_dir / "fonts.json"
        self.registry = {}

        self.load_registry()
        if not self._validate_registry():
            logging.info("[FontRegistry] Registre invalide, rescan nécessaire")
            self.scan_fonts()

    def load_registry(self):
        """
        Charge le registre des polices depuis le fichier JSON.
        En cas d'échec, initialise un registre vide.
        """
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
                total_polices = sum(len(polices) for polices in self.registry.values())
            logging.info(f"[FontRegistry] {total_polices} polices chargées")
        except (FileNotFoundError, json.JSONDecodeError):
            self.registry = {"arabic_fonts": {}, "latin_fonts": {}}
            logging.info("[FontRegistry] Registre non trouvé ou corrompu")

    def _validate_registry(self) -> bool:
        """
        Valide que toutes les polices enregistrées existent sur le disque.

        Returns:
            bool: True si toutes les polices existent, False sinon.
        """
        try:
            return all((self.fonts_dir / Path(path)).exists() for path in self._all_font_paths())
        except Exception as e:
            logging.info(f"[ERREUR] FontRegistry Validation du registre : {str(e)}")
            return False

    def _all_font_paths(self):
        """
        Générateur pour tous les chemins de police dans toutes les catégories.

        Yields:
            str: Chemin relatif de chaque police.
        """
        for category_dict in self.registry.values():
            # Vérifier que category_dict est bien un dictionnaire
            if isinstance(category_dict, dict):
                for path in category_dict.values():
                    yield path

    def scan_fonts(self):
        """
        Scanne le répertoire des polices et met à jour le registre.
        Trie les polices par catégorie (arabic_fonts, latin_fonts).
        """
        arabic_fonts = {}
        latin_fonts = {}
        other_fonts = {}

        for root, _, files in os.walk(self.fonts_dir):
            for file in files:
                if file.lower().endswith(('.ttf', '.otf')):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(self.fonts_dir).as_posix()
                    font_name = Path(file).stem.strip()
                    folder = Path(rel_path).parts[0] if len(Path(rel_path).parts) > 1 else ""

                    if folder == "arabic_fonts":
                        arabic_fonts[font_name] = rel_path
                    elif folder == "latin_fonts":
                        latin_fonts[font_name] = rel_path
                    else:
                        other_fonts[font_name] = rel_path

        # Maintenir la structure hiérarchique
        self.registry = {
            "arabic_fonts": dict(sorted(arabic_fonts.items(), key=lambda x: x[0].lower())),
            "latin_fonts": dict(sorted(latin_fonts.items(), key=lambda x: x[0].lower())),
        }
        
        # Ajouter les autres polices seulement s'il y en a
        if other_fonts:
            self.registry["other_fonts"] = dict(sorted(other_fonts.items(), key=lambda x: x[0].lower()))
            
        self.save_registry()
        total_polices = sum(len(polices) for polices in self.registry.values())
        logging.info(f"[FontRegistry] Scan terminé : {total_polices} polices enregistrées")

    def save_registry(self):
        """
        Sauvegarde le registre des polices dans le fichier JSON.
        """
        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.info(f"[ERREUR] FontRegistry Sauvegarde du registre : {str(e)}")

    def get_available_fonts(self, folder_name: str) -> list[str]:
        """
        Retourne les noms des polices disponibles dans une catégorie donnée.

        Args:
            folder_name (str): Catégorie des polices.

        Returns:
            list[str]: Liste des noms de polices triés.
        """
        polices = self.registry.get(folder_name, {})
        return sorted(list(polices.keys()))

    def _get_font_folder_by_language(self, language_code: str) -> str:
        """
        Détermine le dossier de polices en fonction du code de langue.

        Args:
            language_code (str): Code de langue (ex: 'ara', 'fr').

        Returns:
            str: Dossier correspondant ('arabic_fonts' ou 'latin_fonts').
        """
        if language_code and language_code.startswith("ara"):
            return "arabic_fonts"
        return "latin_fonts"

    def clean_registry(self):
        """
        Nettoie le registre en supprimant les entrées de polices inexistantes.
        """
        removed_fonts = []
        new_registry = {}

        for category_name, category_dict in self.registry.items():
            new_category_dict = {}
            for font_name, rel_path in category_dict.items():
                path = self.fonts_dir / rel_path
                if path.exists():
                    new_category_dict[font_name] = rel_path
                else:
                    removed_fonts.append(f"{category_name}/{font_name}")
            
            new_registry[category_name] = new_category_dict

        if removed_fonts:
            logging.info(f"[FontRegistry] {len(removed_fonts)} police(s) supprimée(s) du registre :")
            for name in removed_fonts:
                logging.info(f"  - {name}")
        else:
            logging.info("[FontRegistry] Aucune police orpheline trouvée")

        self.registry = new_registry
        self.save_registry()
        total_polices = sum(len(polices) for polices in self.registry.values())
        logging.info(f"[FontRegistry] {total_polices} police(s) dans le registre")

    
    def get_font_path(self, font_name: str, folder_name: str) -> Path | None:
        """
        Retourne le chemin absolu d'une police dans une catégorie donnée.

        Args:
            font_name (str): Nom de la police.
            folder_name (str): Catégorie/dossier de la police.

        Returns:
            Path | None: Chemin absolu vers la police ou None si non trouvée.
        """
        category_dict = self.registry.get(folder_name, {})
        relative_path = category_dict.get(font_name)
        
        if not relative_path:
            return None

        rel_path = Path("ressources/fonts").joinpath(relative_path).as_posix()
        return self.path_manager.get_path(rel_path)

    def get_all_categories(self) -> list[str]:
        """
        Retourne la liste des catégories disponibles.

        Returns:
            list[str]: Liste des noms de catégories.
        """
        return list(self.registry.keys())

    def get_total_font_count(self) -> int:
        """
        Retourne le nombre total de polices dans le registre.

        Returns:
            int: Nombre total de polices.
        """
        return sum(len(category_dict) for category_dict in self.registry.values())


    
    def import_font_file(self, chemin_police: str, destination_folder: str) -> str | None:
        """
        Copie physiquement un fichier de police et met à jour le registre.

        Args:
            chemin_police (str): Chemin vers le fichier de police à importer.
            destination_folder (str): Dossier de destination ('arabic_fonts' ou 'latin_fonts').

        Returns:
            str | None: Nom de la police importée ou None si déjà présente.

        Raises:
            Exception: En cas d'erreur lors de l'importation.
        """
        try:
            ext = chemin_police.split('.')[-1]
            nom_police = Path(chemin_police).stem.strip()

            if not nom_police:
                raise ValueError("Nom de police non trouvé.")

            dossier_destination = self.fonts_dir / destination_folder
            dossier_destination.mkdir(parents=True, exist_ok=True)
            chemin_destination = dossier_destination / f"{nom_police}.{ext}"

            # Vérifier si la police existe déjà dans le dossier cible
            if destination_folder in self.registry and nom_police in self.registry[destination_folder]:
                return None  # Police déjà présente

            shutil.copyfile(chemin_police, chemin_destination)
            rel_path = chemin_destination.relative_to(self.fonts_dir).as_posix()
            
            # CORRECTION: S'assurer que la structure hiérarchique est maintenue
            if destination_folder not in self.registry:
                self.registry[destination_folder] = {}
            
            # Ajouter la police dans le bon dossier
            self.registry[destination_folder][nom_police] = rel_path
            
            self.save_registry()

            logging.info(f"[FontRegistry] ✅ Police '{nom_police}' importée dans '{destination_folder}'.")
            return nom_police

        except Exception as e:
            logging.info(f"[ERREUR] FontRegistry Échec de l'importation de {chemin_police}: {e}")
            raise
    