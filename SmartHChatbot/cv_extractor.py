import requests
import json
from typing import Dict, Optional
import io
import re
import PyPDF2

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extrait le texte d'un PDF.
    
    Args:
        pdf_content: Contenu binaire du PDF
    
    Returns:
        Texte extrait
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Erreur extraction PDF: {e}")
        return ""

def extract_text_from_file(content: bytes, filename: str) -> str:
    """
    Extrait le texte selon le type de fichier.
    
    Args:
        content: Contenu du fichier
        filename: Nom du fichier
    
    Returns:
        Texte extrait
    """
    if filename.endswith('.pdf'):
        return extract_text_from_pdf(content)
    elif filename.endswith(('.txt', '.text')):
        try:
            return content.decode('utf-8')
        except:
            return content.decode('latin-1')
    else:
        # Pour .doc, .docx, retourner un message
        return f"Format {filename.split('.')[-1]} non supporté directement"

def extract_cv_data_with_ai(cv_text: str) -> Optional[Dict]:
    """
    Utilise Ollama pour extraire les données structurées d'un CV.
    
    Args:
        cv_text: Texte du CV
    
    Returns:
        Dictionnaire avec les données extraites
    """
    
    if not cv_text or len(cv_text.strip()) < 50:
        return None
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    prompt = f"""Tu es un expert en analyse de CV. Analyse le CV suivant et extrais les informations principales au format JSON.

CV:
{cv_text}

Retourne UNIQUEMENT un JSON valide (sans autre texte) avec cette structure:
{{
    "nom": "Nom de famille",
    "prenom": "Prénom",
    "email": "Email si trouvé sinon vide",
    "telephone": "Téléphone si trouvé sinon vide",
    "poste": "Poste actuel ou dernier titre",
    "experience": nombre d'années (nombre entier),
    "formation": "Formation principale",
    "competences": ["liste", "de", "compétences"],
    "langues": ["Langue 1", "Langue 2"],
    "linkedin": "URL si trouvée sinon vide",
    "disponibilite": "Disponibilité ou préavis"
}}

IMPORTANT:
- Si une information n'est pas trouvée, mets une valeur vide ou par défaut
- Pour l'expérience, calcule le nombre d'années
- Pour les compétences et langues, retourne une liste même si vide
- Retourne UNIQUEMENT le JSON"""

    try:
        print(f"            ⏳ Appel Ollama (timeout 30s)...")
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": "gemma:2b",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
                "num_predict": 1000,
                "format": "json"
            },
            timeout=30  # Timeout de 30 secondes
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '{}')
            
            try:
                cv_data = json.loads(ai_response)
                cv_data = validate_and_clean_cv_data(cv_data)
                print(f"            ✅ Extraction réussie")
                return cv_data
            except json.JSONDecodeError:
                print(f"            ⚠️  JSON invalide, passage au fallback")
                return None
        else:
            print(f"            ⚠️  Ollama erreur {response.status_code}, fallback")
            return None
    
    except requests.exceptions.Timeout:
        print("            ⏱️  Timeout Ollama (>30s), passage au fallback")
        return None
    except requests.exceptions.ConnectionError:
        print("            ❌ Ollama non accessible, passage au fallback")
        return None
    except Exception as e:
        print(f"            ❌ Erreur: {str(e)[:50]}")
        return None


