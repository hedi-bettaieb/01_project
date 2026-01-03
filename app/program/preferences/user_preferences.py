# program.preferences/user_preferences.py 
import json
import os
from pathlib import Path
import pycountry
from program.fonts.font_manager import FontManager
from program.utils.paths import PathManager
from program.preferences.language_manager import LanguageManager


class UserPreferences:
    """
    Gère les préférences utilisateur de manière persistante (lecture/écriture dans config.json).
    Cette classe ne gère AUCUNE logique d'interface utilisateur (UI).
    """

    # Valeurs par défaut pour éviter la redondance dans le code
    VALEURS_DEFAUT = {
        "taille_police": 36,
        "couleur": "white",
        "langue" : "English",  
        "accessibilite": False,
        "opacite_fond": 70,
        "epaisseur_bordure": 3
    }

    def __init__(self, font_manager: FontManager):
        """
        Initialise les chemins, charge la configuration et les gestionnaires nécessaires.

        Args:
            font_manager (FontManager): Instance de FontManager pour accéder aux polices.
        """
        self.paths = PathManager()
        self.chemin_config = self.paths.get_path("ressources/configuration/config.json")
        chemin_languages = self.paths.get_path("ressources/languages/languages.json")
        self.language_manager = LanguageManager(languages_file_path=chemin_languages)
        self.font_manager = font_manager  # Injection de dépendance

        # Vérification et chargement initial de la configuration
        if not self.chemin_config.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable : {self.chemin_config}")

        with open(self.chemin_config, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get_language_code(self, language_name: str) -> str:
        """
        Retourne le code ISO-639-2 (ex: 'ara', 'fre') à partir du nom de la langue (ex: 'Arabic', 'French').
        Utilise LanguageManager pour la conversion.

        Args:
            language_name (str): Nom complet de la langue.

        Returns:
            str: Code ISO-639-2 ou 'und' si non trouvé.
        """
        code = self.language_manager.get_code(language_name, code_type='iso639_2')
        return code if code else "und"
    def sauvegarder_preferences(self):
        """Sauvegarde la configuration actuelle dans le fichier JSON (AppData via PathManager)."""
        try:
            # Assurez-vous que le dossier parent existe (AppData/Easy_Subtitle...)
            os.makedirs(os.path.dirname(self.chemin_config), exist_ok=True)
            with open(self.chemin_config, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except PermissionError:
            print(f"[Erreur] Impossible d'écrire dans {self.chemin_config}. Vérifiez PathManager.")


    def update_config_from_ui(self, collected_data: dict):
        """
        Met à jour la configuration interne à partir des données de l'UI.
        Ajoute l'extension '.ttf' au nom de la police si nécessaire.

        Args:
            collected_data (dict): Données collectées depuis l'UI.
        """
        if "police" in collected_data and not str(collected_data["police"]).endswith(".ttf"):
            police_nom = collected_data.pop("police")
            collected_data["police"] = f"{police_nom}.ttf"

        self.config.update(collected_data)
        self.sauvegarder_preferences()

    def get(self, cle, default=None):
        """
        Retourne une préférence avec une valeur par défaut si la clé n'existe pas.

        Args:
            cle (str): Clé de la préférence.
            default: Valeur par défaut si la clé n'existe pas.

        Returns:
            Valeur associée à la clé ou valeur par défaut.
        """
        return self.config.get(cle, self.VALEURS_DEFAUT.get(cle, default))


    def get_police_path(self, police_nom: str, folder_name: str = None) -> str:
        """
        Retourne le chemin complet de la police choisie.
        
        Args:
            police_nom (str): Nom de la police (avec ou sans extension).
            folder_name (str, optional): Dossier spécifique, sinon auto-détecté.

        Returns:
            str: Chemin absolu vers la police.

        Raises:
            ValueError: Si la police est introuvable.
        """
        nom_sans_ext = Path(police_nom).stem
        # Utiliser le folder_name fourni ou le détecter automatiquement
        target_folder = folder_name if folder_name else self._get_active_folder_name()
        chemin = self.font_manager.get_font_path(nom_sans_ext, target_folder)

        if chemin is None or not chemin.exists():
            raise ValueError(f"Police '{nom_sans_ext}' introuvable dans le registre '{target_folder}'.")
        return str(chemin)
    
    
    def valider_configuration(self, detected_language: str = None):
        """
        Valide la configuration avec option pour langue détectée.
        
        Args:
            detected_language (str, optional): Code langue détecté du ASS

        Returns:
            dict: Configuration validée.

        Raises:
            ValueError: Si la police ou la taille est invalide.
            FileNotFoundError: Si la police est introuvable.
        """
        # Assurer que les préférences sont à jour AVANT de lire la police
        self.recharger_preferences() 

        try:
            police_nom = self.config.get("police", "Amiri.ttf")
            folder_name = self._get_active_folder_name(detected_language)
            police_chemin = self.get_police_path(police_nom, folder_name)
            
            if not Path(police_chemin).exists():
                raise FileNotFoundError(f"Police '{police_nom}' introuvable : {police_chemin}")

            taille = self.get("taille_police")
            if not isinstance(taille, int) or taille < 8 or taille > 200:
                raise ValueError(f"Taille de police invalide : {taille}")

            langue_nom_complet = self.get("langue", "English")
            return {
                "language": self.get_language_code(langue_nom_complet),
                "langue": langue_nom_complet,
                "police_chemin": police_chemin,
                "taille_police": taille,
                "couleur": self.get("couleur"),
                "accessibilite": self.get("accessibilite"),
                "opacite_fond": self.get("opacite_fond"),
                "epaisseur_bordure": self.get("epaisseur_bordure"),
            }


            print(f"[DEBUG] Registre complet: {self.font_registry.registry}")
            print(f"[DEBUG] Dossier cherché: {folder_name}")
            print(f"[DEBUG] Police cherchée: {police_nom}")

            
        except ValueError as e:
            # Erreur de police introuvable ou paramètre invalide
            print(f"❌ Erreur de validation (ValueError): {e}")
            raise
        except FileNotFoundError as e:
            # Erreur de fichier police non trouvé
            print(f"❌ Erreur de validation (FileNotFoundError): {e}")
            raise
        except Exception as e:
            # Erreur inattendue
            print(f"❌ Erreur inattendue lors de la validation: {e}")
            raise ValueError(f"Erreur de configuration: {str(e)}")


    def recharger_preferences(self):
        """Recharge la configuration depuis le fichier config.json."""
        print("🔄 Rechargement de la configuration utilisateur depuis le disque...")
        try:
            with open(self.chemin_config, "r", encoding="utf-8") as f:
                self.config = json.load(f)
                print("Configuration rechargée :", self.config)
        except Exception as e:
            print(f"❌ Erreur lors du rechargement des préférences : {e}")
            # En cas d'échec, réinitialise avec les valeurs par défaut
            self.config = self.VALEURS_DEFAUT.copy()

    
    def _get_active_folder_name(self, detected_language: str = None) -> str:
        """
        Déduit le nom du dossier des polices ('arabic_fonts' ou 'latin_fonts'), 
        en priorisant la langue détectée du fichier ASS.
        """
        # PRIORITÉ 1 : Langue détectée par le fichier ASS (PRIME TOUT)
        if detected_language:
            if detected_language.startswith('ar'):
                 return "arabic_fonts"
            # Si la langue est détectée et n'est PAS arabe (ex: 'en', 'fr', etc.), c'est latin.
            return "latin_fonts" 
        
        # PRIORITÉ 2 : Langue configurée (uniquement si aucune langue ASS n'a été détectée)
        langue_config_name = self.config.get("langue", "English").strip().lower()
        
        # Utilisation de la langue configurée uniquement si la Priorité 1 n'a pas été déclenchée.
        if langue_config_name == 'arabic':
             return "arabic_fonts"
        
        # Par défaut (toute autre langue configurée, ou défaut 'English')
        return "latin_fonts"

    