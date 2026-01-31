# 🚀 Guide de Déploiement Microsoft Teams - Smart-Hire Bot

## 📋 Prérequis

### 1. Comptes et Abonnements
- ✅ Compte Microsoft 365 avec droits administrateur
- ✅ Abonnement Azure actif
- ✅ Accès au portail Azure (portal.azure.com)
- ✅ Accès au Teams Admin Center

### 2. Outils Nécessaires
```powershell
# Installer Azure CLI
winget install Microsoft.AzureCLI

# Installer Bot Framework CLI
npm install -g @microsoft/botframework-cli

# Installer Teams Toolkit (optionnel)
# Via VS Code Extension: Teams Toolkit
```

## 🔧 Étape 1 : Enregistrer le Bot dans Azure

### 1.1 Créer une Azure Bot Service
```bash
# Se connecter à Azure
az login

# Créer un groupe de ressources
az group create --name smart-hire-rg --location westeurope

# Créer l'Azure Bot
az bot create \
  --resource-group smart-hire-rg \
  --name smart-hire-bot \
  --kind registration \
  --sku F0 \
  --appid {MICROSOFT_APP_ID} \
  --password {MICROSOFT_APP_PASSWORD}
```

### 1.2 Enregistrer l'Application Azure AD
1. Aller sur https://portal.azure.com
2. **Azure Active Directory** → **App registrations** → **New registration**
3. Renseigner :
   - **Name** : Smart-Hire Bot
   - **Supported account types** : Multitenant
   - **Redirect URI** : Laisser vide pour le moment
4. Copier l'**Application (client) ID** → `{MICROSOFT_APP_ID}`
5. **Certificates & secrets** → **New client secret**
6. Copier la **Value** → `{MICROSOFT_APP_PASSWORD}`

## 🌐 Étape 2 : Déployer l'Application

### 2.1 Créer un App Service
```bash
# Créer un App Service Plan
az appservice plan create \
  --name smart-hire-plan \
  --resource-group smart-hire-rg \
  --sku B1 \
  --is-linux

# Créer le Web App
az webapp create \
  --resource-group smart-hire-rg \
  --plan smart-hire-plan \
  --name smart-hire-api \
  --runtime "PYTHON:3.11"
```

### 2.2 Configurer les Variables d'Environnement
```bash
az webapp config appsettings set \
  --resource-group smart-hire-rg \
  --name smart-hire-api \
  --settings \
    MICROSOFT_APP_ID="{YOUR_APP_ID}" \
    MICROSOFT_APP_PASSWORD="{YOUR_APP_PASSWORD}" \
    AZURE_TENANT_ID="{YOUR_TENANT_ID}" \
    OLLAMA_URL="http://your-ollama-server:11434" \
    SMTP_SERVER="smtp.gmail.com" \
    SMTP_PORT="587"
```

### 2.3 Déployer le Code
```bash
# Créer un fichier .zip avec le code
# Exclure : venv/, __pycache__/, .env, .git/

# Déployer via Azure CLI
az webapp deploy \
  --resource-group smart-hire-rg \
  --name smart-hire-api \
  --src-path smart-hire-bot.zip \
  --type zip
```

**OU via Git :**
```bash
# Configurer Git deployment
az webapp deployment source config-local-git \
  --name smart-hire-api \
  --resource-group smart-hire-rg

# Ajouter Azure remote et push
git remote add azure https://{username}@smart-hire-api.scm.azurewebsites.net/smart-hire-api.git
git push azure main
```

## 🤖 Étape 3 : Configurer le Bot

### 3.1 Définir le Messaging Endpoint
1. Aller sur **Azure Portal** → **Bot Services** → **smart-hire-bot**
2. **Configuration** → **Messaging endpoint**
3. Entrer : `https://smart-hire-api.azurewebsites.net/api/messages`
4. **Apply**

### 3.2 Activer le Canal Teams
1. **Channels** → **Microsoft Teams**
2. Cliquer sur **Microsoft Teams** pour l'activer
3. **Accept** les termes
4. Le canal Teams est maintenant actif ✅

## 📦 Étape 4 : Préparer le Package Teams

### 4.1 Structure du Package
```
smart-hire-teams-package/
├── manifest.json          # Fichier teams_manifest.json renommé
├── icon-color.png         # Icône 192x192px
└── icon-outline.png       # Icône 32x32px (transparente)
```