def basic_cv_fallback(cv_text: str, sender_email: str = "") -> Optional[Dict]:
    """
    Fallback amélioré pour extraire les infos clés sans IA.
    Utilise des regex et patterns pour extraire nom, prénom, compétences, etc.
    """
    if not cv_text or len(cv_text.strip()) < 20:
        return None

    text_lower = cv_text.lower()
    
    # Email - chercher dans tout le texte
    email_match = re.search(r"[\w.+'%-]+@[\w.-]+\.[a-zA-Z]{2,}", cv_text)
    email = email_match.group(0) if email_match else sender_email

    # Téléphone - pattern plus large
    phone_match = re.search(r"(\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,4})", cv_text)
    telephone = phone_match.group(0).strip() if phone_match else ""

    # Nom/prénom - première ligne avec capitales ou près de "CV" ou début
    lines = [ln.strip() for ln in cv_text.splitlines() if ln.strip() and len(ln.strip()) > 2]
    nom, prenom = "Non spécifié", "Non spécifié"
    for i, line in enumerate(lines[:5]):  # Chercher dans les 5 premières lignes
        if re.match(r"^[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+", line):
            tokens = line.split()[:2]
            if len(tokens) == 2:
                prenom, nom = tokens[0], tokens[1]
                break
    
    # Poste - chercher "Title:", "Position:", ou ligne après nom
    poste = "Poste à préciser"
    for i, line in enumerate(lines[:10]):
        if any(keyword in line.lower() for keyword in ["title:", "position:", "role:", "poste:"]):
            poste = line.split(":", 1)[-1].strip()
            break
        if i > 0 and len(line.split()) <= 5 and not any(c.isdigit() for c in line):
            # Probablement un titre de poste
            poste = line
            break
    
    # Compétences - mots-clés techniques courants
    tech_keywords = [
        'python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
        'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring', 'laravel',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'docker', 'kubernetes',
        'aws', 'azure', 'gcp', 'git', 'linux', 'agile', 'scrum', 'ai', 'ml', 'data'
    ]
    competences = []
    for keyword in tech_keywords:
        if keyword in text_lower:
            competences.append(keyword.upper() if keyword in ['sql', 'ai', 'ml', 'aws', 'gcp'] else keyword.capitalize())
    
    # Langues - chercher "Languages:", "Langues:", ou mots courants
    langues = []
    lang_keywords = {
        'french': 'Français', 'francais': 'Français', 'français': 'Français',
        'english': 'Anglais', 'anglais': 'Anglais',
        'spanish': 'Espagnol', 'espagnol': 'Espagnol',
        'german': 'Allemand', 'allemand': 'Allemand',
        'arabic': 'Arabe', 'arabe': 'Arabe',
        'chinese': 'Chinois', 'chinois': 'Chinois'
    }
    for key, value in lang_keywords.items():
        if key in text_lower and value not in langues:
            langues.append(value)
    
    # Expérience - chercher des années ou durées
    experience = 0
    exp_match = re.search(r'(\d+)\s*(?:years?|ans?|year)', text_lower)
    if exp_match:
        try:
            experience = int(exp_match.group(1))
        except:
            pass
    
    # Formation - chercher "Education:", "Formation:", "Degree:", etc.
    formation = "Formation à préciser"
    for line in lines:
        if any(keyword in line.lower() for keyword in ['university', 'université', 'bachelor', 'master', 'phd', 'engineer', 'ingénieur']):
            formation = line[:100]  # Limiter à 100 caractères
            break
    
    # LinkedIn
    linkedin = ""
    linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', cv_text)
    if linkedin_match:
        linkedin = "https://" + linkedin_match.group(0)

    fallback_candidate = {
        "nom": nom,
        "prenom": prenom,
        "email": email or sender_email,
        "telephone": telephone,
        "poste": poste,
        "experience": experience,
        "formation": formation,
        "competences": competences[:10],  # Max 10 compétences
        "langues": langues,
        "linkedin": linkedin,
        "disponibilite": "Immédiate"
    }

    return fallback_candidate

