import streamlit as st
from pypdf import PdfReader
import requests
import io
import os
import json
from typing import Dict, Tuple, Optional
from pathlib import Path

# ==============================
# CONSTANTES
# ==============================

CONFIG_FILE = Path("cr_config.json")

DEFAULT_DOC_TYPES = {
    "Échographie cardiaque": """Tu es un cardiologue expert en échocardiographie adulte.
Tu reçois le compte-rendu brut d'une échographie cardiaque (mesures, texte libre).
Ta mission :
- Structurer un compte-rendu clair, concis et professionnel.
- Résumer les données chiffrées importantes (dimensions, FE, pressions, valves…).
- Conclure par un paragraphe "Conclusion" puis, si utile, "Recommandations".
- Style attendu : compte-rendu hospitalier français, impersonnel, sans formules de politesse.
Ne JAMAIS inventer de valeur : si une information manque, tu l'ignores simplement.""",

    "Holter ECG": """Tu es un cardiologue expert en rythmologie.
Tu reçois un rapport brut de Holter ECG (24 h ou plus) avec de nombreuses données chiffrées.
Ta mission :
- Synthétiser les principaux éléments (rythme de base, FC moyenne/min/max, extrasystoles, salves, FA, pauses, troubles conductifs...).
- Dégager les éléments cliniquement pertinents et les présenter de façon structurée.
- Terminer par une "Conclusion" claire (normal / anomalies principales / corrélation aux symptômes si mentionnée).
Style : compte-rendu médical français, concis, sans extrapoler au-delà des données fournies.""",

    "Holter tensionnel": """Tu es un cardiologue expert en HTA.
Tu reçois un rapport brut de Holter tensionnel (MAPA).
Ta mission :
- Résumer les pressions moyennes (24 h, jour, nuit) si disponibles.
- Commenter la charge tensionnelle, le profil nycthéméral (dipper / non dipper / reverse dipper), et l'équilibre global.
- Conclure par une "Conclusion" avec interprétation clinique : équilibre satisfaisant ou non, suspicion d'HTA masquée/blouse blanche, etc., si ces éléments apparaissent clairement.
Ne pas inventer de diagnostic non mentionné dans les données.""",

    "Polygraphie ventilatoire": """Tu es un cardiologue / spécialiste du sommeil.
Tu reçois un compte-rendu brut de polygraphie ventilatoire.
Ta mission :
- Synthétiser les indices principaux (IAH, IAH obstructif/central, saturation, désaturations, ronflements... si présents).
- Décrire le profil global du sommeil respiratoire.
- Conclure par une "Conclusion" sur la sévérité du SAOS ou absence de SAOS si c'est clairement documenté.
Tu restes strictement sur les données fournies.""",

    "ECG standard": """Tu es un cardiologue expert en électrocardiographie.
Tu reçois un descriptif brut d'ECG (souvent semi-structuré).
Ta mission :
- Produire une interprétation ECG standardisée : rythme, fréquence, axe, conduction, repolarisation, autres anomalies.
- Terminer par une "Conclusion" courte en une ou deux phrases.
Ne fais pas de diagnostic étiologique complet (ex : "infarctus ancien") si ce n'est pas explicitement supporté par le texte."""
}

DEFAULT_LLM_CONFIG = {
    "base_url": "http://127.0.0.1:1234",
    "model_name": "model",
    "api_key": "lm-studio",
    "temperature": 0.2,
    "max_tokens": 1500,
    "max_chars": 20000,
}


# ==============================
# GESTION DE LA CONFIGURATION
# ==============================

def load_config() -> Optional[Dict]:
    """Charge la configuration depuis le fichier JSON."""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        st.warning(f"Impossible de charger la configuration : {e}")
        return None


