import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

def send_interview_email(
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    candidate_name: str,
    interview_date: datetime,
    location: str,
    duration: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587
) -> bool:
    """
    Envoie un email d'invitation à un entretien à un candidat.
    
    Args:
        sender_email: Email de l'expéditeur (recruteur)
        sender_password: Mot de passe de l'email (ou mot de passe d'application)
        recipient_email: Email du candidat
        candidate_name: Nom complet du candidat
        interview_date: Date et heure de l'entretien
        location: Lieu de l'entretien
        duration: Durée de l'entretien
        smtp_server: Serveur SMTP à utiliser
        smtp_port: Port SMTP
    
    Returns:
        True si l'email a été envoyé avec succès, False sinon
    """
    
    # Créer le message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Invitation à un entretien - Smart-Hire"
    message["From"] = sender_email
    message["To"] = recipient_email
    
    # Formater la date
    date_str = interview_date.strftime("%d/%m/%Y à %H:%M")
    
    # Corps de l'email en texte brut
    text_body = f"""
Bonjour {candidate_name},

Nous avons le plaisir de vous informer que votre candidature a retenu notre attention.

Nous souhaiterions vous rencontrer pour un entretien afin d'échanger sur votre parcours et le poste proposé.

Détails de l'entretien:
━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: {date_str}
📍 Lieu: {location}
⏱️ Durée: {duration}

Merci de confirmer votre présence en répondant à cet email.

Si cet horaire ne vous convient pas, n'hésitez pas à nous proposer d'autres créneaux.

Nous vous prions de bien vouloir apporter:
• Une pièce d'identité
• Un CV à jour
• Vos diplômes

Nous restons à votre disposition pour toute question.

Cordialement,
L'équipe Smart-Hire

━━━━━━━━━━━━━━━━━━━━━━━━━━
Smart-Hire - Recrutement Intelligent
Email: {sender_email}
    """
    
    # Corps de l'email en HTML
    html_body = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
          }}
          .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 10px;
          }}
          .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 10px 10px 0 0;
          }}
          .content {{
            background-color: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
          }}
          .info-box {{
            background-color: #e8f5e9;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 20px 0;
          }}
          .info-item {{
            margin: 10px 0;
            font-size: 16px;
          }}
          .icon {{
            margin-right: 10px;
          }}
          .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
          }}
          .checklist {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
          }}
          ul {{
            margin: 10px 0;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🎯 Smart-Hire</h1>
            <p>Invitation à un entretien</p>
          </div>
          
          <div class="content">
            <p>Bonjour <strong>{candidate_name}</strong>,</p>
            
            <p>Nous avons le plaisir de vous informer que <strong>votre candidature a retenu notre attention</strong>.</p>
            
            <p>Nous souhaiterions vous rencontrer pour un entretien afin d'échanger sur votre parcours et le poste proposé.</p>
            
            <div class="info-box">
              <h3 style="margin-top: 0;">📋 Détails de l'entretien</h3>
              <div class="info-item">
                <span class="icon">📅</span>
                <strong>Date:</strong> {date_str}
              </div>
              <div class="info-item">
                <span class="icon">📍</span>
                <strong>Lieu:</strong> {location}
              </div>
              <div class="info-item">
                <span class="icon">⏱️</span>
                <strong>Durée:</strong> {duration}
              </div>
            </div>
            
            <p>Merci de <strong>confirmer votre présence</strong> en répondant à cet email.</p>
            
            <p>Si cet horaire ne vous convient pas, n'hésitez pas à nous proposer d'autres créneaux.</p>
            
            <div class="checklist">
              <h3 style="margin-top: 0;">📝 À apporter le jour de l'entretien</h3>
              <ul>
                <li>Une pièce d'identité</li>
                <li>Un CV à jour</li>
                <li>Vos diplômes</li>
              </ul>
            </div>
            
            <p>Nous restons à votre disposition pour toute question.</p>
            
            <p>Cordialement,<br>
            <strong>L'équipe Smart-Hire</strong></p>
            
            <div class="footer">
              <p>Smart-Hire - Recrutement Intelligent<br>
              Email: {sender_email}</p>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    
    # Attacher les deux versions
    part1 = MIMEText(text_body, "plain")
    part2 = MIMEText(html_body, "html")
    
    message.attach(part1)
    message.attach(part2)
    
    try:
        # Connexion au serveur SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Sécuriser la connexion
        
        # Connexion avec les identifiants
        server.login(sender_email, sender_password)
        
        # Envoi de l'email
        server.sendmail(sender_email, recipient_email, message.as_string())
        
        # Fermeture de la connexion
        server.quit()
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        raise Exception("Erreur d'authentification. Vérifiez vos identifiants email.")
    except smtplib.SMTPException as e:
        raise Exception(f"Erreur SMTP: {str(e)}")
    except Exception as e:
        raise Exception(f"Erreur lors de l'envoi de l'email: {str(e)}")


def send_rejection_email(
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    candidate_name: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587
) -> bool:
    """
    Envoie un email de rejet poli à un candidat.
    
    Args:
        sender_email: Email de l'expéditeur (recruteur)
        sender_password: Mot de passe de l'email
        recipient_email: Email du candidat
        candidate_name: Nom complet du candidat
        smtp_server: Serveur SMTP à utiliser
        smtp_port: Port SMTP
    
    Returns:
        True si l'email a été envoyé avec succès
    """
    
    message = MIMEMultipart("alternative")
    message["Subject"] = "Réponse à votre candidature - Smart-Hire"
    message["From"] = sender_email
    message["To"] = recipient_email
    
    text_body = f"""
Bonjour {candidate_name},

Nous vous remercions pour l'intérêt que vous avez porté à notre entreprise et pour le temps consacré à votre candidature.

Après un examen attentif de votre profil, nous regrettons de vous informer que nous ne pourrons pas donner suite à votre candidature pour ce poste.

Cette décision ne remet pas en cause vos compétences. Nous avons simplement sélectionné des profils dont l'expérience correspondait davantage aux besoins spécifiques du poste.

Nous conservons votre CV dans notre base de données et ne manquerons pas de vous recontacter si un poste correspondant mieux à votre profil se présentait.

Nous vous souhaitons beaucoup de succès dans vos recherches.

Cordialement,
L'équipe Smart-Hire
    """
    
    part = MIMEText(text_body, "plain")
    message.attach(part)
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"Erreur lors de l'envoi de l'email: {str(e)}")
