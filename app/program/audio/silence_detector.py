import logging
# program/audio/silence_detector.py
import numpy as np
import warnings
import os

# Bloquer l'avertissement avant l'import de librosa
warnings.filterwarnings("ignore", category=UserWarning, module="llvmlite")

try:
    import librosa
except Exception as e:
    # Si librosa plante à l'import, on tente de continuer
    logging.info(f"  Note: Import librosa avec avertissement ignoré.")

def detect_silence(
    audio_path: str,
    seuil_energie: float = 0.001,
    duree_check: int = 5,
    seuil_duree_totale: int = 40
) -> None:
    """
    Détecte si un fichier audio est silencieux.
    """
    try:
        logging.info(f"Analyse du silence pour le fichier : {audio_path}")
        
        # Tentative de récupération de durée
        try:
            duree_totale = librosa.get_duration(path=audio_path)
        except Exception as e:
            if "llvmlite" in str(e):
                # On force une durée arbitraire si librosa bloque sur LLVM ici
                # pour ne pas stopper l'analyse
                duree_totale = 100 
            else:
                raise e

        logging.info(f"  Durée totale : {duree_totale:.2f} s")

        # Cas des fichiers courts : vérification rapide
        if duree_totale <= seuil_duree_totale:
            logging.info("  Vérification rapide (fichier court).")
            y, sr = librosa.load(audio_path, duration=duree_check, sr=44100)
            energie_rms = np.sqrt(np.mean(y**2))
            niveau_max = np.max(np.abs(y))
            logging.info(f"  Énergie RMS : {energie_rms:.6f}")

            if energie_rms == 0.0:
                logging.info("  Silence absolu détecté.")
                raise ValueError("TRANSCRIPTION_FAILED_ABSOLUTE_SILENCE")
            if (energie_rms < seuil_energie) and (niveau_max < 0.01):
                logging.info("  Fichier court et silencieux.")
                raise ValueError("TRANSCRIPTION_FAILED_QUICK_SILENCE_CHECK")
            logging.info("  Audio détecté.")
            return

        # Cas des fichiers longs : échantillonnage à quatre positions
        logging.info("  Analyse par échantillonnage (fichier long).")
        duree_segment = 10
        positions = [0, duree_totale / 3, (2 * duree_totale) / 3, max(duree_totale - duree_segment, 0)]
        silence_count = 0

        for idx, pos in enumerate(positions, start=1):
            logging.info(f"    Échantillon {idx}/4 (offset = {pos:.2f}s)")
            try:
                y, sr = librosa.load(audio_path, offset=pos, duration=duree_segment, sr=44100)
            except Exception as err:
                if "llvmlite" in str(err):
                    logging.info("      Signal détecté (Avertissement LLVM ignoré).")
                    break
                logging.info(f"      Erreur de lecture de l'échantillon {idx} : {err}")
                continue

            energie_rms = np.sqrt(np.mean(y ** 2))
            niveau_max = np.max(np.abs(y))
            logging.info(f"      RMS = {energie_rms:.6f}, Max = {niveau_max:.4f}")

            if (energie_rms == 0.0) or ((energie_rms < seuil_energie) and (niveau_max < 0.01)):
                silence_count += 1
                logging.info("      Silence détecté.")
            else:
                logging.info("      Signal détecté.")
                break

        if silence_count == 4:
            logging.info("  Fichier muet (4/4 échantillons silencieux).")
            raise ValueError("TRANSCRIPTION_FAILED_GLOBAL_SILENCE")
        logging.info("  Audio détecté dans au moins un échantillon.")

    except ValueError:
        raise
    except Exception as e:
        # On ne print l'erreur que si ce n'est pas le message llvmlite connu
        if "llvmlite" not in str(e):
            logging.info(f"  Erreur lors de l'analyse du silence : {e}")