def validate_and_clean_cv_data(cv_data: Dict) -> Dict:
    """
    Valide et nettoie les données extraites.
    
    Args:
        cv_data: Données brutes
    
    Returns:
        Données nettoyées
    """
    
    # Valeurs par défaut
    defaults = {
        "nom": "Non spécifié",
        "prenom": "Non spécifié",
        "email": "",
        "telephone": "",
        "poste": "Poste non spécifié",
        "experience": 0,
        "formation": "Non spécifiée",
        "competences": [],
        "langues": [],
        "linkedin": "",
        "disponibilite": "Immédiate"
    }
    
    # Fusionner avec les valeurs par défaut
    for key, default_value in defaults.items():
        if key not in cv_data or cv_data[key] is None:
            cv_data[key] = default_value
    
    # Convertir les listes
    for field in ['competences', 'langues']:
        if not isinstance(cv_data.get(field), list):
            cv_data[field] = []
    
    # Convertir l'expérience en entier
    try:
        cv_data['experience'] = int(cv_data.get('experience', 0))
    except (ValueError, TypeError):
        cv_data['experience'] = 0
    
    # Nettoyer les chaînes
    for field in ['nom', 'prenom', 'email', 'telephone', 'poste', 'formation', 'linkedin', 'disponibilite']:
        if isinstance(cv_data.get(field), str):
            cv_data[field] = cv_data[field].strip()
    
    return cv_data

def candidate_exists(cv_data: Dict) -> bool:
    """
    Vérifie si un CV exactement identique existe déjà dans la base.
    Compare tous les champs principaux pour détecter les doublons stricts.
    
    Args:
        cv_data: Données du candidat
    
    Returns:
        True si le CV exact existe déjà, False sinon
    """
    cv_file = 'data/cv_data.json'
    
    try:
        if os.path.exists(cv_file):
            with open(cv_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            # Normaliser les données du nouveau CV
            new_email = cv_data.get('email', '').strip().lower()
            new_nom = cv_data.get('nom', '').strip().lower()
            new_prenom = cv_data.get('prenom', '').strip().lower()
            new_poste = cv_data.get('poste', '').strip().lower()
            new_exp = cv_data.get('experience', 0)
            new_formation = cv_data.get('formation', '').strip().lower()
            new_competences = sorted([c.strip().lower() for c in cv_data.get('competences', [])])
            
            # Comparer avec chaque candidat existant
            for candidate in candidates:
                # Normaliser les données du candidat existant
                cand_email = candidate.get('email', '').strip().lower()
                cand_nom = candidate.get('nom', '').strip().lower()
                cand_prenom = candidate.get('prenom', '').strip().lower()
                cand_poste = candidate.get('poste', '').strip().lower()
                cand_exp = candidate.get('experience', 0)
                cand_formation = candidate.get('formation', '').strip().lower()
                cand_competences = sorted([c.strip().lower() for c in candidate.get('competences', [])])
                
                # Vérifier si TOUS les champs principaux sont identiques
                if (cand_email == new_email and
                    cand_nom == new_nom and
                    cand_prenom == new_prenom and
                    cand_poste == new_poste and
                    cand_exp == new_exp and
                    cand_formation == new_formation and
                    cand_competences == new_competences):
                    return True  # CV exactement identique trouvé
        
        return False
    
    except Exception as e:
        print(f"Erreur lors de la vérification: {e}")
        return False

def add_candidate_to_database(cv_data: Dict) -> bool:
    """
    Ajoute un candidat à la base de données.
    Évite les doublons en vérifiant l'existence préalable.
    
    Args:
        cv_data: Données du candidat
    
    Returns:
        True si succès, False sinon
    """
    cv_file = 'data/cv_data.json'
    
    # Vérifier que le candidat n'existe pas déjà
    if candidate_exists(cv_data):
        print(f"⚠️  Candidat déjà présent: {cv_data.get('prenom')} {cv_data.get('nom')}")
        return False
    
    try:
        # Charger les données existantes
        if os.path.exists(cv_file):
            with open(cv_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
        else:
            candidates = []
        
        # Générer nouvel ID
        new_id = max((c.get('id', 0) for c in candidates), default=0) + 1
        cv_data['id'] = new_id
        
        # Ajouter le candidat
        candidates.append(cv_data)
        
        # Sauvegarder
        with open(cv_file, 'w', encoding='utf-8') as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Candidat ajouté: {cv_data.get('prenom')} {cv_data.get('nom')} (ID: {new_id})")
        return True
    
    except Exception as e:
        print(f"Erreur lors de l'ajout: {e}")
        return False

import os
