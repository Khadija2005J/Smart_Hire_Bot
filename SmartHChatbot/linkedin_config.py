"""
Configuration LinkedIn OAuth (sans secrets en clair).
Les variables sont chargées depuis .env.
Les tokens OAuth sont sauvegardés localement (hors Git).
"""

import os
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_CONFIG = {
    # Credentials LinkedIn Developer (dans .env)
    "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
    "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
    "redirect_uri": os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8501/linkedin/callback"),

    # Tokens (chargés depuis un fichier local, pas depuis Git)
    "access_token": None,
    "refresh_token": None,
    "token_expiry": None,
}

# Instructions :
# 1. Aller sur https://www.linkedin.com/developers/apps
# 2. Créer une nouvelle application
# 3. Dans "Auth", copier "Client ID" → .env
# 4. Dans "Auth", copier "Client Secret" → .env
# 5. Dans "Auth", ajouter redirect URI : http://localhost:8501/linkedin/callback
# 6. Lancer l'auth OAuth pour générer les tokens (stockés hors Git)
