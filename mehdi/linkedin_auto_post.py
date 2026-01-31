"""
Module de publication automatique LinkedIn
Crée automatiquement un post LinkedIn quand aucun candidat n'est trouvé
"""

import requests
import json
from typing import Dict, Optional, List
from datetime import datetime
import re


def _parse_request(job_description: str) -> Dict:
    """Analyse simple de la requête pour extraire le rôle, l'expérience et les compétences."""
    text = job_description.lower()
    # Rôle
    role_map = {
        'medecin cardiovasculaire': ['medecin cardiovasculaire', 'médecin cardiovasculaire', 'cardiologue', 'cardiologie', 'cardio'],
        'developpeur java': ['developpeur java', 'développeur java', 'java developer', 'ingenieur java', 'ingénieur java']
    }
    role_found = None
    for role, terms in role_map.items():
        if any(t in text for t in terms):
            role_found = role
            break

    # Expérience minimale
    exp = 0
    m = re.search(r'(\d+)\s*ans', text)
    if m:
        try:
            exp = int(m.group(1))
        except:
            exp = 0

    # Compétences (tokens >2 chars, filtrer mots génériques)
    stop = {
        'je','veux','cherche','besoin','recherche','trouve','trouver','candidat','candidats','profil','profils',
        'avec','pour','de','du','des','un','une','le','la','les','et','ou','dans','sur','poste'
    }
    tokens = [t for t in re.findall(r"[a-zA-ZÀ-ÿ0-9+#]+", text) if len(t) > 2]
    skills = [t for t in tokens if t not in stop]

    # Nettoyage basique
    # Retirer les termes de rôle des compétences
    role_terms = sum(role_map.values(), [])
    skills = [s for s in skills if s not in role_terms]

    # Quelques synonymes pour affichage
    synonyms = {
        'java': 'Java',
        'spring': 'Spring',
        'hibernate': 'Hibernate',
        'doctor': 'Doctor',
        'medecin': 'Médecin',
        'cardiologie': 'Cardiologie',
        'cardiologue': 'Cardiologue'
    }
    display_skills: List[str] = []
    for s in skills:
        display_skills.append(synonyms.get(s, s.capitalize()))

    return {
        'role': role_found or 'Profil recherché',
        'min_experience': exp,
        'skills': display_skills[:10]  # Limiter à 10 pour concision
    }


def generate_linkedin_post_content(job_description: str, num_candidates: int) -> str:
    """
    Génère un post LinkedIn précis avec sections claires (profil, offre, apport, CTA).
    """
    parsed = _parse_request(job_description)
    role = parsed['role']
    exp = parsed['min_experience']
    skills = parsed['skills']

    skills_block = "\n".join([f"- {s}" for s in skills]) if skills else "- Compétences clés à préciser"
    exp_line = f"- Expérience: {exp}+ ans" if exp > 0 else "- Expérience: à définir (ou junior/confirmé/senior)"

    subject_role = role.replace('profil recherché', job_description[:30])
    subject_line = f"Candidature - {subject_role[:40]}"

    post_template = f"""🔍 NOUS RECRUTONS: {role.upper()} ({num_candidates} poste(s))

📌 DÉTAILS DU POSTE
- Fonction: {role}
{exp_line}
- Compétences requises:
{skills_block}

📊 VOTRE PROFIL
✅ Vous maîtrisez les compétences listées ci-dessus
✅ Vous avez une réelle passion pour votre métier
✅ Vous êtes curieux(se) et en apprentissage continu
✅ Vous aimez le travail en équipe et l'innovation

🎯 CE QUE NOUS OFFRONS
✅ Un environnement de travail moderne et stimulant
✅ Des opportunités de développement et d'évolution
✅ Une équipe talentueuse et motivée
✅ Des projets innovants et challengeants
✅ Une rémunération compétitive

💼 CE QUE VOUS APPORTEREZ
✅ Votre expertise et vos compétences techniques
✅ Votre créativité et vos idées nouvelles
✅ Votre dynamisme et votre professionnalisme
✅ Votre contribution à nos succès

👉 INTÉRESSÉ(E) ?
Envoyez votre CV à : smarthire221@gmail.com
Objet : "{subject_line}"

⏱️ URGENT : Les candidatures sont traitées rapidement
N'attendez pas, postulez dès maintenant ! 🚀

#Recrutement #Emploi #Opportunité #Carrière #SmartHire #Hiring #Jobs

---
🤖 Offre créée par Smart-Hire AI Recruiting System
{datetime.now().strftime("%d/%m/%Y à %H:%M")}
"""

    return post_template


def create_linkedin_post_with_ollama(job_description: str, num_candidates: int) -> str:
    """
    Utilise Ollama pour générer un post LinkedIn professionnel et engageant.
    
    Args:
        job_description: Description du poste recherché
        num_candidates: Nombre de candidats souhaités
    
    Returns:
        Post LinkedIn généré par l'IA
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    prompt = f"""Tu es un expert en recrutement et en marketing RH. Crée un post LinkedIn professionnel et engageant pour recruter des candidats.

BESOIN DE RECRUTEMENT:
{job_description}

