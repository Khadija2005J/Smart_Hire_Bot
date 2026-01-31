import imaplib
import email
from email.header import decode_header
import os
from typing import List, Dict, Tuple
import io

def connect_to_email(email_address: str, password: str, imap_server: str = "imap.gmail.com") -> imaplib.IMAP4_SSL:
    """
    Établit une connexion IMAP à la boîte mail.
    
    Args:
        email_address: Adresse email
        password: Mot de passe ou mot de passe d'application
        imap_server: Serveur IMAP (défaut: Gmail)
    
    Returns:
        Connexion IMAP établie
    """
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"Erreur de connexion: {e}")
        return None

def get_attachment_info(msg) -> List[Dict]:
    """
    Extrait les informations des pièces jointes d'un email.
    
    Args:
        msg: Message email
    
    Returns:
        Liste des pièces jointes avec leur contenu
    """
    attachments = []
    
    for part in msg.walk():
        content_disposition = part.get_content_disposition()
        filename = part.get_filename()
        
        # Log détaillé pour debug
        if filename:
            print(f"      🔍 Fichier trouvé: {filename}")
            print(f"         Type: {part.get_content_type()}")
            print(f"         Disposition: {content_disposition}")
        
        if content_disposition == "attachment" or filename:
            if filename:
                # Accepter plus d'extensions de fichiers
                valid_extensions = ['.pdf', '.txt', '.doc', '.docx', '.odt', '.rtf']
                is_valid = any(filename.lower().endswith(ext) for ext in valid_extensions)
                
                print(f"         Extension valide: {is_valid}")
                
                if is_valid:
                    try:
                        content = part.get_payload(decode=True)
                        attachments.append({
                            'filename': filename,
                            'content': content,
                            'content_type': part.get_content_type()
                        })
                        print(f"         ✅ Fichier ajouté comme CV")
                    except Exception as e:
                        print(f"         ❌ Erreur extraction: {e}")
                else:
                    print(f"         ⚠️  Extension non supportée")
    
    return attachments

def extract_sender_info(msg) -> Tuple[str, str]:
    """
    Extrait le nom et l'email de l'expéditeur.
    
    Args:
        msg: Message email
    
    Returns:
        Tuple (email, nom)
    """
    from_header = msg.get("From", "")
    
    # Parser le header From
    if "<" in from_header:
        # Format: "Nom <email@example.com>"
        email_addr = from_header.split("<")[1].split(">")[0]
        name = from_header.split("<")[0].strip().strip('"')
    else:
        # Format: "email@example.com"
        email_addr = from_header.strip()
        name = email_addr.split("@")[0]
    
    return email_addr, name

def fetch_cv_emails(mail: imaplib.IMAP4_SSL, unread_only: bool = False) -> List[Dict]:
    """
    Récupère les emails contenant des CV.
    
    Args:
        mail: Connexion IMAP
        unread_only: Ne récupérer que les emails non lus (défaut: False = tous les emails)
    
    Returns:
        Liste des emails avec CVs trouvés
    """
    emails_with_cv = []
    
    try:
        # Sélectionner la boîte de réception
        mail.select("INBOX")
        
        # Chercher les emails
        if unread_only:
            status, messages = mail.search(None, "UNSEEN")
            print(f"   📧 Mode: Emails non lus uniquement")
        else:
            # Chercher TOUS les emails pour trouver les CVs
            status, messages = mail.search(None, "ALL")
            print(f"   📧 Mode: Tous les emails")
        
        if status != "OK":
            print("   ❌ Erreur lors de la recherche des emails")
            return emails_with_cv
        
        message_ids = messages[0].split()
        total_emails = len(message_ids)
        print(f"   📬 {total_emails} email(s) total dans la boîte de réception")
        
        # Traiter les 100 derniers emails pour être sûr
        recent_ids = message_ids[-100:] if len(message_ids) > 100 else message_ids
        print(f"   🔍 Analyse des {len(recent_ids)} emails les plus récents...")
        
        attachments_found = 0
        
        for msg_id in recent_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            try:
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Récupérer les infos de l'expéditeur
                sender_email, sender_name = extract_sender_info(msg)
                
                # Récupérer les pièces jointes
                attachments = get_attachment_info(msg)
                
                # Si des CVs trouvés
                if attachments:
                    attachments_found += 1
                    subject = msg.get("Subject", "Sans sujet")
                    
                    # Décoder le sujet s'il est encodé
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    
                    emails_with_cv.append({
                        'msg_id': msg_id,
                        'sender_email': sender_email,
                        'sender_name': sender_name,
                        'subject': subject,
                        'attachments': attachments,
                        'date': msg.get("Date", "")
                    })
                    print(f"      ✅ CV trouvé: {sender_name} - {attachments[0]['filename']}")
            
            except Exception as e:
                print(f"   ⚠️  Erreur message {msg_id}: {str(e)[:50]}")
        
        print(f"   📊 Résultat: {attachments_found} email(s) avec pièces jointes CV")
        
        return emails_with_cv
    
    except Exception as e:
        print(f"   ❌ Erreur lors de la récupération: {e}")
        return emails_with_cv

def mark_email_as_processed(mail: imaplib.IMAP4_SSL, msg_id: bytes) -> bool:
    """
    Marque un email comme traité en le déplaçant ou en lui ajoutant un flag.
    
    Args:
        mail: Connexion IMAP
        msg_id: ID du message
    
    Returns:
        True si succès, False sinon
    """
    try:
        mail.store(msg_id, '+FLAGS', '\\Seen')
        return True
    except Exception as e:
        print(f"Erreur lors du marquage de l'email: {e}")
        return False

def get_email_config_suggestions() -> Dict:
    """
    Retourne les configurations IMAP pour les providers populaires.
    
    Returns:
        Dictionnaire avec les configurations
    """
    return {
        "Gmail": {
            "imap_server": "imap.gmail.com",
            "port": 993,
            "info": "Utilisez un mot de passe d'application (2FA requis)"
        },
        "Outlook/Hotmail": {
            "imap_server": "imap-mail.outlook.com",
            "port": 993,
            "info": "Activez l'authentification par application"
        },
        "Yahoo": {
            "imap_server": "imap.mail.yahoo.com",
            "port": 993,
            "info": "Utilisez un mot de passe d'application"
        },
        "ProtonMail": {
            "imap_server": "imap.protonmail.com",
            "port": 993,
            "info": "IMAP/SMTP optionnel, utilisez le mot de passe du compte"
        }
    }
