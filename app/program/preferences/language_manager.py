# program/preferences/language_manager.py 
import json
from pathlib import Path

class LanguageManager:
    """
    Gère le mapping entre les noms de langue et leurs codes ISO (639-1 et 639-2).
    Charge les données depuis un fichier JSON et fournit des méthodes pour accéder aux codes.
    """

    def __init__(self, languages_file_path: Path):
        """
        Initialise le gestionnaire de langues avec le chemin vers le fichier JSON.

        Args:
            languages_file_path (Path): Chemin vers le fichier JSON contenant les données des langues.
        """
        self.languages_file_path = languages_file_path
        self._load_languages()

    def _load_languages(self):
        """
        Charge le dictionnaire des langues depuis le fichier JSON.
        En cas d'erreur, initialise un dictionnaire vide.
        """
        try:
            with open(self.languages_file_path, 'r', encoding='utf-8') as f:
                self.language_data = json.load(f)
        except Exception as e:
            print(f"❌ Erreur critique au chargement des langues : {e}")
            self.language_data = {}

    def get_supported_language_names(self) -> list[str]:
        """
        Retourne la liste des noms complets des langues supportées, triés par ordre alphabétique.
        Utilisé pour l'affichage dans l'interface utilisateur.

        Returns:
            list[str]: Liste des noms de langues.
        """
        return sorted(list(self.language_data.keys()))

    def get_code(self, language_name: str, code_type: str = 'iso639_2') -> str | None:
        """
        Récupère un code ISO spécifique (par défaut 'iso639_2') pour une langue donnée.

        Args:
            language_name (str): Nom complet de la langue (ex: 'Arabic', 'French').
            code_type (str): Type de code souhaité ('iso639_1' ou 'iso639_2').

        Returns:
            str | None: Code ISO correspondant ou None si non trouvé.
        """
        data = self.language_data.get(language_name)
        if data:
            return data.get(code_type)
        return None
