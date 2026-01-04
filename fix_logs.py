#Voici un script Python qui va parcourir tous vos fichiers, ajouter l'import `logging` et remplacer les `print` par `logging` intelligemment (error pour les exceptions, info pour le reste).
#1. Créez un fichier `fix_logs.py` dans votre dossier.
import os
import re

def transform_code(content):
    if "import logging" not in content:
        content = "import logging\n" + content
    
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if "print(" in line:
            if any(err in line.lower() for err in ["error", "fail", "exception", "wrong"]):
                line = line.replace("print(", "logging.error(")
            else:
                line = line.replace("print(", "logging.info(")
        new_lines.append(line)
    return "\n".join(new_lines)

for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py") and file != "fix_logs.py":
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
            with open(path, 'w', encoding='utf-8') as f:
                f.write(transform_code(data))
#3. Dans votre terminal, tapez : `python fix_logs.py`
#4. Tapez ensuite : `git add .`
#5. Tapez : `git commit -m "Migration print vers logging"`
#6. Tapez : `git push`