Nombre de postes à pourvoir: {num_candidates}

Le post doit:
1. Être accrocheur et professionnel
2. Mettre en avant l'opportunité
3. Inclure des emojis pertinents (🔍, 💼, ✅, 👉, etc.)
4. Mentionner comment postuler (envoi CV par email)
5. Inclure des hashtags pertinents (#Recrutement, #EmploiTech, etc.)
6. Être concis (200-300 mots max)
7. Créer un sentiment d'urgence mais rester professionnel

Format souhaité:
- Titre accrocheur avec emoji
- Description du besoin
- Ce qui est proposé (avantages)
- Call-to-action clair
- Hashtags pertinents

Génère UNIQUEMENT le texte du post, sans introduction ni explication.
"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": "gemma:2b",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,  # Plus créatif pour le contenu marketing
                "num_predict": 400
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_post = result.get('response', '').strip()
            
            # Ajouter la signature automatique
            ai_post += f"\n\n---\n📧 recrutement@smart-hire.com\n⏰ Publié le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
            
            return ai_post
        else:
            # Fallback sur le template par défaut
            return generate_linkedin_post_content(job_description, num_candidates)
    
    except Exception as e:
        print(f"Erreur Ollama pour génération post: {e}")
        return generate_linkedin_post_content(job_description, num_candidates)


def publish_to_linkedin_api(access_token: str, post_content: str, user_id: str) -> Dict:
    """
    Publie réellement sur LinkedIn via l'API (nécessite authentification OAuth).
    VERSION AMÉLIORÉE avec logs détaillés.
    
    Args:
        access_token: Token d'accès LinkedIn OAuth
        post_content: Contenu du post à publier
        user_id: ID de l'utilisateur LinkedIn
    
    Returns:
        Réponse de l'API LinkedIn
    """
    
    url = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # Construction du payload selon l'API LinkedIn
    payload = {
        "author": f"urn:li:person:{user_id}",
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
    
    try:
        print("\n" + "="*60)
        print("📤 TENTATIVE DE PUBLICATION SUR LINKEDIN")
        print("="*60)
        print(f"User ID: {user_id}")
        print(f"Token (début): {access_token[:20]}...")
        print(f"Longueur du post: {len(post_content)} caractères")
        print(f"URL: {url}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"\n📊 Réponse de l'API:")
        print(f"   Statut HTTP: {response.status_code}")
        
        if response.status_code == 201:
            post_data = response.json()
            post_id = post_data.get('id', '')
            
            print(f"   ✅ SUCCÈS - Post publié!")
            print(f"   ID du post: {post_id}")
            print("="*60 + "\n")
            
            return {
                "success": True,
                "message": "Post publié avec succès sur LinkedIn!",
                "post_id": post_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_text = response.text
            print(f"   ❌ ÉCHEC de publication")
            print(f"   Erreur: {error_text}")
            print("="*60 + "\n")
            
            return {
                "success": False,
                "message": f"Erreur API LinkedIn: {response.status_code}",
                "error": error_text
            }
    
    except Exception as e:
        print(f"   ❌ EXCEPTION lors de la publication")
        print(f"   Erreur: {str(e)}")
        print("="*60 + "\n")
        
        return {
            "success": False,
            "message": f"Erreur lors de la publication: {str(e)}"
        }


def save_linkedin_post_draft(post_content: str, job_description: str, filename: Optional[str] = None) -> str:
    """
    Sauvegarde le brouillon du post LinkedIn dans un fichier pour publication manuelle.
    
    Args:
        post_content: Contenu du post généré
        job_description: Description originale du poste
        filename: Nom du fichier (optionnel, généré automatiquement si non fourni)
    
    Returns:
        Chemin du fichier sauvegardé
    """
    
    import os
    
    # Créer le dossier si nécessaire
    drafts_dir = "data/linkedin_drafts"
    os.makedirs(drafts_dir, exist_ok=True)
    
    # Générer le nom du fichier si non fourni
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_post_{timestamp}.txt"
    
    filepath = os.path.join(drafts_dir, filename)
    
    # Créer le contenu complet avec métadonnées
    full_content = f"""# POST LINKEDIN - BROUILLON
# Généré automatiquement par Smart-Hire
# Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

## DESCRIPTION DU POSTE ORIGINAL:
{job_description}

## CONTENU DU POST À PUBLIER:
{post_content}

## INSTRUCTIONS:
1. Copiez le contenu du post ci-dessus
2. Allez sur LinkedIn: https://www.linkedin.com
3. Cliquez sur "Commencer un post"
4. Collez et adaptez si nécessaire
5. Publiez !

## HASHTAGS SUGGÉRÉS:
#Recrutement #EmploiTech #SmartHire #Opportunité #Carrière
#DéveloppeurPython #IA #TechJobs #HiringNow #JoinOurTeam
"""
    
    # Sauvegarder
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    return filepath


def auto_publish_job_post(
    job_description: str, 
    num_candidates: int,
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
    save_draft: bool = True
) -> Dict:
    """
    Fonction principale pour publier automatiquement une offre d'emploi sur LinkedIn
    quand aucun candidat n'est trouvé dans la base de données.
    
    Args:
        job_description: Description du poste recherché
        num_candidates: Nombre de candidats souhaités
        access_token: Token LinkedIn OAuth (optionnel)
        user_id: ID utilisateur LinkedIn (optionnel)
        save_draft: Sauvegarder un brouillon même si la publication réussit
    
    Returns:
        Dictionnaire avec le statut et les détails de la publication
    """
    
    result = {
        "post_generated": False,
        "post_content": "",
        "published_online": False,
        "draft_saved": False,
        "draft_path": "",
        "message": "",
        "timestamp": datetime.now().isoformat()
    }
    
    # Étape 1: Générer le contenu du post avec l'IA
    try:
        post_content = create_linkedin_post_with_ollama(job_description, num_candidates)
        result["post_generated"] = True
        result["post_content"] = post_content
        result["message"] = "Post généré avec succès"
    except Exception as e:
        result["message"] = f"Erreur lors de la génération: {str(e)}"
        return result
    
    # Étape 2: Sauvegarder le brouillon (toujours)
    if save_draft or not access_token:
        try:
            draft_path = save_linkedin_post_draft(post_content, job_description)
            result["draft_saved"] = True
            result["draft_path"] = draft_path
            result["message"] += f" | Brouillon sauvegardé: {draft_path}"
        except Exception as e:
            result["message"] += f" | Erreur sauvegarde brouillon: {str(e)}"
    
    # Étape 3: Publier en ligne si token disponible
    if access_token and user_id:
        try:
            publish_result = publish_to_linkedin_api(access_token, post_content, user_id)
            
            if publish_result.get("success"):
                result["published_online"] = True
                result["message"] += " | Publié sur LinkedIn avec succès!"
            else:
                result["message"] += f" | Publication échouée: {publish_result.get('message')}"
        
        except Exception as e:
            result["message"] += f" | Erreur publication: {str(e)}"
    else:
        result["message"] += " | Publication manuelle requise (pas de token LinkedIn)"
    
    return result


from urllib.parse import urlencode

def get_linkedin_oauth_url(client_id: str, redirect_uri: str) -> str:
    """
    Génère l'URL d'authentification OAuth LinkedIn.
    
    Args:
        client_id: Client ID de l'application LinkedIn
        redirect_uri: URI de redirection configurée
    
    Returns:
        URL d'authentification complète
    """
    
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    
    # Paramètres avec encodage automatique
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social"  # Espaces normaux
    }
    
    # urlencode gère l'encodage automatiquement
    query_string = urlencode(params)
    
    return f"{base_url}?{query_string}"

def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Optional[str]:
    """
    Échange le code d'autorisation contre un access token.
    
    Args:
        code: Code d'autorisation reçu
        client_id: Client ID LinkedIn
        client_secret: Client Secret LinkedIn
        redirect_uri: URI de redirection
    
    Returns:
        Access token ou None si échec
    """
    
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"Erreur échange token: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"Erreur lors de l'échange de token: {e}")
        return None


def get_linkedin_user_id(access_token: str) -> Optional[str]:
    """
    NOUVELLE FONCTION: Récupère l'ID utilisateur LinkedIn.
    Nécessaire pour publier automatiquement des posts.
    
    Args:
        access_token: Token d'accès LinkedIn
    
    Returns:
        User ID LinkedIn ou None si erreur
    """
    
    # Essayer d'abord avec l'API v2/userinfo (OpenID Connect)
    try:
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('sub')  # Le 'sub' contient l'ID
            
            if user_id:
                print(f"✅ User ID récupéré via /userinfo: {user_id}")
                return user_id
    except Exception as e:
        print(f"Tentative /userinfo échouée: {e}")
    
    # Fallback: Essayer avec l'API v2/me
    try:
        url = "https://api.linkedin.com/v2/me"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('id')
            
            if user_id:
                print(f"✅ User ID récupéré via /me: {user_id}")
                return user_id
    except Exception as e:
        print(f"Tentative /me échouée: {e}")
    
    print("❌ Impossible de récupérer le User ID")
    return None


# ==================== FONCTIONS DE TEST ====================

def test_linkedin_post_generation():
    """Test de génération de post LinkedIn"""
    
    print("\n" + "="*70)
    print("  🧪 TEST - GÉNÉRATION POST LINKEDIN")
    print("="*70)
    
    job_desc = "Recherche 3 développeurs Python avec 5+ ans d'expérience en Django, FastAPI et React. Poste full remote possible."
    num_cand = 3
    
    print("\n📝 Description du poste:")
    print(job_desc)
    
    print("\n🤖 Génération avec IA...")
    post = create_linkedin_post_with_ollama(job_desc, num_cand)
    
    print("\n✅ POST GÉNÉRÉ:")
    print("-"*70)
    print(post)
    print("-"*70)
    
    # Sauvegarder le brouillon
    draft_path = save_linkedin_post_draft(post, job_desc)
    print(f"\n💾 Brouillon sauvegardé: {draft_path}")
    
    return post


if __name__ == "__main__":
    # Test de génération
    test_linkedin_post_generation()