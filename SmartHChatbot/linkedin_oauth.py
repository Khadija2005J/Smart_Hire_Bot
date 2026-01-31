#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestion de l'authentification OAuth LinkedIn
Permet la publication automatique sur LinkedIn
"""

import requests
import json
import webbrowser
from typing import Dict, Optional
from datetime import datetime, timedelta
import os

try:
    from linkedin_config import LINKEDIN_CONFIG
except ImportError:
    LINKEDIN_CONFIG = {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://localhost:8000/callback",
        "access_token": None,
        "refresh_token": None,
        "token_expiry": None,
    }

TOKENS_PATH = os.getenv(
    "LINKEDIN_TOKENS_PATH",
    os.path.join(os.path.dirname(__file__), "data", "linkedin_tokens.json"),
)


def _load_tokens_from_file() -> Dict[str, Optional[str]]:
    """Charge les tokens depuis un fichier local (hors Git)."""
    try:
        if os.path.exists(TOKENS_PATH):
            with open(TOKENS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "token_expiry": data.get("token_expiry"),
            }
    except Exception as e:
        print(f"⚠️ Erreur chargement tokens LinkedIn: {e}")
    return {
        "access_token": None,
        "refresh_token": None,
        "token_expiry": None,
    }


def _save_tokens_to_file(access_token: str, refresh_token: Optional[str], token_expiry: str) -> None:
    """Sauvegarde les tokens dans un fichier local (hors Git)."""
    try:
        os.makedirs(os.path.dirname(TOKENS_PATH), exist_ok=True)
        with open(TOKENS_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expiry": token_expiry,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print("✅ Tokens LinkedIn sauvegardés localement")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde tokens LinkedIn: {e}")


class LinkedInOAuth:
    """
    Gère l'authentification OAuth2 avec LinkedIn
    """
    
    def __init__(self):
        self.client_id = LINKEDIN_CONFIG.get('client_id', '')
        self.client_secret = LINKEDIN_CONFIG.get('client_secret', '')
        self.redirect_uri = LINKEDIN_CONFIG.get('redirect_uri', '')
        self.access_token = LINKEDIN_CONFIG.get('access_token')
        self.refresh_token = LINKEDIN_CONFIG.get('refresh_token')
        self.token_expiry = LINKEDIN_CONFIG.get('token_expiry')

        # Charger les tokens depuis un fichier local, si disponible
        file_tokens = _load_tokens_from_file()
        self.access_token = file_tokens.get("access_token") or self.access_token
        self.refresh_token = file_tokens.get("refresh_token") or self.refresh_token
        self.token_expiry = file_tokens.get("token_expiry") or self.token_expiry
        
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.api_base = "https://api.linkedin.com/v2"
    
    def is_configured(self) -> bool:
        """Vérifie si les credentials sont configurés"""
        return bool(self.client_id and self.client_secret)
    
    def is_authenticated(self) -> bool:
        """Vérifie si nous avons un token valide"""
        if not self.access_token:
            return False
        
        # Vérifier l'expiration
        if self.token_expiry:
            try:
                expiry = datetime.fromisoformat(self.token_expiry)
                if datetime.now() >= expiry:
                    print("⚠️ Token LinkedIn expiré, tentative de refresh...")
                    return self.refresh_access_token()
            except:
                pass
        
        return True
    
    def get_auth_url(self) -> str:
        """Génère l'URL pour l'authentification LinkedIn"""
        # Utilise OpenID Connect pour récupérer l'identité sans r_liteprofile
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid profile w_member_social'
        }
        
        from urllib.parse import urlencode
        return f"{self.auth_url}?{urlencode(params)}"
    
    def get_access_token(self, auth_code: str) -> bool:
        """
        Échange le code d'authentification contre un token d'accès
        
        Args:
            auth_code: Code reçu de LinkedIn après autorisation
        
        Returns:
            True si succès, False sinon
        """
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(self.token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                self.refresh_token = result.get('refresh_token')
                
                # Calculer l'expiration (généralement 60 jours)
                expires_in = result.get('expires_in', 5184000)  # 60 jours par défaut
                expiry = datetime.now() + timedelta(seconds=expires_in)
                self.token_expiry = expiry.isoformat()
                
                # Sauvegarder localement
                _save_tokens_to_file(self.access_token, self.refresh_token, self.token_expiry)
                
                print("✅ Authentification LinkedIn réussie !")
                return True
            else:
                print(f"❌ Erreur lors de l'authentification : {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Erreur lors de l'échange du code : {str(e)}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Rafraîchit le token d'accès expiré"""
        if not self.refresh_token:
            print("⚠️ Aucun refresh token disponible")
            return False
        
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(self.token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                self.refresh_token = result.get('refresh_token', self.refresh_token)
                
                expires_in = result.get('expires_in', 5184000)
                expiry = datetime.now() + timedelta(seconds=expires_in)
                self.token_expiry = expiry.isoformat()
                
                _save_tokens_to_file(self.access_token, self.refresh_token, self.token_expiry)
                print("✅ Token LinkedIn rafraîchi")
                return True
            else:
                print(f"❌ Erreur lors du refresh : {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Erreur lors du refresh : {str(e)}")
            return False
    
    def _save_tokens(self):
        """Compatibilité: sauvegarde locale des tokens."""
        _save_tokens_to_file(self.access_token, self.refresh_token, self.token_expiry)
    
    def publish_post(self, post_content: str) -> Dict:
        """
        Publie un post sur LinkedIn
        
        Args:
            post_content: Contenu du post
        
        Returns:
            Dict avec statut et détails
        """
        if not self.is_authenticated():
            return {
                'success': False,
                'message': 'Non authentifié. Veuillez d\'abord configurer OAuth.'
            }
        
        try:
            # Obtenir l'ID utilisateur via OpenID userinfo (scopes openid profile)
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            user_response = requests.get(
                'https://api.linkedin.com/v2/userinfo',
                headers=headers,
                timeout=10
            )
            if user_response.status_code != 200:
                return {
                    'success': False,
                    'message': f"Erreur lors de la récupération de l'ID utilisateur : {user_response.text}"
                }
            user_id = user_response.json().get('sub')

            author_urn = f"urn:li:person:{user_id}"

            # Construire le post UGC (ShareContent)
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Publier
            post_response = requests.post(
                f'{self.api_base}/ugcPosts',
                json=post_data,
                headers=headers,
                timeout=10
            )
            
            if post_response.status_code in [200, 201]:
                post_id = post_response.json().get('id', 'unknown')
                return {
                    'success': True,
                    'message': f'Post publié avec succès sur LinkedIn (ID: {post_id})',
                    'post_id': post_id
                }
            else:
                return {
                    'success': False,
                    'message': f'Erreur lors de la publication : {post_response.text}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la publication : {str(e)}'
            }


# Instance globale
linkedin_oauth = LinkedInOAuth()
