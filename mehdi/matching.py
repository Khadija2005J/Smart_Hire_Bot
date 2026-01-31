import requests
import json
import re
from typing import List, Dict


# Modèle par défaut pour Ollama (facile à remplacer)
MODEL_NAME = "tinyllama:latest"

# NOUVEAU: Seuil minimum de matching (score minimal pour être pertinent)
MINIMUM_MATCH_SCORE = 30  # Les candidats avec un score < 30% seront rejetés


def extract_criteria_from_request(job_description: str) -> Dict:
    """
    Extrait les critères (expérience minimale, nombre de candidats, skills) de la demande
    
    Args:
        job_description: Description de la recherche de candidat
    
    Returns:
        Dict avec min_experience, max_candidates, required_skills, languages, role_terms
    """
    criteria = {
        'min_experience': 0,
        'max_candidates': 4,
        'required_keywords': [],
        'languages': [],
        'role_terms': []
    }
    
    # Chercher patterns comme "10 ans", "5+ ans", "senior" etc
    experience_patterns = [
        r'(\d+)\+\s*ans',  # "10+ ans"
        r'(\d+)\s*ans',     # "10 ans"
        r'senior',          # "senior"
        r'expert',          # "expert"
        r'confirmé'         # "confirmé"
    ]
    
    desc_lower = job_description.lower()
    for pattern in experience_patterns:
        match = re.search(pattern, desc_lower)
        if match:
            if pattern == r'(\d+)\+\s*ans' or pattern == r'(\d+)\s*ans':
                years = int(match.group(1))
                if years > criteria['min_experience']:
                    criteria['min_experience'] = years
            elif 'senior' in pattern and criteria['min_experience'] < 5:
                criteria['min_experience'] = 5
            elif 'expert' in pattern and criteria['min_experience'] < 7:
                criteria['min_experience'] = 7
    
    # Chercher le nombre de candidats
    num_patterns = [
        r'(\d+)\s*(?:développeurs|ingénieurs|candidats|spécialistes|experts)',
        r'(?:je\s+veux|cherche|besoin)\s+(\d+)',
        r'(?:trouver|recruter)\s+(\d+)'
    ]
    
    for pattern in num_patterns:
        match = re.search(pattern, desc_lower)
        if match:
            num = int(match.group(1))
            criteria['max_candidates'] = num
            break

    # Détecter les langues demandées dans la requête
    lang_map = {
        'francais': 'français', 'français': 'français', 'french': 'français',
        'anglais': 'anglais', 'english': 'anglais',
        'espagnol': 'espagnol', 'spanish': 'espagnol',
        'arabe': 'arabe', 'arabic': 'arabe',
        'allemand': 'allemand', 'german': 'allemand'
    }
    langs = []
    for k, v in lang_map.items():
        if k in desc_lower and v not in langs:
            langs.append(v)
    criteria['languages'] = langs

    # Détecter des termes de rôle utiles (souples)
    role_variants = [
        'developpeur', 'développeur', 'developpeurs', 'développeurs', 'developer', 'dev',
        'software engineer', 'software engineers', 'software engineering',
        'ingenieur logiciel', 'ingénieur logiciel', 'engineer', 'engineers', 'ingénieur', 'ingenieur', 'ingénieurs', 'ingenieurs',
        'medecin', 'médecin', 'docteur', 'doctor', 'cardiologue'
    ]
    criteria['role_terms'] = [r for r in role_variants if r in desc_lower]

    return criteria


