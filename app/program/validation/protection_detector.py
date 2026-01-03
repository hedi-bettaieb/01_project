import os
import stat
from pathlib import Path

class ProtectionDetector:

    # --- Détection EFS via attribut NTFS ---
    def _is_encrypted_efs(self, filepath):
        try:
            attrs = os.stat(filepath).st_file_attributes
            return bool(attrs & stat.FILE_ATTRIBUTE_ENCRYPTED)
        except Exception:
            return False

    # --- Vérification accès fichier ---
    def _check_file_access(self, filepath):
        try:
            with open(filepath, 'r+', encoding='utf-8'):
                pass
            return "accessible"
        except PermissionError:
            return "protected"
        except Exception:
            return "protected"

    # --- Vérification dossier parent ---
    def _check_folder_access(self, folderpath):
        try:
            testfile = os.path.join(folderpath, "~testfile.tmp")
            with open(testfile, 'w') as f:
                f.write("test")
            os.remove(testfile)
            return "accessible"
        except PermissionError:
            return "protected"
        except:
            return "protected"

    # --- Vérification principale ---
    def check(self, target_path):
        path = Path(target_path)

        if not path.exists():
            return "🔍 Erreur: Chemin introuvable"

        if path.is_file():

            # 🔐 Étape 1 : Détection EFS
            if self._is_encrypted_efs(path):
                return "🔒 Fichier chiffré EFS — modification impossible"

            # 🔐 Étape 2 : Vérification du dossier parent
            parent_status = self._check_folder_access(path.parent)
            if parent_status == "protected":
                return "🔒 Dossier parent protégé — modification impossible"

            # 🔐 Étape 3 : Vérification du fichier
            file_status = self._check_file_access(path)
            if file_status == "protected":
                return "🔒 Fichier protégé ou utilisé — modification impossible"

            return "🔓 Fichier accessible"

        # Cas dossier
        dir_status = self._check_folder_access(path)
        if dir_status == "protected":
            return "🔒 Dossier protégé — modification impossible"

        return "🔓 Dossier accessible"