def save_config() -> None:
    """Sauvegarde la configuration actuelle sur le disque."""
    config_data = {
        "doc_types": st.session_state.doc_types,
        "base_url": st.session_state.base_url,
        "model_name": st.session_state.model_name,
        "api_key": st.session_state.api_key,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "max_chars": st.session_state.max_chars,
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")


# ==============================
# INITIALISATION SESSION STATE
# ==============================

def init_session_state() -> None:
    """Initialise les variables de session Streamlit."""
    cfg = load_config()

    # Types de documents + prompts
    if "doc_types" not in st.session_state:
        st.session_state.doc_types = (
            cfg.get("doc_types", DEFAULT_DOC_TYPES) if cfg else DEFAULT_DOC_TYPES.copy()
        )

    # Sélection pour la configuration
    if "config_selected_doc_type" not in st.session_state:
        st.session_state.config_selected_doc_type = next(iter(st.session_state.doc_types))

    if "config_prompt_buffer" not in st.session_state:
        st.session_state.config_prompt_buffer = st.session_state.doc_types[
            st.session_state.config_selected_doc_type
        ]

    # Paramètres LLM avec valeurs par défaut
    for key, default_value in DEFAULT_LLM_CONFIG.items():
        if key not in st.session_state:
            st.session_state[key] = cfg.get(key, default_value) if cfg else default_value


# ==============================
# EXTRACTION TEXTE PDF
# ==============================

def extract_text_from_pdf(uploaded_file) -> str:
    """Extrait le texte d'un fichier PDF uploadé."""
    if uploaded_file is None:
        return ""

    try:
        pdf_bytes = uploaded_file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du PDF : {e}")
        return ""


# ==============================
# APPEL AU MODÈLE LLM
# ==============================

def call_local_llm(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> str:
    """Appelle le modèle LLM local via une API compatible OpenAI."""
    endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key or 'lm-studio'}",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Erreur de connexion à l'API : {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Réponse API invalide : {data}") from e


# ==============================
# SIDEBAR : CONFIGURATION
# ==============================

def sidebar_config() -> Tuple[str, str, str, float, int]:
    """Affiche et gère la configuration dans la sidebar."""
    st.sidebar.header("⚙️ Configuration du modèle local")

    # Paramètres LLM
    base_url = st.sidebar.text_input(
        "Base URL du serveur",
        value=st.session_state.base_url,
        key="base_url",
        help="Ex : http://127.0.0.1:1234 si LM Studio tourne en local."
    )

    model_name = st.sidebar.text_input(
        "Nom du modèle",
        value=st.session_state.model_name,
        key="model_name",
        help="Nom exact du modèle chargé dans LM Studio (ex: llama-3.1-8b-instruct)."
    )

    api_key = st.sidebar.text_input(
        "API key",
        value=st.session_state.api_key,
        key="api_key",
        type="password",
        help="LM Studio accepte souvent n'importe quelle clé."
    )

    temperature = st.sidebar.slider(
        "Température",
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.temperature),
        step=0.05,
        key="temperature",
        help="Plus c'est bas, plus la réponse est déterministe."
    )

    max_tokens = st.sidebar.slider(
        "max_tokens (réponse)",
        min_value=256,
        max_value=4096,
        value=int(st.session_state.max_tokens),
        step=256,
        key="max_tokens"
    )

    st.sidebar.markdown("---")
    
    # Configuration des modèles de compte-rendu
    render_doc_type_configuration()
    
    st.sidebar.markdown("---")
    
    # Ajout d'un nouveau type
    render_add_doc_type()

    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Sauvegarder toute la configuration"):
        save_config()
        st.sidebar.success("Configuration sauvegardée !")

    return base_url, model_name, api_key, temperature, max_tokens


