#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Serveur OAuth LinkedIn - Simplifié
Lance ce serveur, obtient le token, puis publie automatiquement
"""

from flask import Flask, request, redirect
import requests
import webbrowser
import threading
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Credentials
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

# Chemin local des tokens (hors Git)
TOKENS_PATH = os.getenv(
    "LINKEDIN_TOKENS_PATH",
    os.path.join(os.path.dirname(__file__), "data", "linkedin_tokens.json"),
)

# Variables globales pour stocker le token
access_token = None
server_running = True

@app.route('/linkedin/login')
def linkedin_login():
    """Redirige vers LinkedIn pour autorisation"""
    # Scopes OpenID + publication
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid%20profile%20w_member_social"
    )
    return redirect(auth_url)

@app.route('/linkedin/callback')
def linkedin_callback():
    """Reçoit le code et échange contre un token"""
    global access_token, server_running
    
    code = request.args.get('code')
    
    if not code:
        return "❌ Erreur: Aucun code reçu", 400
    
    # Échanger le code contre un token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        token_data = response.json()
        
        if 'access_token' in token_data:
            access_token = token_data['access_token']
            
            # Sauvegarder le token
            save_token(access_token)
            
            # Arrêter le serveur
            server_running = False
            
            return """
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authentification réussie !</h1>
                <p>Token LinkedIn obtenu et sauvegardé.</p>
                <p><strong>Vous pouvez fermer cette fenêtre et retourner au bot.</strong></p>
                <p>La publication LinkedIn sera désormais AUTOMATIQUE ! 🚀</p>
            </body>
            </html>
            """
        else:
            return f"❌ Erreur lors de l'obtention du token: {token_data}", 400
    
    except Exception as e:
        return f"❌ Erreur: {str(e)}", 500

def save_token(token):
    """Sauvegarde le token dans un fichier local (hors Git)."""
    try:
        os.makedirs(os.path.dirname(TOKENS_PATH), exist_ok=True)
        with open(TOKENS_PATH, "w", encoding="utf-8") as f:
            json.dump({"access_token": token}, f, ensure_ascii=False, indent=2)
        print("✅ Token sauvegardé localement")
    except Exception as e:
        print(f"⚠️ Erreur lors de la sauvegarde: {e}")

def run_server():
    """Lance le serveur Flask"""
    app.run(port=8501, debug=False, use_reloader=False)

def get_linkedin_token():
    """Processus complet pour obtenir un token LinkedIn"""
    print("\n" + "="*80)
    print("🔗 AUTHENTIFICATION LINKEDIN OAUTH")
    print("="*80 + "\n")
    
    print("1️⃣ Lancement du serveur local sur http://localhost:8501...")
    
    # Lancer le serveur dans un thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    
    print("2️⃣ Ouverture du navigateur pour authentification LinkedIn...")
    print()
    
    # Ouvrir le navigateur
    webbrowser.open('http://localhost:8501/linkedin/login')
    
    print("👉 Connectez-vous à LinkedIn et autorisez Smart-Hire")
    print("   (Le navigateur s'ouvre automatiquement)")
    print()
    
    # Attendre que le token soit obtenu
    print("⏳ En attente de l'autorisation...")
    
    timeout = 120  # 2 minutes
    start = time.time()
    
    while access_token is None and time.time() - start < timeout:
        time.sleep(1)
    
    if access_token:
        print()
        print("=" * 80)
        print("✅ TOKEN LINKEDIN OBTENU ET SAUVEGARDÉ !")
        print("=" * 80)
        print()
        print("La publication LinkedIn est maintenant AUTOMATIQUE ! 🚀")
        print()
        print("Redémarrez le bot et testez :")
        print("  1. Recherche sans résultats")
        print("  2. Clic 'Publier sur LinkedIn'")
        print("  3. Post publié AUTOMATIQUEMENT !")
        print()
        return access_token
    else:
        print()
        print("❌ Timeout - Aucune autorisation reçue")
        print("   Réessayez en lançant : python linkedin_get_token.py")
        return None

if __name__ == "__main__":
    token = get_linkedin_token()
    
    if token:
        print(f"Token : {token[:30]}...")
