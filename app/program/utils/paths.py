#projet/app/program/utils/paths.py
import yaml
import sys
import os
import shutil
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Any

# Verrou pour assurer la sécurité des opérations de copie dans un contexte multi-thread
copy_lock = Lock()

class PathManager:
    """
    Gère les chemins du projet de manière centralisée.
    Supporte les modes développement et production (exécutable/portable).
    Gère la synchronisation des ressources vers AppData en mode production.
    """
    _instance = None
    _is_initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PathManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_filepath: str = "ressources/configuration/config.yaml"):
        """
        Initialise le gestionnaire de chemins.
        """
        if PathManager._is_initialized:
            return 
        
        with copy_lock:
            if PathManager._is_initialized:
                return 
            
            self._initialize_once(config_filepath)
            PathManager._is_initialized = True
            
    def _initialize_once(self, config_filepath: str):
        """Initialisation interne unique des attributs et dossiers."""
        self.project_root = self._find_project_root()
        
        # 1. Charger la configuration YAML de base
        install_config = self.project_root / config_filepath
        if not install_config.exists():
            install_config = self.project_root / "app" / config_filepath

        self.config_data = self._load_initial_config(install_config)
        
        # Récupération des noms de dossiers et projet depuis la config
        self.project_name = self.config_data.get("project_name", "Easy_Subtitle_Creator_V1.0.0")
        self.data_folder_name = self.config_data.get("data_folder_name", "ressources")
        
        # 2. Détecter le mode d'exécution
        executable_path = sys.executable.lower()
        if "program files" in executable_path or "appdata" in executable_path:
            self.execution_mode = "production"
        else:
            self.execution_mode = "development"

        # 3. Définir le dossier utilisateur (AppData)
        self.user_dir = Path(os.environ["APPDATA"]) / self.project_name
        
        # 4. Centralisation des Logs
        self.logs_dir = self.user_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 5. Préparer/Synchroniser les ressources si on est en mode production
        if self.execution_mode == "production":
            self._prepare_user_resources()

    def _find_project_root(self) -> Path:
        """Détermine la racine du projet selon le contexte d'exécution."""
        executable_path = sys.executable.lower()
        if "python_env" in executable_path or "python-portable" in executable_path:
            return Path(sys.executable).parent.parent
        return Path(__file__).resolve().parents[2]

    def _load_initial_config(self, path: Path) -> Dict[str, Any]:
        """Charge le fichier YAML de configuration initiale."""
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            logging.error(f"Erreur chargement config YAML : {e}")
            return {}

    def _prepare_user_resources(self):
        """Synchronise les ressources vers AppData en mode production."""
        source = self.project_root / self.data_folder_name
        if not source.exists():
            source = self.project_root / "app" / self.data_folder_name
            
        dest = self.user_dir / self.data_folder_name
        
        version_filename = self.config_data.get("version_file", "version.txt")
        src_version_file = source / version_filename
        dst_version_file = dest / version_filename

        try:
            source_version = src_version_file.read_text().strip() if src_version_file.exists() else "0"
            dest_version = dst_version_file.read_text().strip() if dst_version_file.exists() else "0"

            if not dest.exists() or source_version > dest_version:
                if dest.exists():
                    shutil.rmtree(dest)
                
                dest.mkdir(parents=True, exist_ok=True)
                
                for item in source.glob("**/*"):
                    rel_path = item.relative_to(source)
                    target_path = dest / rel_path
                    if item.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target_path)
        except Exception as e:
            logging.error(f"Erreur lors de la préparation des ressources : {e}")

    def get_path(self, relative_path: str) -> Path:
        """Résout un chemin de fichier de manière dynamique."""
        parts = Path(relative_path).parts
        if self.execution_mode == "production" and parts and parts[0] == self.data_folder_name:
            return self.user_dir / relative_path
        path = self.project_root / relative_path
        if not path.exists():
            alt_path = self.project_root / "app" / relative_path
            if alt_path.exists():
                return alt_path
        return path

    def get_project_root(self) -> Path:
        return self.project_root

    def get_user_data_dir(self) -> Path:
        return self.user_dir

    def get_logs_dir(self) -> Path:
        """Retourne le chemin du dossier de logs dans AppData."""
        return self.logs_dir