def match_candidates(job_description: str, cv_data: List[Dict], num_candidates: int = 4) -> List[Dict]:
    """
    Utilise Ollama pour matcher les candidats avec la description du poste.
    AMÉLIORATION: Retourne une liste vide si aucun candidat pertinent.
    
    Args:
        job_description: Description du poste recherché
        cv_data: Liste des CV au format JSON
        num_candidates: Nombre de candidats à retourner
    
    Returns:
        Liste des candidats matchés avec leur score (vide si aucun pertinent)
    """
    
    # URL de l'API Ollama locale
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    # Préparer les données des CV pour l'IA
    cv_summaries = []
    for idx, cv in enumerate(cv_data):
        summary = f"""
        Candidat {idx + 1}:
        - Nom: {cv['nom']} {cv['prenom']}
        - Email: {cv['email']}
        - Poste: {cv['poste']}
        - Expérience: {cv['experience']} ans
        - Compétences: {', '.join(cv.get('competences', []))}
        - Formation: {cv.get('formation', 'Non spécifié')}
        - Langues: {', '.join(cv.get('langues', []))}
        """
        cv_summaries.append(summary)
    
    # AMÉLIORATION: Prompt plus strict
    prompt = f"""Tu es un expert en recrutement. Analyse la description du poste suivante et les CV des candidats.

IMPORTANT: 
- Sois TRÈS STRICT dans ton évaluation
- Si AUCUN candidat ne correspond vraiment, retourne une liste VIDE
- Un candidat doit avoir AU MOINS 30% de compatibilité pour être retourné
- Ne force PAS un matching si les profils ne correspondent pas

Description du poste:
{job_description}

Candidats disponibles:
{chr(10).join(cv_summaries)}

Pour chaque candidat QUI CORRESPOND RÉELLEMENT (score >= 30%), fournis:
1. Le numéro du candidat (1-{len(cv_data)})
2. Un score de matching de 0 à 100 (sois HONNÊTE)
3. Une explication courte (2-3 phrases) justifiant le score

Si AUCUN candidat ne correspond, retourne une liste vide: {{"selected_candidates": []}}

Réponds UNIQUEMENT au format JSON suivant (sans autre texte):
{{
    "selected_candidates": [
        {{
            "candidate_number": 1,
            "match_score": 95,
            "match_reason": "Explication du matching..."
        }}
    ]
}}

Si aucun candidat pertinent: {{"selected_candidates": []}}
"""
    
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3,
                "num_predict": 500,
                "format": "json"
            },
            timeout=None
        )

        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '{}')

            try:
                matching_result = json.loads(ai_response)
                selected = matching_result.get('selected_candidates', [])

                # NOUVEAU: Filtrer les candidats avec score trop bas
                matched_candidates = []
                for selection in selected[:num_candidates]:
                    match_score = selection.get('match_score', 0)
                    
                    # Rejeter si score trop bas
                    if match_score < MINIMUM_MATCH_SCORE:
                        print(f"⚠️  Candidat rejeté (score {match_score}% < {MINIMUM_MATCH_SCORE}%)")
                        continue
                    
                    candidate_idx = selection.get('candidate_number', 1) - 1

                    if 0 <= candidate_idx < len(cv_data):
                        candidate = cv_data[candidate_idx].copy()
                        candidate['match_score'] = match_score
                        candidate['match_reason'] = selection.get('match_reason', 'Bon profil pour le poste')
                        matched_candidates.append(candidate)

                # NOUVEAU: Appliquer une pertinence post-filtre (titre/compétences/expérience)
                def _is_relevant(cand: Dict) -> bool:
                    # Expérience
                    min_exp = extract_criteria_from_request(job_description)['min_experience']
                    if cand.get('experience', 0) < min_exp:
                        return False
                    # Compétences
                    comp = ' '.join(cand.get('competences', [])).lower()
                    has_skill = any(k in comp for k in job_description.lower().split())
                    # Poste
                    poste = cand.get('poste', '').lower()
                    role_terms = ['développeur', 'developpeur', 'developer', 'ingénieur', 'ingenieur', 'engineer', 'médecin', 'medecin', 'doctor']
                    role_in_query = any(t in job_description.lower() for t in role_terms)
                    role_in_title = any(t in poste for t in role_terms)
                    if role_in_query and not role_in_title:
                        return False
                    # Si des mots techniques existent dans la requête, exiger au moins 1 match
                    tokens = [t for t in re.findall(r"[a-zA-ZÀ-ÿ0-9+#]+", job_description.lower()) if len(t) > 2]
                    tech_tokens = [t for t in tokens if t not in ['développeur','developpeur','developer','ingénieur','ingenieur','engineer','médecin','medecin','doctor']]
                    if tech_tokens and not any(t in comp for t in tech_tokens):
                        return False
                    return True

                matched_candidates = [c for c in matched_candidates if _is_relevant(c)]

                # NOUVEAU: Si aucun candidat pertinent, retourner liste vide
                if len(matched_candidates) == 0:
                    print("ℹ️  Aucun candidat ne correspond aux critères (tous < {}%)".format(MINIMUM_MATCH_SCORE))
                    return []

                # Si pas assez de candidats, essayer le fallback
                if len(matched_candidates) < num_candidates:
                    return fallback_matching(job_description, cv_data, num_candidates)

                return matched_candidates

            except json.JSONDecodeError:
                return fallback_matching(job_description, cv_data, num_candidates)

        # Si Ollama répond avec erreur, basculer sur le fallback
        return fallback_matching(job_description, cv_data, num_candidates)

    except requests.exceptions.ConnectionError:
        # Ollama pas démarré : fallback silencieux
        return fallback_matching(job_description, cv_data, num_candidates)

    except Exception:
        # Toute autre erreur : fallback pour garantir un résultat
        return fallback_matching(job_description, cv_data, num_candidates)


