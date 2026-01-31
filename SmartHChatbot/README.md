# 🎯 Smart-Hire - Application de Recrutement Intelligent

Watch the demo video here:  
👉 https://youtu.be/yutaDIqKAkw?si=8ZhCdikVQW-y4Ozz

Application de recrutement automatisée utilisant l'IA (Ollama) pour matcher les candidats avec les besoins des recruteurs.

## 📋 Fonctionnalités

1. **Input Recruteur** : Interface pour décrire les besoins en recrutement
2. **Matching IA** : Utilise Ollama (Mistral/Llama3) pour analyser les CV et trouver les meilleurs candidats
3. **Affichage des résultats** : Cartes de candidats avec scores de matching
4. **Envoi d'emails** : Invitations automatiques aux entretiens
5. **Génération de contrats** : Création de contrats de travail personnalisés

## 🚀 Installation

### Prérequis

- Python 3.8 ou supérieur
- Ollama installé et en cours d'exécution

### Installation d'Ollama

1. Téléchargez Ollama depuis [https://ollama.ai](https://ollama.ai)
2. Installez le modèle Llama 3.2 :
   ```bash
   ollama pull llama3.2
   ```
3. Démarrez le serveur Ollama :
   ```bash
   ollama serve
   ```

### Installation de l'application

1. Clonez ou téléchargez ce projet
2. Installez les dépendances Python :
   ```powershell
   pip install -r requirements.txt
   ```

## 🎮 Utilisation

### Démarrage de l'application

```powershell
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

### Configuration Email

Pour envoyer des emails, vous devez configurer vos identifiants dans la barre latérale :

**Pour Gmail :**
1. Activez la validation en deux étapes sur votre compte Google
2. Générez un mot de passe d'application : [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Utilisez ce mot de passe dans l'application (pas votre mot de passe Gmail)
4. Serveur SMTP : `smtp.gmail.com`
5. Port : `587`

**Pour Outlook/Hotmail :**
- Serveur SMTP : `smtp-mail.outlook.com`
- Port : `587`

### Flux de travail

1. **Décrivez votre besoin** : Entrez une description du poste (ex: "4 développeurs Python avec Django")
2. **Recherche** : Cliquez sur "Rechercher les candidats" pour lancer l'analyse IA
3. **Sélection** : Examinez les candidats recommandés et confirmez ceux qui vous intéressent
4. **Planification** : Définissez la date et l'heure de l'entretien
5. **Invitation** : Envoyez les emails d'invitation automatiquement
6. **Contrat** : Générez un contrat pour les candidats retenus

## 📁 Structure du projet

```
Smart-Hire/
│
├── app.py                      # Application Streamlit principale
├── matching.py                 # Logique de matching avec Ollama
├── email_sender.py             # Envoi d'emails automatiques
├── contract_generator.py       # Génération de contrats
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation
│
├── data/
│   └── cv_data.json           # Base de données des CV (exemple)
│
└── contracts/                  # Dossier pour les contrats générés
```

## 🔧 Configuration avancée

### Modifier le modèle IA

Dans [matching.py](matching.py#L56), vous pouvez changer le modèle utilisé :

```python
"model": "llama3.2",  # ou "mistral", "llama3.1" ou tout autre modèle Ollama
```

### Personnaliser les CV

Modifiez [data/cv_data.json](data/cv_data.json) pour ajouter vos propres candidats. Structure :

```json
{
  "id": 1,
  "nom": "Nom",
  "prenom": "Prénom",
  "email": "email@example.com",
  "telephone": "+33 6 12 34 56 78",
  "poste": "Titre du poste",
  "experience": 5,
  "formation": "Formation",
  "competences": ["Python", "Django", "..."],
  "langues": ["Français", "Anglais"],
  "cv_url": "https://...",
  "linkedin": "https://...",
  "disponibilite": "Immédiate"
}
```

## 🐛 Dépannage

### Erreur "Impossible de se connecter à Ollama"

1. Vérifiez qu'Ollama est bien démarré : `ollama serve`
2. Testez la connexion : `curl http://localhost:11434/api/tags`
3. Assurez-vous qu'un modèle est installé : `ollama list`

### Erreur d'authentification email

1. Utilisez un mot de passe d'application (pas votre mot de passe principal)
2. Vérifiez que votre compte autorise les applications moins sécurisées
3. Essayez avec un autre serveur SMTP

### L'application ne trouve pas cv_data.json

Assurez-vous que le fichier `data/cv_data.json` existe dans le dossier du projet.

## 📝 Notes importantes

- **Sécurité** : Ne partagez jamais vos mots de passe email. Utilisez des variables d'environnement pour la production.
- **RGPD** : Assurez-vous d'avoir le consentement des candidats avant de traiter leurs données.
- **Test** : Testez d'abord avec votre propre email avant d'envoyer aux candidats.

## 🎓 Exemples de requêtes

- "4 développeurs Python avec expérience en Django et FastAPI"
- "Un Data Scientist avec expertise en Machine Learning"
- "Développeur Full-Stack junior disponible immédiatement"
- "Ingénieur DevOps avec compétences AWS et Kubernetes"

## 📄 Licence

Ce projet est fourni à titre éducatif. Libre à vous de l'adapter à vos besoins.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à améliorer le code ou à ajouter de nouvelles fonctionnalités.

---

**Bon recrutement avec Smart-Hire ! 🎯**
