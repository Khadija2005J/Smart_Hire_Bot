#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation des CV reçus par email
Récupère les CVs, les traite avec l'IA et les ajoute à la base de données
"""

import json
from email_receiver import connect_to_email, fetch_cv_emails, mark_email_as_processed
from cv_extractor import extract_text_from_file, extract_cv_data_with_ai, add_candidate_to_database
from typing import Dict, List

def sync_emails_with_database(email_address: str, app_password: str, imap_server: str = "imap.gmail.com") -> Dict:
    """
    Synchronise les emails contenant des CVs avec la base de données.
    
    Args:
        email_address: Email de la boîte de réception
        app_password: Mot de passe d'application
        imap_server: Serveur IMAP
    
    Returns:
        Résumé de la synchronisation
    """
    
    summary = {
        'connected': False,
        'emails_found': 0,
        'cvs_processed': 0,
        'cvs_added': 0,
        'errors': [],
        'candidates_added': []
    }
    
    print("\n" + "="*70)
    print("  📧 SYNCHRONISATION DES EMAILS - EXTRACTION DE CVs")
    print("="*70)
    
    # Étape 1: Connexion
    print("\n1️⃣  Connexion à la boîte mail...")
    mail = connect_to_email(email_address, app_password, imap_server)
    
    if not mail:
        summary['errors'].append("Impossible de se connecter à la boîte mail")
        print("   ❌ Connexion échouée")
        return summary
    
    print(f"   ✅ Connexion établie à {email_address}")
    summary['connected'] = True
    
    # Étape 2: Récupérer les emails
    print("\n2️⃣  Récupération des emails avec CVs...")
    print("   🔍 Recherche uniquement les emails NON LUS...")
    emails = fetch_cv_emails(mail, unread_only=True)
    print(f"   ✅ {len(emails)} email(s) avec pièces jointes trouvé(s)")
    summary['emails_found'] = len(emails)
    
    if not emails:
        print("\n   ℹ️  Aucun email avec CV à traiter")
        mail.close()
        return summary
    
    # Étape 3: Traiter chaque email
    print("\n3️⃣  Traitement des CVs avec l'IA...")
    
    for idx, email_data in enumerate(emails, 1):
        print(f"\n   📨 Email {idx}/{len(emails)}")
        print(f"      De: {email_data['sender_name']} ({email_data['sender_email']})")
        print(f"      Sujet: {email_data['subject'][:50]}...")
        print(f"      Pièces jointes: {len(email_data['attachments'])}")
        
        # Traiter chaque pièce jointe
        for attachment in email_data['attachments']:
            filename = attachment['filename']
            content = attachment['content']
            
            print(f"      📄 Traitement: {filename}")
            
            try:
                # Étape 3a: Extraire le texte
                cv_text = extract_text_from_file(content, filename)
                
                if not cv_text or len(cv_text) < 50:
                    print(f"         ⚠️  Fichier trop court ou vide")
                    continue
                
                summary['cvs_processed'] += 1
                
                # Étape 3b: Analyser avec l'IA
                print(f"         🤖 Analyse avec l'IA...")
                cv_data = extract_cv_data_with_ai(cv_text)
                
                if not cv_data:
                    print(f"         ⚠️  IA a échoué, tentative avec fallback basique...")
                    from cv_extractor import basic_cv_fallback
                    cv_data = basic_cv_fallback(cv_text, email_data['sender_email'])
                    
                if not cv_data:
                    print(f"         ❌ Extraction impossible (IA et fallback ont échoué)")
                    summary['errors'].append(f"{filename}: Extraction impossible")
                    continue
                
                # Ajouter les infos de l'email si l'email n'est pas vide
                if not cv_data.get('email') and email_data['sender_email']:
                    cv_data['email'] = email_data['sender_email']
                
                if not cv_data.get('prenom') and email_data['sender_name']:
                    parts = email_data['sender_name'].split()
                    if len(parts) > 1:
                        cv_data['prenom'] = parts[0]
                        cv_data['nom'] = ' '.join(parts[1:])
                    else:
                        cv_data['prenom'] = email_data['sender_name']
                
                # Étape 3c: Vérifier si le candidat existe déjà
                from cv_extractor import candidate_exists
                if candidate_exists(cv_data):
                    print(f"         ℹ️  Candidat déjà présent (doublon)")
                    summary['errors'].append(f"{filename}: Candidat déjà présent")
                    continue
                
                # Étape 3d: Ajouter à la base de données
                print(f"         💾 Ajout à la base de données...")
                if add_candidate_to_database(cv_data):
                    print(f"         ✅ {cv_data['prenom']} {cv_data['nom']} ajouté(e)")
                    summary['cvs_added'] += 1
                    summary['candidates_added'].append({
                        'nom': cv_data['nom'],
                        'prenom': cv_data['prenom'],
                        'email': cv_data['email'],
                        'poste': cv_data['poste']
                    })
                else:
                    print(f"         ❌ Erreur lors de l'ajout")
                    summary['errors'].append(f"{filename}: Erreur lors de l'ajout à la BD")
            
            except Exception as e:
                print(f"         ❌ Erreur: {str(e)[:50]}")
                summary['errors'].append(f"{filename}: {str(e)}")
        
        # Marquer l'email comme traité
        try:
            mark_email_as_processed(mail, email_data['msg_id'])
        except:
            pass
    
    # Fermer la connexion
    mail.close()
    
    # Afficher le résumé
    print("\n" + "="*70)
    print("  📊 RÉSUMÉ DE LA SYNCHRONISATION")
    print("="*70)
    print(f"\n  Connexion: {'✅ Réussie' if summary['connected'] else '❌ Échouée'}")
    print(f"  Emails trouvés: {summary['emails_found']}")
    print(f"  CVs traités: {summary['cvs_processed']}")
    print(f"  Candidats ajoutés: {summary['cvs_added']} ✅")
    
    if summary['candidates_added']:
        print(f"\n  📝 Candidats ajoutés:")
        for cand in summary['candidates_added']:
            print(f"     • {cand['prenom']} {cand['nom']} - {cand['poste']}")
    
    if summary['errors']:
        print(f"\n  ⚠️  Erreurs ({len(summary['errors'])}):")
        for error in summary['errors'][:5]:
            print(f"     • {error}")
        if len(summary['errors']) > 5:
            print(f"     ... et {len(summary['errors']) - 5} autres")
    
    print("\n" + "="*70 + "\n")
    
    return summary

def save_sync_history(summary: Dict) -> bool:
    """
    Sauvegarde l'historique de synchronisation.
    
    Args:
        summary: Résumé de la synchronisation
    
    Returns:
        True si succès
    """
    from datetime import datetime
    
    try:
        history_file = 'data/sync_history.json'
        
        # Charger l'historique existant
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # Ajouter la nouvelle entrée
        entry = {
            'timestamp': datetime.now().isoformat(),
            'emails_found': summary['emails_found'],
            'cvs_processed': summary['cvs_processed'],
            'cvs_added': summary['cvs_added'],
            'candidates_added': summary['candidates_added']
        }
        
        history.append(entry)
        
        # Sauvegarder
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return True
    except:
        return False

import os

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("  🚀 OUTIL DE SYNCHRONISATION DES EMAILS - SMART-HIRE")
    print("="*70)
    
    print("\n⚙️  Configuration requise:")
    print("   • Email d'accès à la boîte mail")
    print("   • Mot de passe d'application (si 2FA activé)")
    print("   • Serveur IMAP")
    
    # Récupérer les paramètres
    print("\n" + "-"*70)
    email_address = input("\n📧 Email de la boîte mail: ").strip()
    app_password = input("🔐 Mot de passe d'application: ").strip()
    imap_server_input = input("🌐 Serveur IMAP (défaut: imap.gmail.com): ").strip()
    
    imap_server = imap_server_input if imap_server_input else "imap.gmail.com"
    
    # Lancer la synchronisation
    print("\n" + "-"*70)
    summary = sync_emails_with_database(email_address, app_password, imap_server)
    
    # Sauvegarder l'historique
    save_sync_history(summary)
    
    # Code de sortie
    sys.exit(0 if summary['cvs_added'] > 0 else 1)