def fallback_matching(job_description: str, cv_data: List[Dict], num_candidates: int) -> List[Dict]:
    """
    Système de matching de secours basé sur les mots-clés
    AMÉLIORATION: Retourne une liste vide si aucun candidat pertinent
    AMÉLIORATION 2: Respecte les critères d'expérience demandés
    """
    
    # Extraire les critères
    criteria = extract_criteria_from_request(job_description)
    min_experience = criteria['min_experience']
    desired_languages = set(criteria.get('languages', []))
    requested_role_terms = set(criteria.get('role_terms', []))
    
    # Mots à ignorer (stop words + mots génériques)
    stop_words = {
        'recherche', 'cherche', 'besoin', 'rechercher', 'trouver',
        'développeur', 'développeurs', 'developer', 'dev', 'engineer', 'ingénieur',
        'candidat', 'candidats', 'profil', 'profils', 'personne',
        'poste', 'emploi', 'job', 'travail', 'mission',
        'pour', 'avec', 'dans', 'sur', 'une', 'des', 'les', 'un',
        'expérimenté', 'expérience', 'senior', 'junior', 'confirmé', 'expert',
        'ans', 'year', 'years', 'mois', 'month', 'months'
    }
    
    # Extraire les mots-clés techniques uniquement (> 2 lettres et pas dans stop words)
    keywords = set(
        word.lower() for word in re.findall(r"[a-zA-ZÀ-ÿ0-9+#]+", job_description.lower())
        if len(word) > 2 and word.lower() not in stop_words
    )
    
    # Ajouter des variantes de technologies
    keyword_variations = {
        'python': ['python', 'django', 'flask', 'fastapi', 'pydantic', 'pytorch', 'tensorflow'],
        'javascript': ['javascript', 'js', 'react', 'vue', 'angular', 'node', 'nodejs'],
        'java': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
        'data': ['data', 'scientist', 'analyst', 'engineer', 'machine learning', 'ml', 'ai'],
        'web': ['web', 'frontend', 'backend', 'fullstack', 'full-stack'],
        'mobile': ['mobile', 'android', 'ios', 'react native', 'flutter'],
        'cloud': ['cloud', 'aws', 'azure', 'gcp', 'devops', 'kubernetes', 'docker'],
        'blockchain': ['blockchain', 'solidity', 'web3', 'ethereum', 'crypto', 'smart', 'contract'],
        'security': ['security', 'cybersecurity', 'cyber', 'secure', 'encryption', 'cryptography'],
        # Médecine / santé (pour les demandes hors IT)
        'medecin': ['médecin', 'medecin', 'docteur', 'doctor', 'cardio', 'cardiologie', 'cardiologue', 'cardiovascular', 'cardiovasculaire']
    }

    role_keywords = {
        'developpeur': ['développeur', 'developpeur', 'developer', 'dev', 'ingénieur', 'ingenieur', 'engineer', 'engineering'],
        'medecin': ['médecin', 'medecin', 'docteur', 'doctor', 'cardiologue', 'cardio']
    }
    
    # Étendre avec variantes
    extended_keywords = set(keywords)
    for keyword in list(keywords):
        if keyword in keyword_variations:
            extended_keywords.update(keyword_variations[keyword])
    
    # Si aucun mot-clé technique, chercher au moins le contexte
    if not extended_keywords:
        extended_keywords = keywords
    
    # Déterminer les rôles demandés ou implicites (ex: développeur, médecin)
    role_terms_present = set()
    for role, variants in role_keywords.items():
        if any(v in extended_keywords for v in variants) or any(v in requested_role_terms for v in variants):
            role_terms_present.add(role)

    # Rôles explicitement demandés via la requête (si fournis, prioritaire)
    requested_roles = set()
    if requested_role_terms:
        for role, variants in role_keywords.items():
            if any(v in requested_role_terms for v in variants):
                requested_roles.add(role)
    else:
        requested_roles = set(role_terms_present)

    # Calculer le score avec contraintes flexibles (compétences OU titre OU langues)
    scored_candidates = []
    
    for candidate in cv_data:
        # ✅ Vérifier l'expérience minimale requise
        candidate_experience = candidate.get('experience', 0)
        if candidate_experience < min_experience:
            # Pénalité très forte pour ne pas respecter l'expérience requise
            continue  # Ignorer complètement si l'expérience ne correspond pas
        
        score = 0
        matching_skills = 0
        matching_in_title = 0
        matching_langs = 0
        
        # Vérifier compétences (priorité absolue)
        competences_text = ' '.join(candidate.get('competences', [])).lower()
        for keyword in extended_keywords:
            if keyword in competences_text:
                matching_skills += 1
                # Bonus fort pour technologies clés
                if keyword in ['python', 'java', 'javascript', 'react', 'angular', 'django', 'flask', 'spring', 'solidity', 'blockchain']:
                    score += 30  # Encore plus fort pour technos principales
                else:
                    score += 20  # Bonus pour autres compétences
        
        # Vérifier le poste
        poste = candidate.get('poste', '').lower()
        for keyword in extended_keywords:
            if keyword in poste:
                matching_in_title += 1
                score += 15  # Bonus modéré pour titre

        # Si la requête implique un rôle, ne compter que les variantes de CE(S) rôle(s)
        if requested_roles:
            role_variants_flat = set()
            for r in requested_roles:
                role_variants_flat.update(role_keywords.get(r, []))
            if any(var in poste for var in role_variants_flat):
                matching_in_title += 1
                score += 15

        # Si des termes de rôle explicites sont demandés, bonus si le poste contient un de ces termes
        if requested_role_terms:
            if any(rt in poste for rt in requested_role_terms):
                score += 15
        
        # Vérifier la formation
        formation = candidate.get('formation', '').lower()
        for keyword in extended_keywords:
            if keyword in formation:
                score += 5
        
        # Langues demandées (si présentes)
        cand_langs = [l.lower() for l in candidate.get('langues', [])]
        for lang in desired_languages:
            if any(lang in l for l in cand_langs):
                matching_langs += 1
                score += 10

        # ✅ Bonus pour l'expérience qui dépasse le minimum
        # Si le candidat a plus d'expérience que demandé, ça vaut des points
        if candidate_experience >= min_experience:
            bonus_exp = min((candidate_experience - min_experience) * 2, 15)  # Max 15 points bonus
            score += bonus_exp

        # ❗ Exiger au moins 1 signal pertinent parmi (titre, compétences, langues)
        signals_matched = (1 if matching_skills > 0 else 0) + (1 if matching_in_title > 0 else 0) + (1 if matching_langs > 0 else 0)
        if signals_matched == 0:
            continue

        # Cas stricte: si un rôle médical est explicitement demandé, exiger présence dans le titre
        if 'medecin' in requested_roles:
            med_variants = set(role_keywords['medecin'])
            if not any(v in poste for v in med_variants):
                continue

        # Ne garder que si score minimum atteint (seuil adaptatif selon nombre de critères fournis)
        provided_signals = 0
        if extended_keywords:
            provided_signals += 1
        if requested_role_terms:
            provided_signals += 1
        if desired_languages:
            provided_signals += 1
        role_only_query = bool(requested_role_terms) and not extended_keywords and not desired_languages
        dynamic_threshold = MINIMUM_MATCH_SCORE - (10 if provided_signals <= 1 else 0)
        if role_only_query:
            dynamic_threshold -= 5
        if score >= dynamic_threshold:
            candidate_copy = candidate.copy()
            candidate_copy['match_score'] = min(score, 100)
            candidate_copy['match_reason'] = f"✓ {matching_skills} compétences techniques | ✓ {matching_in_title} match(s) titre | ✓ {candidate_experience} ans exp."
            scored_candidates.append(candidate_copy)
    
    # Si aucun candidat ne dépasse le seuil
    if len(scored_candidates) == 0:
        min_exp_msg = f" avec minimum {min_experience} ans" if min_experience > 0 else ""
        # Utiliser un message sans emoji pour éviter les problèmes d'encodage console Windows
        print(f"Fallback: Aucun candidat ne depasse le seuil de {MINIMUM_MATCH_SCORE}%{min_exp_msg}")
        return []
    
    # Trier par score
    scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
    
    return scored_candidates[:num_candidates]


