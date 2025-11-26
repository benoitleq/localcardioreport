# ❤️ Générateur de Comptes-Rendus Cardiologiques

Application Streamlit pour générer automatiquement des comptes-rendus cardiologiques structurés à partir de fichiers PDF bruts, en utilisant un modèle LLM local (LM Studio).

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Fonctionnalités

- ✅ **Extraction automatique** de texte depuis des PDF médicaux
- 🏥 **5 types d'examens pré-configurés** :
  - Échographie cardiaque
  - Holter ECG
  - Holter tensionnel
  - Polygraphie ventilatoire
  - ECG standard
- ⚙️ **Configuration personnalisable** des prompts par type d'examen
- 🤖 **Compatible avec LM Studio** et tout serveur compatible OpenAI API
- 💾 **Sauvegarde automatique** de la configuration
- 📝 **Édition en ligne** des comptes-rendus générés
- ⬇️ **Export** des comptes-rendus en fichier texte

## 📋 Prérequis

- Python 3.8 ou supérieur
- [LM Studio](https://lmstudio.ai/) installé et configuré
- Un modèle LLM chargé dans LM Studio (recommandé : Llama 3.1, Mistral, ou Qwen)

## 🚀 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-username/cardiac-report-generator.git
cd cardiac-report-generator
```

### 2. Créer un environnement virtuel
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer LM Studio

1. Lancez LM Studio
2. Chargez un modèle (ex: `llama-3.1-8b-instruct`)
3. Démarrez le serveur local (port 1234 par défaut)
4. Vérifiez que le serveur est accessible à `http://127.0.0.1:1234`

## 📖 Usage

### Lancer l'application
```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`

### Workflow typique

1. **Configurez le modèle** dans la barre latérale :
   - URL : `http://127.0.0.1:1234`
   - Nom du modèle (tel qu'affiché dans LM Studio)
   - Ajustez la température et max_tokens selon vos besoins

2. **Sélectionnez le type d'examen** correspondant à votre PDF

3. **Uploadez votre fichier PDF** (export brut de votre logiciel d'examen)

4. **Ajoutez des consignes supplémentaires** si nécessaire

5. **Cliquez sur "Générer le compte-rendu"**

6. **Éditez et téléchargez** le résultat

## ⚙️ Configuration

### Personnaliser les prompts

Dans la barre latérale, vous pouvez :
- Modifier les instructions pour chaque type d'examen
- Ajouter de nouveaux types d'examens personnalisés
- Supprimer des types d'examens existants

Toutes les modifications sont automatiquement sauvegardées dans `cr_config.json`

### Paramètres LLM

- **Temperature** (0.0 - 1.0) : Contrôle la créativité des réponses
  - 0.0-0.3 : Très déterministe (recommandé pour les comptes-rendus)
  - 0.4-0.7 : Équilibré
  - 0.8-1.0 : Créatif

- **max_tokens** : Longueur maximale de la réponse (256-4096)
  - 1500 par défaut, suffisant pour la plupart des comptes-rendus

- **max_chars** : Limite du texte PDF envoyé au modèle
  - 20000 par défaut, ajustez selon la capacité de votre modèle

## 📁 Structure des fichiers
```
.
├── app.py                 # Application principale
├── cr_config.json        # Configuration sauvegardée (créé automatiquement)
├── requirements.txt      # Dépendances Python
└── README.md            # Ce fichier
```

## 🔧 Dépannage

### Le serveur LM Studio n'est pas accessible
```bash
# Vérifiez que le serveur est démarré
curl http://127.0.0.1:1234/v1/models
```

### Erreur "Aucun texte extrait du PDF"

- Vérifiez que votre PDF contient du texte (pas juste une image scannée)
- Si c'est un scan, utilisez un logiciel OCR avant l'import

### Le modèle ne génère rien ou plante

- Réduisez `max_chars` et `max_tokens`
- Vérifiez que votre modèle a assez de RAM/VRAM
- Essayez un modèle plus petit (7B au lieu de 13B par exemple)

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amelioration`)
3. Commit vos changements (`git commit -m 'Ajout d'une fonctionnalité'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrir une Pull Request

## 📝 License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## ⚠️ Avertissement

Cet outil est conçu pour **assister** les professionnels de santé dans la rédaction de comptes-rendus, **pas pour les remplacer**. 

- Toujours vérifier et valider les comptes-rendus générés
- Ne jamais utiliser sans relecture par un professionnel qualifié
- Respecter les réglementations locales sur les dispositifs médicaux et l'IA en santé

## 📧 Contact

Pour toute question ou suggestion, ouvrez une [issue](https://github.com/votre-username/cardiac-report-generator/issues) sur GitHub.

## 🙏 Remerciements

- [Streamlit](https://streamlit.io/) pour le framework web
- [LM Studio](https://lmstudio.ai/) pour l'interface LLM locale
- [pypdf](https://github.com/py-pdf/pypdf) pour l'extraction de texte PDF

---

Fait avec ❤️ pour la cardiologie
