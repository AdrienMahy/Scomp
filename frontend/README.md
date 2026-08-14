# 🎮 Scomp Frontend

Interface React simple pour afficher les jeux et fichiers de sortie stockés en base de données.

## 📋 Fonctionnalités

- ✅ Liste des jeux avec score et détails
- ✅ Affichage détaillé de chaque jeu
- ✅ Liste des fichiers de sortie par jeu
- ✅ Filtrage par type de fichier (XML, JSON, etc.)
- ✅ Affichage des URLs S3 pré-signées
- ✅ Statut des fichiers (disponible, obsolète, version)

## 🚀 Installation & Lancement

### Prérequis
- Node.js 18+
- npm ou yarn
- Backend Scomp en cours d'exécution sur `http://localhost:8001`

### Installation
```bash
cd frontend
npm install
```

### Développement
```bash
npm run dev
```

L'app sera disponible sur `http://localhost:3000`

### Build Production
```bash
npm run build
npm run preview
```

## 📁 Structure du Projet

```
frontend/
├── src/
│   ├── App.jsx                    # Composant principal
│   ├── App.css
│   ├── main.jsx                   # Entry point
│   ├── index.css                  # Styles globaux
│   ├── pages/
│   │   ├── GamesList.jsx          # Liste des jeux
│   │   └── GameDetail.jsx         # Détail d'un jeu
│   └── styles/
│       ├── GamesList.css
│       └── GameDetail.css
├── index.html
├── vite.config.js
├── package.json
└── .gitignore
```

## 🔄 Fonctionnement

### GamesList
- Affiche tous les jeux de la DB
- Click sur une carte → ouvre les détails
- Affiche le score et le nombre de fichiers

### GameDetail
- Affiche tous les détails du jeu
- Liste les fichiers de sortie (XML, JSON)
- Filtre par type de fichier
- Affiche les URLs S3 complètes
- Indique les statuts (disponible, obsolète, version)

## 🔌 API Backend

L'app consomme ces endpoints :

- `GET /games` - Liste tous les jeux
- `GET /games/{game_id}` - Détail d'un jeu

## 🎨 Style

- Gradient violet/bleu
- Design responsive
- Cartes interactives
- Dark theme header

## 📝 Notes

- Frontend lit-only (pas de POST/scrape)
- CORS proxy configuré dans vite.config.js
- Backend doit être accessible sur `http://localhost:8001`

## 🔗 Dépendances

- **React** - UI library
- **Axios** - HTTP client
- **Vite** - Build tool