def smart_match_candidates(job_description: str, cv_data: List[Dict], num_candidates: int = 4) -> Dict:
    """
    NOUVELLE FONCTION: Matching intelligent avec analyse de pertinence
    
    Returns:
        Dict avec:
        - 'candidates': Liste des candidats matchés (peut être vide)
        - 'has_results': Boolean indiquant si des candidats pertinents ont été trouvés
        - 'reason': Raison si aucun résultat
    """
    
    matched = match_candidates(job_description, cv_data, num_candidates)
    
    result = {
        'candidates': matched,
        'has_results': len(matched) > 0,
        'total_in_db': len(cv_data),
        'requested': num_candidates
    }
    
    if not result['has_results']:
        # Analyser pourquoi aucun résultat
        keywords = set(word.lower() for word in job_description.lower().split() if len(word) > 3)
        
        # Compter les profils qui ont AU MOINS un mot-clé
        partial_matches = 0
        for candidate in cv_data:
            competences = ' '.join(candidate.get('competences', [])).lower()
            poste = candidate.get('poste', '').lower()
            text = f"{competences} {poste}"
            
            if any(keyword in text for keyword in keywords):
                partial_matches += 1
        
        if partial_matches == 0:
            result['reason'] = "Aucun profil dans la base ne correspond aux compétences recherchées."
        else:
            result['reason'] = f"Bien que {partial_matches} profil(s) partagent quelques mots-clés, aucun ne correspond suffisamment au besoin spécifique (seuil: {MINIMUM_MATCH_SCORE}%)."
    
    return result


