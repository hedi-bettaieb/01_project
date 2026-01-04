import logging
#program/subtitle/generateur_ass.py 
import os
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from PyQt6.QtGui import QColor
from program.preferences.user_preferences import UserPreferences
from program.utils.paths import PathManager


class GenerateurASS:
    """
    Génère et met à jour un fichier de sous-titres .ass avec gestion complète des couleurs et accessibilité
    """
    def __init__(self, modele="small" , user_preferences: UserPreferences = None):
        """
        Si `modele` est déjà une instance de WhisperModel, on la garde.
        Sinon, on la charge via whisper.load_model(modele).
        """
        from faster_whisper import WhisperModel

        if isinstance(modele, WhisperModel):
            logging.info("🧠 Modèle déjà en mémoire, utilisation directe.")
            self.modele = modele
        else:
            logging.info(f"🧠 Chargement du modèle Whisper '{modele}'...")
            self.modele = whisper.load_model(modele)

        self.paths = PathManager()


        # ✅ Stocker l'instance reçue
        if user_preferences is None:
            raise ValueError("GenerateurASS requiert une instance de UserPreferences pour la configuration du style.")
        self.user_preferences = user_preferences # <-- AJOUTÉ


    def generer(self, audio_path: str, ass_path: str) -> bool:
        """
        Transcrit automatiquement l'audio en texte, et génère un fichier ASS.
        """
        if not os.path.exists(audio_path):
            logging.info(f"❌ Fichier audio introuvable : {audio_path}")
            return False

        try:
            logging.info("🎙️ Transcription audio avec Whisper...")
            # ✅ faster_whisper retourne un tuple (segments, info)
            segments, info = self.modele.transcribe(audio_path, task="transcribe")
            
            # ✅ Convertir le générateur en liste
            segments = list(segments)
            
        except Exception as e:
            logging.info("❌ Erreur Whisper :", e)
            import traceback
            traceback.print_exc()
            return False

        if not segments:
            logging.info("❌ Aucun segment détecté.")
            raise ValueError("TRANSCRIPTION_FAILED_NO_SPEECH") 
        
        # VÉRIFICATION DE LA QUALITÉ ET DE L'HALLUCINATION
        
        # 1. Vérification du texte total généré
        texte_total = "".join([s.text.strip() for s in segments])
        
        # S'il y a des segments mais très peu de texte réellement transcrit (ex: moins de 5 caractères par minute de vidéo)
        # On peut aussi vérifier si le texte est principalement composé de bruit ou de caractères étranges.
        
        # 2. Vérification de la langue détectée (souvent un bon indicateur d'hallucination)
        langue_detectee = info.language
        
        # Considérez 'nn' (nynorsk) comme une langue suspecte si non attendue
        # Si la langue détectée est trop faible OU si le texte total est très court
        
        # Pour le test d'hallucination/silence, on vérifie si la transcription génère des segments 
        # qui sont presque entièrement du bruit (comme votre exemple)
        
        # --- LOGIQUE D'ÉCHEC DE LA TRANSCRIPTION ---
        # Si le texte total est très court (moins de 10 caractères au total)
        if len(texte_total) < 10:
             logging.info("❌ Transcription suspecte : Texte total généré trop court.")
             return False

        # Si la probabilité de non-discours est élevée (disponible dans le segment, mais plus complexe)
        # OU Si la langue détectée est une langue 'bruit' (ex: nn, 'unk' si utilisé, ou si la confiance est trop basse)
        # Pour rester simple, nous allons ajouter une vérification de la longueur minimale.
        
        # ⚠️ Pour reproduire l'échec voulu :
        # Le Worker doit vérifier le statut retourné. 
        # Si la chaîne atteint l'écriture du fichier ASS, l'échec n'est plus possible ici.
        
        # La seule façon de forcer l'échec est d'échouer AVANT l'écriture.
        
        # On peut simuler l'échec de la transcription si on considère que cette langue suspecte doit être un échec.
        if langue_detectee in ('nn', 'unk'): # 'unk' est parfois retourné pour l'inconnu
            logging.info(f"❌ Langue détectée suspecte ({langue_detectee}). Considéré comme échec de transcription.")
            return False
        
        
        style_config = self.get_style_config()

        def ass_time(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            cs = int((t - int(t)) * 100)
            return f"{h:01}:{m:02}:{s:02}.{cs:02}"

        try:
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write("[Script Info]\n")
                f.write("Title: Sous-titres générés automatiquement\n")
                f.write("ScriptType: v4.00+\n")
                f.write("WrapStyle: 0\n")
                f.write("ScaledBorderAndShadow: yes\n")
                f.write("YCbCr Matrix: TV.601\n")
                f.write("PlayResX: 1920\n")
                f.write("PlayResY: 1080\n\n")
                f.write(f"Language: {info.language}\n\n") 
                
                f.write("[V4+ Styles]\n")
                f.write(
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                )
                f.write(
                    f"Style: Default,{style_config['font_name']},{style_config['font_size']}," 
                    f"{style_config['primary_color']},{style_config['secondary_color']}," 
                    f"{style_config['outline_color']},{style_config['back_color']},0,0,0,0,100,100,0,0,1," 
                    f"{style_config['outline']},{style_config['shadow']},{style_config['alignment']}," 
                    f"10,10,{style_config['margin_v']},1\n\n"
                )

                f.write("[Events]\n")
                f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

                # ✅ Les segments sont des objets avec des attributs, pas des dictionnaires
                for segment in segments:
                    debut = ass_time(segment.start)
                    fin = ass_time(segment.end)
                    texte = segment.text.strip()
                    texte = texte.replace("{", "\\{").replace("}", "\\}")
                    f.write(f"Dialogue: 0,{debut},{fin},Default,,0,0,0,,{texte}\n")

        except Exception as e:
            logging.info("❌ Erreur lors de l'écriture du fichier ASS :", e)
            import traceback
            traceback.print_exc()
            return False

        # 🔥 Message informatif sur le mode utilisé
        mode = "haute visibilité" if style_config['accessibilite'] else "standard"
        logging.info(f"✅ Sous-titres ASS enregistrés dans : {ass_path}")
        logging.info(f"🌍 Langue détectée : {info.language}")  # ✅ Utiliser info.language
        logging.info(f"👁️ Mode d'affichage : {mode}")
        
        return True


    

    @staticmethod
    def couleur_nom_vers_ass(nom_couleur):
        """Convertit les noms de couleurs en format ASS. 100% synchronisé avec l'interface."""
        conversion = {
            # Couleurs de base
            "black": "&H00000000",
            "white": "&H00FFFFFF",
            "red": "&H000000FF",
            "green": "&H0000FF00",
            "blue": "&H00FF0000",
            "yellow": "&H0000FFFF",

            # Autres couleurs 
            "magenta": "&H00FF00FF",
            "cyan": "&H00FFFF00",
            "orange": "&H0000A5FF",
            "purple": "&H00800080",
            "pink": "&H00FFC0CB",
            "hotpink": "&H00B469FF",
            "brown": "&H002A2AA5",
            "gray": "&H00808080"
        }

        couleur_ass = conversion.get(nom_couleur.lower(), "&H00FFFFFF")

        if couleur_ass == "&H00FFFFFF" and nom_couleur.lower() not in conversion:
            logging.info(f"⚠ Attention : couleur '{nom_couleur}' non reconnue. Utilisation du blanc.")

        return couleur_ass

    def get_style_config(self):
        """
        Récupère la config avec gestion de l'accessibilité
        """
        prefs = self.user_preferences
        try:
                
            logging.info(f"[DEBUG] get_style_config() - police préférée: {prefs.get('police', 'Amiri.ttf')}")
            logging.info(f"[DEBUG] get_style_config() - langue config: {prefs.config.get('langue', 'English')}")
            
            police_nom_complet = prefs.get("police", "Amiri.ttf")
            logging.info(f"[DEBUG] police_nom_complet: {police_nom_complet}")
            
            police_chemin = prefs.get_police_path(police_nom_complet)
            logging.info(f"[DEBUG] police_chemin retourné: {police_chemin}")
            
            police_path = self.paths.get_path(police_chemin)
            logging.info(f"[DEBUG] police_path résolu: {police_path}")


                
                        # 1. Utiliser le get_police_path du UserPreferences pour garantir la cohérence:
            police_nom_complet = prefs.get("police", "Amiri.ttf")
            police_chemin = prefs.get_police_path(police_nom_complet) # Cette méthode est propre et gère les erreurs.
            police_path = self.paths.get_path(police_chemin)

            


        #Utiliser prefs.get() qui gère déjà les valeurs par défaut
            accessibilite = prefs.get("accessibilite")  
            opacite = prefs.get("opacite_fond")         
            epaisseur_bordure = prefs.get("epaisseur_bordure")
            
            # 🔥 Adapter la configuration selon le mode
            if accessibilite:
                # Mode accessibilité : fond semi-transparent réglable + bordure épaisse
                opacity_hex = f"{int(255 * opacite / 100):02X}"
                back_color = f"&H{opacity_hex}000000"  
                outline = epaisseur_bordure
                shadow = epaisseur_bordure + 1  
            else:
                # Mode normal
                back_color = "&H80000000"  
                outline = 2
                shadow = 2
            
            return {
                "font_name": police_path.stem,
                "font_size": prefs.get("taille_police", 36),
                "primary_color": self.couleur_nom_vers_ass(prefs.get("couleur", "white")),
                "secondary_color": "&H000000FF",  
                "outline_color": "&H00000000",    # Noir 
                "back_color": back_color,         # 🔥 Adapté selon le mode
                "outline": outline,               # 🔥 Adapté selon le mode
                "shadow": shadow,                 # 🔥 Adapté selon le mode
                "alignment": 2,
                "margin_v": 20,
                "accessibilite": accessibilite    # 🔥 Pour information
            }
        except Exception as e:
            logging.info(f"❌ Erreur configuration dans get_style_config(): {e}")
            import traceback
            traceback.print_exc()  # Affiche la stack trace complète
            return self.get_style_config_default()


    
    def get_style_config_default(self):
        """Config par défaut si erreur"""
        return {
            "font_name": "DejaVuSans",
            "font_size": 42,
            "primary_color": "&H00FFFFFF",  # Blanc
            "secondary_color": "&H000000FF",
            "outline_color": "&H00000000",
            "back_color": "&H80000000",     # Semi-transparent normal
            "outline": 2,
            "shadow": 2,
            "alignment": 2,
            "margin_v": 20,
            "accessibilite": False
        }

    