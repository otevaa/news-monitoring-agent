# Agent de Veille Automatique avec IA

## 🎯 Qu'est-ce que l'application ?

Cet agent de veille automatique est un système intelligent conçu pour surveiller et collecter automatiquement des contenus récents sur des sujets spécifiques. L'application utilise l'intelligence artificielle pour améliorer la pertinence des résultats de recherche.

### 🧠 Fonctionnement avec l'IA

**Expansion intelligente des mots-clés :**
- L'IA (via OpenRouter) analyse vos mots-clés initiaux
- Elle génère automatiquement des termes connexes, synonymes et variations
- Cela améliore considérablement la pertinence et la couverture de votre veille
- Exemple : "IA" → "Intelligence Artificielle", "Machine Learning", "Deep Learning", "AI", "Artificial Intelligence"

**Remplissage automatique des feuilles de calcul :**
- Connexion sécurisée à votre compte Google via OAuth 2.0
- Création automatique de feuilles Google Sheets structurées
- Sauvegarde des articles avec métadonnées complètes (titre, URL, source, date)
- Mise à jour en temps réel selon la fréquence configurée

### 🔧 Architecture technique

- **Backend** : Flask (Python)
- **IA** : OpenRouter API (modèle DeepSeek R1 gratuit)
- **Stockage** : Google Sheets via API Google
- **Authentification** : OAuth 2.0 Google
- **Déploiement** : Compatible Docker et Render.com

## 🚀 Installation

### Prérequis
- Python 3.12+
- Un compte Google
- Une clé API OpenRouter (gratuite)

### 1. Cloner le dépôt
```bash
git clone https://github.com/Neriya98/news-monitoring-agent.git
cd news-monitoring-agent
```

### 2. Configurer l'environnement Python
```bash
# Installer uv (gestionnaire de paquets rapide)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Créer un environnement virtuel
uv venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances
uv pip install -r requirements.txt
```

### 3. Obtenir les clés API Google

#### 3.1 Créer un projet Google Cloud
1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un existant
3. Activez les APIs suivantes :
   - Google Sheets API
   - Google Drive API
   - Google OAuth 2.0

#### 3.2 Créer les identifiants OAuth
1. Dans Google Cloud Console → "APIs & Services" → "Credentials"
2. Cliquez sur "CREATE CREDENTIALS" → "OAuth 2.0 Client IDs"
3. Choisissez "Web application"
4. Ajoutez les URLs de redirection :
   - `http://localhost:5000/oauth2callback` (pour le développement local)
5. Téléchargez le fichier JSON et renommez-le `client_secret.json`
6. Placez-le dans le dossier racine du projet