def test_ollama_connection() -> bool:
    """
    Teste si Ollama est accessible
    
    Returns:
        True si Ollama est accessible, False sinon
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


# ==================== TESTS ====================

def test_matching_with_irrelevant_search():
    """
    Test: Recherche de profil totalement non pertinent
    Devrait retourner 0 résultats
    """
    print("\n" + "="*70)
    print("  TEST: Recherche de profil non pertinent")
    print("="*70)
    
    # Données de test (développeurs)
    test_cv_data = [
        {
            "id": 1,
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean.dupont@email.com",
            "poste": "Développeur Python",
            "experience": 5,
            "competences": ["Python", "Django", "PostgreSQL", "Docker"],
            "formation": "Master Informatique"
        },
        {
            "id": 2,
            "nom": "Martin",
            "prenom": "Marie",
            "email": "marie.martin@email.com",
            "poste": "Data Scientist",
            "experience": 3,
            "competences": ["Python", "Machine Learning", "TensorFlow", "SQL"],
            "formation": "Master Data Science"
        }
    ]
    
    # Recherche totalement non pertinente
    job_desc = "Recherche astronaute avec 20 ans d'expérience en missions spatiales vers Mars"
    
    print(f"\n📝 Description: {job_desc}")
    print(f"📊 Candidats en base: {len(test_cv_data)}")
    
    result = smart_match_candidates(job_desc, test_cv_data, num_candidates=3)
    
    print(f"\n✅ Résultats trouvés: {len(result['candidates'])}")
    print(f"🎯 Pertinence détectée: {result['has_results']}")
    
    if not result['has_results']:
        print(f"💡 Raison: {result['reason']}")
        print("\n✅ TEST RÉUSSI - Aucun faux positif!")
        return True
    else:
        print("\n❌ TEST ÉCHOUÉ - Des résultats non pertinents ont été retournés:")
        for cand in result['candidates']:
            print(f"  - {cand['prenom']} {cand['nom']}: {cand['match_score']}%")
        return False


def test_matching_with_relevant_search():
    """
    Test: Recherche de profil pertinent
    Devrait retourner des résultats
    """
    print("\n" + "="*70)
    print("  TEST: Recherche de profil pertinent")
    print("="*70)
    
    test_cv_data = [
        {
            "id": 1,
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean.dupont@email.com",
            "poste": "Développeur Python",
            "experience": 5,
            "competences": ["Python", "Django", "PostgreSQL", "Docker"],
            "formation": "Master Informatique"
        },
        {
            "id": 2,
            "nom": "Martin",
            "prenom": "Marie",
            "email": "marie.martin@email.com",
            "poste": "Développeur Full-Stack",
            "experience": 3,
            "competences": ["Python", "Django", "React", "PostgreSQL"],
            "formation": "Master Informatique"
        }
    ]
    
    # Recherche pertinente
    job_desc = "Développeur Python avec Django et PostgreSQL"
    
    print(f"\n📝 Description: {job_desc}")
    print(f"📊 Candidats en base: {len(test_cv_data)}")
    
    result = smart_match_candidates(job_desc, test_cv_data, num_candidates=2)
    
    print(f"\n✅ Résultats trouvés: {len(result['candidates'])}")
    print(f"🎯 Pertinence détectée: {result['has_results']}")
    
    if result['has_results']:
        print("\n📋 Candidats trouvés:")
        for cand in result['candidates']:
            print(f"  - {cand['prenom']} {cand['nom']}: {cand['match_score']}% - {cand.get('poste', 'N/A')}")
        print("\n✅ TEST RÉUSSI - Candidats pertinents retournés!")
        return True
    else:
        print(f"\n❌ TEST ÉCHOUÉ - Aucun résultat alors qu'il y a des profils pertinents")
        print(f"💡 Raison: {result.get('reason', 'N/A')}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  🧪 TESTS DU MATCHING AMÉLIORÉ")
    print("="*70)
    
    test1 = test_matching_with_irrelevant_search()
    test2 = test_matching_with_relevant_search()
    
    print("\n" + "="*70)
    print("  📊 RÉSUMÉ")
    print("="*70)
    print(f"  Test recherche non pertinente: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Test recherche pertinente: {'✅ PASS' if test2 else '❌ FAIL'}")
    print("="*70)
    
    if test1 and test2:
        print("\n🎉 TOUS LES TESTS SONT RÉUSSIS!")
        print("\n💡 Le système détecte maintenant correctement:")
        print("   ✅ Quand AUCUN profil ne correspond → Liste vide")
        print("   ✅ Quand des profils correspondent → Retourne les meilleurs")
    else:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")