def render_doc_type_configuration() -> None:
    """Affiche l'interface de configuration des types de documents."""
    st.sidebar.header("🧩 Paramétrage des comptes-rendus")

    doc_type_names = list(st.session_state.doc_types.keys())
    
    if not doc_type_names:
        st.sidebar.warning("Aucun type d'examen configuré.")
        return
    
    # Callback pour mettre à jour le buffer quand on change de sélection
    def on_doc_type_change():
        selected = st.session_state.config_selected_doc_type
        st.session_state.config_prompt_buffer = st.session_state.doc_types[selected]
    
    selected = st.sidebar.selectbox(
        "Type d'examen à configurer",
        doc_type_names,
        index=doc_type_names.index(st.session_state.config_selected_doc_type)
        if st.session_state.config_selected_doc_type in doc_type_names
        else 0,
        key="config_selected_doc_type",
        on_change=on_doc_type_change
    )

    # Utiliser une clé unique pour forcer la mise à jour du text_area
    prompt_text = st.sidebar.text_area(
        "Instructions pour ce type :",
        value=st.session_state.doc_types[selected],
        height=250,
        key=f"config_prompt_textarea_{selected}"
    )
    
    # Mettre à jour le buffer à chaque modification
    st.session_state.config_prompt_buffer = prompt_text

    col1, col2 = st.sidebar.columns([2, 1])
    
    with col1:
        if st.button("💾 Enregistrer", use_container_width=True, key=f"save_{selected}"):
            st.session_state.doc_types[selected] = st.session_state.config_prompt_buffer
            save_config()
            st.sidebar.success("Modèle mis à jour !")
    
    with col2:
        if st.button("🗑️ Supprimer", use_container_width=True, key=f"delete_{selected}"):
            if len(st.session_state.doc_types) > 1:
                del st.session_state.doc_types[selected]
                st.session_state.config_selected_doc_type = next(iter(st.session_state.doc_types))
                st.session_state.config_prompt_buffer = st.session_state.doc_types[st.session_state.config_selected_doc_type]
                save_config()
                st.sidebar.success("Type supprimé !")
                st.rerun()
            else:
                st.sidebar.error("Impossible de supprimer le dernier type.")


def render_add_doc_type() -> None:
    """Affiche l'interface d'ajout d'un nouveau type de document."""
    st.sidebar.subheader("➕ Ajouter un type d'examen")

    new_doc_name = st.sidebar.text_input(
        "Nom du nouveau type",
        placeholder="Ex : IRM cardiaque",
        key="new_doc_name"
    )

    new_doc_prompt = st.sidebar.text_area(
        "Instructions pour ce type :",
        placeholder="Décris les attentes pour ce type d'examen...",
        key="new_doc_prompt",
        height=150
    )

    if st.sidebar.button("Ajouter ce type"):
        if not new_doc_name.strip():
            st.sidebar.error("Merci de renseigner un nom.")
        elif new_doc_name in st.session_state.doc_types:
            st.sidebar.error("Ce nom existe déjà.")
        else:
            st.session_state.doc_types[new_doc_name] = (
                new_doc_prompt or "Tu es un cardiologue. Rédige un compte-rendu structuré."
            )
            st.session_state.config_selected_doc_type = new_doc_name
            st.session_state.config_prompt_buffer = st.session_state.doc_types[new_doc_name]
            save_config()
            st.sidebar.success(f"Type '{new_doc_name}' ajouté !")
            st.rerun()


# ==============================
# GÉNÉRATION DU COMPTE-RENDU
# ==============================

def generate_report(
    uploaded_file,
    doc_type: str,
    instructions: str,
    base_url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    max_chars: int
) -> Optional[str]:
    """Génère un compte-rendu à partir du PDF uploadé."""
    if uploaded_file is None:
        st.error("Merci d'importer d'abord un PDF.")
        return None
    
    if not base_url or not model_name:
        st.error("Configuration LLM incomplète (voir sidebar).")
        return None

    with st.spinner("Extraction du texte et génération..."):
        try:
            uploaded_file.seek(0)
            pdf_text = extract_text_from_pdf(uploaded_file)

            if not pdf_text.strip():
                st.error("Aucun texte extrait. PDF scanné sans OCR ?")
                return None

            # Troncature si nécessaire
            if len(pdf_text) > max_chars:
                st.warning(
                    f"Document tronqué : {len(pdf_text)} → {max_chars} caractères."
                )
                pdf_text = pdf_text[:max_chars]

            # Construction du prompt utilisateur
            user_content = (
                f"Type de document : {doc_type}\n\n"
                f"Contenu brut extrait du PDF :\n\n{pdf_text}\n\n"
                f"Consignes supplémentaires : {instructions}"
            )

            # Appel au modèle
            system_prompt = st.session_state.doc_types[doc_type]
            
            report = call_local_llm(
                base_url=base_url,
                api_key=api_key,
                model=model_name,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=temperature,
                max_tokens=max_tokens
            )

            save_config()  # Sauvegarde auto des paramètres
            return report

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")
            return None