### 4. Obtenir une clé API OpenRouter
1. Visitez [OpenRouter](https://openrouter.ai/)
2. Créez un compte gratuit
3. Récupérez votre clé API depuis le dashboard

### 5. Configurer les variables d'environnement
```bash
# Créer le fichier .env
touch .env

# Éditer le fichier .env avec vos clés
GOOGLE_CLIENT_ID=votre_client_id_google
GOOGLE_CLIENT_SECRET=votre_client_secret_google
FLASK_SECRET_KEY=votre_cle_secrete_flask
OPENROUTER_API_KEY=votre_cle_openrouter
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback
```

### 6. Lancer l'application
```bash
python app.py
```

L'application sera accessible sur `http://localhost:5000`

## 📋 Comment utiliser l'application

### Démarrage et création de campagne

1. **Lancement** : Ouvrez `http://localhost:5000` dans votre navigateur
2. **Redirection automatique** : Vous serez redirigé vers la page de création de campagne
3. **Authentification Google** : Connectez-vous avec votre compte Google pour autoriser l'accès aux Google Sheets

### Processus de création d'une campagne

1. **Nom de la campagne** : Donnez un nom descriptif à votre campagne
2. **Mots-clés** : Entrez vos mots-clés séparés par des virgules
   - L'IA les étoffera automatiquement
   - Exemple : "cybersécurité, hacking"
3. **Fréquence** : Choisissez la fréquence de surveillance :
   - Toutes les 15 minutes
   - Toutes les heures
   - Quotidienne
   - Hebdomadaire
4. **Nombre d'articles** : Définissez le nombre maximum d'articles à collecter
5. **Validation** : Cliquez sur "Créer la campagne"

### Fonctionnalités avancées

#### Changer le modèle d'IA
1. Allez dans **Profil** → **Paramètres IA**
2. Sélectionnez parmi les modèles disponibles :
   - DeepSeek R1 (gratuit, recommandé)
   - GPT-3.5 Turbo
   - GPT-4
   - Claude 3 Haiku
3. Sauvegardez vos préférences

#### Visualiser les feuilles de calcul créées
1. **Dashboard** → **Campagnes actives**
2. Cliquez sur "Voir la feuille" pour chaque campagne
3. Accès direct aux Google Sheets avec tous les articles collectés

#### Supprimer des feuilles de calcul
1. **Dashboard** → **Gestion des fichiers**
2. Sélectionnez les feuilles à supprimer
3. Confirmez la suppression
4. Les feuilles seront supprimées de votre Google Drive

### Structure des données collectées

Chaque article est sauvegardé avec les métadonnées suivantes :
- **Titre** : Titre de l'article
- **URL** : Lien vers l'article complet
- **Source** : Site web ou plateforme d'origine
- **Date** : Date de publication
- **Mots-clés** : Mots-clés qui ont déclenché la collecte
- **Résumé** : Extrait ou description courte

## 🔮 Fonctionnalités prévues (non implémentées)

En raison de contraintes de temps, certaines fonctionnalités avancées n'ont pas pu être intégrées :

### 🎤 Commandes vocales
- Création de campagnes par commande vocale
- Consultation des résultats à l'oral
- Interface conversationnelle

### 📱 Responsiveness mobile
- Interface optimisée pour smartphones et tablettes
- Application mobile native
- Notifications push

### 🔗 Connexion Airtable
- Alternative à Google Sheets
- Synchronisation bidirectionnelle
- Gestion avancée des bases de données

### ✏️ Modification complète des campagnes
- Édition des mots-clés après création
- Modification de la fréquence en temps réel
- Historique des modifications

### 🌐 Intégration Google complète en production
- Authentification Google sur Render.com
- Gestion des domaines personnalisés
- Certificats SSL automatiques

## 🎯 Choix techniques

### OpenRouter vs APIs directes
- **Avantage** : Accès unifié à plusieurs modèles d'IA
- **Coût** : Tier gratuit disponible avec DeepSeek R1
- **Flexibilité** : Changement de modèle sans refactorisation

### Google Sheets vs Airtable
- **Accessibilité** : Plus familier pour les utilisateurs
- **Intégration** : OAuth 2.0 natif et API robuste
- **Coût** : Gratuit avec compte Google

### Flask vs FastAPI
- **Simplicité** : Démarrage rapide et documentation extensive
- **Écosystème** : Nombreuses extensions disponibles
- **Stabilité** : Framework mature et éprouvé

### uv vs pip
- **Performance** : Installation 10x plus rapide
- **Fiabilité** : Résolution de dépendances améliorée
- **Modernité** : Outil de nouvelle génération

## 🚀 Déploiement

### Déploiement local (recommandé)
```bash
python app.py
```

### Docker
```bash
docker build -t news-monitor .
docker run -p 5000:5000 news-monitor
```

### Render.com
1. Connectez votre dépôt GitHub
2. Configurez les variables d'environnement
3. Déployez automatiquement

Toutefois, cette option n'est pas totalement opérationnelle. Des difficultés à générer les fichiers d'authentification. Lien vers mon déploiement: [text](https://news-monitoring-agent-izby.onrender.com)

## 📂 Project Structure

```
news-monitoring-agent/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables 
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile           # Docker container configuration
├── render.yaml          # Render.com deployment config
├── nginx.conf           # Nginx configuration for production
├── agent/
│   ├── __init__.py
│   ├── ai_keyword_expander.py    # OpenRouter AI 
│   ├── fetch_multi_source.py     # Multi-source article 
│   ├── google_oauth.py           # Google OAuth 
│   ├── campaign_manager.py       # Campaign management
│   ├── integrations.py           # Integration management
│   ├── scheduler.py              # Background task scheduling
│   ├── google_sheets_manager.py  # Google Sheets integration
│   ├── user_profile_manager.py   # User settings management
│   └── async_campaign_manager.py # Async campaign processing
├── static/
│   ├── style.css         # Application styling
│   └── app.js           # Frontend JavaScript
├── templates/
│   ├── dashboard.html    # Main dashboard
│   ├── campaigns.html    # Campaign management
│   ├── campaign_form.html # Campaign creation/editing
│   ├── integrations.html # Integration setup
│   └── profile.html      # User profile and AI settings
└── README.md            # This file
```