### 4.2 Créer les Icônes
- **icon-color.png** : 192x192px, couleur de marque (#667eea)
- **icon-outline.png** : 32x32px, contour blanc sur transparent

### 4.3 Mettre à Jour le Manifest
```json
// Dans teams_manifest.json, remplacer :
{
  "id": "VOTRE_MICROSOFT_APP_ID",
  "developer": {
    "websiteUrl": "https://smart-hire-api.azurewebsites.net",
    // ...
  },
  "bots": [
    {
      "botId": "VOTRE_MICROSOFT_APP_ID",
      // ...
    }
  ],
  "validDomains": [
    "smart-hire-api.azurewebsites.net"
  ]
}
```

### 4.4 Créer le Package .zip
```powershell
# Zipper les 3 fichiers à la racine
Compress-Archive -Path manifest.json, icon-color.png, icon-outline.png -DestinationPath smart-hire-teams-app.zip
```

## 📥 Étape 5 : Installer dans Teams

### Option A : Installation pour Tests
1. Ouvrir **Microsoft Teams**
2. **Apps** → **Manage your apps** → **Upload a custom app**
3. Sélectionner `smart-hire-teams-app.zip`
4. **Add** pour l'installer en mode personnel

### Option B : Publication Organisationnelle
1. Aller sur **Teams Admin Center** (admin.teams.microsoft.com)
2. **Teams apps** → **Manage apps** → **Upload**
3. Uploader `smart-hire-teams-app.zip`
4. **Publish** pour le rendre disponible à l'organisation
5. Les utilisateurs peuvent maintenant l'installer depuis le catalogue d'entreprise

## ✅ Étape 6 : Tester le Bot

### 6.1 Tests de Base
Dans Teams, taper les commandes suivantes :
```
Bonjour
Recherche développeur Python
Voir les candidats
Aide
```

### 6.2 Tests Avancés
- Upload d'un CV (PDF)
- Génération de contrat
- Envoi d'invitation
- Publication LinkedIn

### 6.3 Vérifier les Logs
```bash
# Voir les logs en temps réel
az webapp log tail \
  --resource-group smart-hire-rg \
  --name smart-hire-api
```

## 🔍 Étape 7 : Monitoring

### 7.1 Activer Application Insights
```bash
# Créer Application Insights
az monitor app-insights component create \
  --app smart-hire-insights \
  --location westeurope \
  --resource-group smart-hire-rg \
  --application-type web

# Lier au Web App
az webapp config appsettings set \
  --resource-group smart-hire-rg \
  --name smart-hire-api \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="{INSTRUMENTATION_KEY}"
```

### 7.2 Dashboard de Monitoring
- **Azure Portal** → **Application Insights** → **smart-hire-insights**
- Voir : Requests, Failures, Performance, Usage

## 🛡️ Sécurité

### Bonnes Pratiques
```bash
# Stocker les secrets dans Azure Key Vault
az keyvault create \
  --name smart-hire-vault \
  --resource-group smart-hire-rg \
  --location westeurope

# Ajouter un secret
az keyvault secret set \
  --vault-name smart-hire-vault \
  --name "MicrosoftAppPassword" \
  --value "{YOUR_PASSWORD}"

# Donner accès au Web App
az webapp identity assign \
  --resource-group smart-hire-rg \
  --name smart-hire-api
```

## 🔄 Mise à Jour du Bot

### Déploiement Continu (CI/CD)
```yaml
# azure-pipelines.yml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- task: ArchiveFiles@2
  inputs:
    rootFolderOrFile: '$(System.DefaultWorkingDirectory)'
    includeRootFolder: false
    archiveType: 'zip'
    archiveFile: '$(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip'

- task: AzureWebApp@1
  inputs:
    azureSubscription: 'Azure Subscription'
    appName: 'smart-hire-api'
    package: '$(Build.ArtifactStagingDirectory)/*.zip'
```

## 📞 Support et Dépannage

### Problèmes Courants

**Bot ne répond pas :**
- Vérifier le messaging endpoint dans Azure Bot Service
- Vérifier que l'App Service est en cours d'exécution
- Consulter les logs : `az webapp log tail`

**Erreur d'authentification :**
- Vérifier MICROSOFT_APP_ID et MICROSOFT_APP_PASSWORD
- S'assurer que le secret n'a pas expiré

**Commands ne s'affichent pas :**
- Vérifier la structure du manifest.json
- Réinstaller l'app dans Teams

### Logs Utiles
```bash
# Logs du Web App
az webapp log download --resource-group smart-hire-rg --name smart-hire-api

# Diagnostics
az webapp browse --resource-group smart-hire-rg --name smart-hire-api
```

## 📚 Ressources

- [Bot Framework Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Teams Platform Documentation](https://docs.microsoft.com/en-us/microsoftteams/platform/)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Teams App Manifest Schema](https://docs.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)

---

✅ **Déploiement terminé !** Votre bot Smart-Hire est maintenant accessible dans Microsoft Teams.