# ==============================
# INTERFACE PRINCIPALE
# ==============================

def main():
    """Point d'entrée principal de l'application."""
    st.set_page_config(
        page_title="Génération de comptes-rendus cardiologiques",
        page_icon="❤️",
        layout="wide",
    )
    
    init_session_state()

    st.title("❤️ Générateur de comptes-rendus cardiologiques")
    st.markdown(
        "Uploadez un PDF (écho, Holter, ECG...) → extraction automatique → "
        "compte-rendu structuré via votre modèle LLM local."
    )

    # Configuration dans la sidebar
    base_url, model_name, api_key, temperature, max_tokens = sidebar_config()

    # ===== ÉTAPE 1 : Type d'examen =====
    st.subheader("1️⃣ Type d'examen")
    
    doc_type = st.selectbox(
        "Sélectionnez le type d'examen :",
        list(st.session_state.doc_types.keys()),
        help="Configurez les types dans la barre latérale"
    )

    # ===== ÉTAPE 2 : Upload PDF =====
    st.subheader("2️⃣ Import du fichier PDF")
    
    uploaded_file = st.file_uploader(
        "Choisissez un fichier PDF :",
        type=["pdf"],
        help="Export brut de votre logiciel d'examen"
    )

    if uploaded_file is not None:
        st.success(f"✅ Fichier importé : {uploaded_file.name}")

        with st.expander("📄 Aperçu du texte extrait"):
            uploaded_file.seek(0)
            raw_text = extract_text_from_pdf(uploaded_file)
            if raw_text:
                st.text_area(
                    "Texte extrait (premiers 5000 caractères)",
                    value=raw_text[:5000],
                    height=200,
                    disabled=True
                )
            else:
                st.warning("Aucun texte extrait du PDF.")

    # ===== ÉTAPE 3 : Options =====
    st.subheader("3️⃣ Options de génération")

    col1, col2 = st.columns([3, 1])
    
    with col1:
        instructions = st.text_area(
            "Consignes supplémentaires (optionnel)",
            value="Rédige un compte-rendu structuré prêt à être collé dans le dossier patient.",
            height=100
        )
    
    with col2:
        max_chars = st.number_input(
            "Limite de caractères",
            min_value=5000,
            max_value=100000,
            value=int(st.session_state.max_chars),
            step=5000,
            key="max_chars",
            help="Évite de dépasser le contexte du modèle"
        )

    # ===== ÉTAPE 4 : Génération =====
    st.subheader("4️⃣ Génération du compte-rendu")

    if st.button("✨ Générer le compte-rendu", type="primary", use_container_width=True):
        report = generate_report(
            uploaded_file=uploaded_file,
            doc_type=doc_type,
            instructions=instructions,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            max_chars=max_chars
        )

        if report:
            st.success("✅ Compte-rendu généré avec succès !")
            
            tab1, tab2 = st.tabs(["📝 Rendu final", "✏️ Version éditable"])
            
            with tab1:
                st.markdown(report)
                st.download_button(
                    "⬇️ Télécharger le compte-rendu",
                    data=report,
                    file_name=f"compte_rendu_{doc_type.lower().replace(' ', '_')}.txt",
                    mime="text/plain"
                )
            
            with tab2:
                edited_report = st.text_area(
                    "Modifiez le compte-rendu avant de le copier :",
                    value=report,
                    height=400
                )
                
                if st.button("📋 Copier dans le presse-papier"):
                    st.code(edited_report, language=None)
                    st.info("💡 Sélectionnez le texte ci-dessus et copiez-le (Ctrl+C)")


if __name__ == "__main__":
    main()