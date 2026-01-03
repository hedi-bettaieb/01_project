#program/fonts/ass_font_manipulateur.py
import os
import re
import json
from pathlib import Path
from program.fonts.font_registry import FontRegistry
from program.utils.paths import PathManager

class AssFontManipulator:
    """
    Classe pour manipuler les polices et les métadonnées de langue dans les fichiers ASS (Advanced SubStation Alpha).
    Utilise FontRegistry pour vérifier la disponibilité des polices et PathManager pour accéder aux ressources.
    """

    def __init__(self):
        """
        Initialise l'instance avec les registres de polices et de chemins.
        """
        self.font_registry = FontRegistry()
        self.path_manager = PathManager()
        self.ass_json_path = self.path_manager.get_path("ressources/languages/languages.json")

    def detect_language_from_ass(self, ass_file_path: str) -> tuple[str, str, str] | None:
        """
        Détecte la langue d'un fichier ASS en lisant la ligne 'Language:'.
        Retourne un tuple (nom_complet, code_iso639_1, code_iso639_2) ou None si non trouvé.

        Args:
            ass_file_path (str): Chemin vers le fichier ASS.

        Returns:
            tuple[str, str, str] | None: (Nom de la langue, code ISO 639-1, code ISO 639-2) ou None.
        """
        if not os.path.exists(self.ass_json_path):
            raise FileNotFoundError(f"Fichier de référence '{os.path.basename(self.ass_json_path)}' manquant.")

        try:
            with open(self.ass_json_path, "r", encoding="utf-8") as f:
                lang_map = json.load(f)
        except Exception as e:
            print(f"❌ Erreur de lecture de languages.json : {e}")
            return None

        # Lecture du fichier ASS pour extraire la langue
        detected = None
        try:
            with open(ass_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.lower().startswith("language:"):
                        detected = line.split(":")[1].strip().lower()
                        break
        except Exception as e:
            print(f"❌ Erreur de lecture du fichier ASS : {e}")
            return None

        if not detected:
            print("⚠ Pas de champ 'Language:' dans le fichier ASS.")
            return None

        # Recherche du code langue dans le mapping JSON
        for name, entry in lang_map.items():
            if detected == entry["iso639_1"].lower() or detected == entry["iso639_2"].lower():
                iso639_1_code = entry["iso639_1"].lower()
                iso639_2_code = entry["iso639_2"].lower()
                print(f"[AssManipulator] 🌍 Langue ASS détectée: {name} (ISO-1: {iso639_1_code}, ISO-2: {iso639_2_code})")
                return name, iso639_1_code, iso639_2_code

        print(f"❌ Code langue ASS inconnu ou non mappé : {detected}")
        return None

    def detect_font_in_ass(self, ass_path: str) -> str | None:
        """
        Détecte la police utilisée dans un fichier ASS depuis la première ligne 'Style:'.
        Retourne le nom de la police ou None si non trouvé.

        Args:
            ass_path (str): Chemin vers le fichier ASS.

        Returns:
            str | None: Nom de la police ou None.
        """
        try:
            with open(ass_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith("Style:"):
                        parts = line.split(",")
                        if len(parts) > 1:
                            return parts[1].strip()
        except Exception as e:
            print(f"[ERREUR] Lecture du fichier ASS : {str(e)}")
        return None

    def replace_font_in_ass(self, old_font: str, new_font: str, ass_file: str, folder_name: str) -> str:
        """
        Remplace la police dans un fichier ASS et crée une copie modifiée.
        Vérifie que la nouvelle police est disponible dans FontRegistry.

        Args:
            old_font (str): Police à remplacer.
            new_font (str): Nouvelle police.
            ass_file (str): Chemin vers le fichier ASS original.
            folder_name (str): Catégorie de police ('arabic_fonts' ou 'latin_fonts').

        Returns:
            str: Chemin vers le fichier ASS modifié.

        Raises:
            ValueError: Si la nouvelle police n'est pas disponible.
        """
        if not self.font_registry.get_font_path(new_font, folder_name):
            raise ValueError(f"Police '{new_font}' non disponible dans le registre pour la catégorie '{folder_name}'.")


        base, ext = os.path.splitext(ass_file)
        new_path = f"{base}_modified{ext}"
        temp_path = f"{new_path}.tmp"

        try:
            with open(ass_file, 'r', encoding='utf-8') as f_in, \
                 open(temp_path, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    line = self._process_ass_line(line, old_font, new_font)
                    f_out.write(line)
            self._verify_font_replacement(temp_path, new_font)
            os.replace(temp_path, new_path)
            return new_path
        except Exception as e:
            self._cleanup_temp_file(temp_path)
            raise

    # --- Méthodes internes ---
    def _process_ass_line(self, line: str, old_font: str, new_font: str) -> str:
        """
        Traite une ligne du fichier ASS pour remplacer la police.
        Gère les lignes 'Style:' et les balises '\\fn'.

        Args:
            line (str): Ligne du fichier ASS.
            old_font (str): Police à remplacer.
            new_font (str): Nouvelle police.

        Returns:
            str: Ligne modifiée.
        """
        if line.startswith("Style:"):
            parts = line.split(',')
            if len(parts) > 1 and parts[1].strip() == old_font:
                parts[1] = f" {new_font}"
                return ','.join(parts)
        elif "\\fn" in line:
            return line.replace(f"\\fn{old_font}", f"\\fn{new_font}")
        return line

    def _verify_font_replacement(self, file_path: str, expected_font: str):
        """
        Vérifie que la police a bien été remplacée dans le fichier.

        Args:
            file_path (str): Chemin vers le fichier à vérifier.
            expected_font (str): Police attendue.

        Raises:
            ValueError: Si la police n'est pas trouvée dans le fichier.
        """
        with open(file_path, 'r', encoding='utf-8') as f_check:
            if expected_font not in f_check.read():
                raise ValueError("Échec du remplacement de police")

    def _cleanup_temp_file(self, temp_path: str):
        """
        Nettoie un fichier temporaire.

        Args:
            temp_path (str): Chemin vers le fichier temporaire.
        """
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"[AVERTISSEMENT] Échec du nettoyage du fichier temporaire : {e}")
