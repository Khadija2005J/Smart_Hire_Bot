"""
🤖 INTERFACE CHATBOT CONVERSATIONNEL - SMART-HIRE
Interface Streamlit moderne avec chat interactif et boutons d'action
"""

import streamlit as st
import json
import os
from datetime import datetime
from chatbot_engine import ChatbotEngine

# Configuration de la page
st.set_page_config(
    page_title="🤖 SMART-HIRE Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .chat-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .badge-skill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 0.25rem;
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .history-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .history-item:hover {
        background: #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FONCTIONS HISTORIQUE ====================

def _to_serializable(obj):
    """Convertit récursivement en objets JSON-sérialisables (datetime -> isoformat)."""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, set):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def save_conversation():
    """Sauvegarde la conversation actuelle."""
    if not st.session_state.messages:
        return
    
    history_dir = "data/chat_history"
    os.makedirs(history_dir, exist_ok=True)
    
    conversation_id = st.session_state.get('conversation_id')
    if not conversation_id:
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.conversation_id = conversation_id
    
    # Créer un titre basé sur le premier message
    title = "Nouvelle conversation"
    if st.session_state.messages:
        first_user_msg = next((m['content'] for m in st.session_state.messages if m['role'] == 'user'), None)
        if first_user_msg:
            title = first_user_msg[:50] + ("..." if len(first_user_msg) > 50 else "")
    
    conversation_data = {
        "id": conversation_id,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "messages": st.session_state.messages,
        "context": st.session_state.chatbot.user_context
    }
    
    filepath = os.path.join(history_dir, f"{conversation_id}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(_to_serializable(conversation_data), f, ensure_ascii=False, indent=2)


def load_conversation(conversation_id: str):
    """Charge une conversation sauvegardée."""
    filepath = os.path.join("data/chat_history", f"{conversation_id}.json")
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        st.session_state.conversation_id = conversation_id
        st.session_state.messages = data.get('messages', [])
        st.session_state.chatbot.user_context = data.get('context', {})
        st.session_state.current_actions = []


def get_conversation_history():
    """Récupère la liste des conversations sauvegardées."""
    history_dir = "data/chat_history"
    if not os.path.exists(history_dir):
        return []
    
    conversations = []
    for filename in os.listdir(history_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(history_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conversations.append({
                    'id': data['id'],
                    'title': data.get('title', 'Sans titre'),
                    'timestamp': data.get('timestamp', ''),
                    'message_count': len(data.get('messages', []))
                })
            except:
                pass
    
    # Trier par date (plus récent en premier)
    conversations.sort(key=lambda x: x['timestamp'], reverse=True)
    return conversations


def delete_conversation(conversation_id: str):
    """Supprime une conversation."""
    filepath = os.path.join("data/chat_history", f"{conversation_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)


def new_conversation():
    """Démarre une nouvelle conversation."""
    st.session_state.messages = []
    st.session_state.current_actions = []
    st.session_state.chatbot.clear_context()
    st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# ==================== FONCTIONS ====================

def display_data(data: dict):
    """Affiche les candidats trouvés et les contrats générés."""
    
    # Afficher le bouton de téléchargement du contrat s'il existe
    if 'contract_path' in data and data['contract_path']:
        st.markdown("---")
        st.markdown("### 📥 Téléchargement du contrat")
        
        contract_path = data['contract_path']
        contract_filename = data.get('contract_filename', 'contrat.pdf')
        
        # Vérifier que le fichier existe
        if os.path.exists(contract_path):
            with open(contract_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            
            st.download_button(
                label="📥 Télécharger le PDF",
                data=pdf_data,
                file_name=contract_filename,
                mime="application/pdf",
                use_container_width=True
            )
            
            # Afficher l'info du fichier
            file_size = len(pdf_data) / 1024  # Taille en KB
            st.success(f"✅ Contrat généré avec succès ({file_size:.1f} KB)")
        else:
            st.error(f"❌ Le fichier {contract_path} n'existe pas")
        st.markdown("---")
    
    if 'matched_candidates' in data and data['matched_candidates']:
        st.markdown("---")
        st.markdown("### 👥 Candidats trouvés")
        
        for i, candidate in enumerate(data['matched_candidates'], 1):
            # Afficher chaque candidat dans une card
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 1rem; border-radius: 10px; margin: 1rem 0; color: white;'>
                <h3>👤 {i}. {candidate.get('nom', 'N/A')} {candidate.get('prenom', 'N/A')}</h3>
                <p style='font-size: 1.1em;'><strong>{candidate.get('poste', 'N/A')}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**📧 Email:** {candidate.get('email', 'N/A')}")
                st.write(f"**📅 Expérience:** {candidate.get('experience', 'N/A')} ans")
                if 'formation' in candidate:
                    st.write(f"**🎓 Formation:** {candidate.get('formation', 'N/A')}")
            
            with col2:
                if 'competences' in candidate and candidate['competences']:
                    st.write("**🔧 Compétences principales:**")
                    # Afficher les compétences comme badges
                    comp_html = " ".join([
                        f'<span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 8px; margin: 2px; display: inline-block; font-size: 0.85em;">{comp}</span>'
                        for comp in candidate['competences'][:6]
                    ])
                    st.markdown(comp_html, unsafe_allow_html=True)
            
            with col3:
                if 'match_score' in candidate:
                    st.markdown(f"""
                    <div style='text-align: center; background: #4caf50; color: white; 
                                padding: 1.5rem; border-radius: 10px;'>
                        <h1 style='margin: 0; font-size: 2.5em;'>{candidate['match_score']}%</h1>
                        <p style='margin: 0;'>Match</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            if 'match_reason' in candidate:
                st.info(f"💡 **Pourquoi ce candidat:** {candidate['match_reason']}")
            
            st.markdown("---")


def handle_action(action: str):
    """Gère les clics sur les boutons."""
    result = st.session_state.chatbot.execute_action(action)
    
    bot_message = {
        "role": "assistant",
        "content": result.get('message', 'Action exécutée'),
        "data": result.get('data', {})  # ✅ AJOUT: Inclure les données (candidats)
    }
    
    st.session_state.messages.append(bot_message)
    st.session_state.current_actions = result.get('actions', [])
    
    st.rerun()


# ==================== INITIALISATION ====================

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = ChatbotEngine()

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'current_actions' not in st.session_state:
    st.session_state.current_actions = []

if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# ==================== SIDEBAR - HISTORIQUE ====================

with st.sidebar:
    st.markdown("### 📜 Historique des conversations")
    
    if st.button("➕ Nouvelle conversation", use_container_width=True, type="primary"):
        save_conversation()  # Sauvegarder l'actuelle avant
        new_conversation()
        st.rerun()
    
    st.markdown("---")
    
    # Afficher l'historique
    conversations = get_conversation_history()
    
    if conversations:
        st.markdown("**Conversations récentes:**")
        for conv in conversations[:10]:  # Limiter à 10
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Créer un bouton cliquable pour chaque conversation
                timestamp = datetime.fromisoformat(conv['timestamp'])
                date_str = timestamp.strftime("%d/%m %H:%M")
                
                if st.button(
                    f"💬 {conv['title'][:30]}",
                    key=f"load_{conv['id']}",
                    help=f"{date_str} - {conv['message_count']} messages",
                    use_container_width=True
                ):
                    save_conversation()  # Sauvegarder avant de charger
                    load_conversation(conv['id'])
                    st.rerun()
            
            with col2:
                # Bouton supprimer
                if st.button("🗑️", key=f"del_{conv['id']}", help="Supprimer"):
                    delete_conversation(conv['id'])
                    st.rerun()
        
        st.markdown("---")
        
        # Statistiques
        total_convs = len(conversations)
        total_msgs = sum(c['message_count'] for c in conversations)
        st.markdown(f"📊 **Stats:** {total_convs} conv. | {total_msgs} messages")
    else:
        st.info("Aucune conversation sauvegardée")
    
    st.markdown("---")
    
    if st.button("💡 Aide", use_container_width=True):
        handle_action("help")

# ==================== INTERFACE ====================

st.markdown("""
<div class="chat-header">
    <h1>🤖 SMART-HIRE Chatbot</h1>
    <p>Assistant intelligent de recrutement</p>
</div>
""", unsafe_allow_html=True)

# Afficher les messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Afficher les données (candidats) si présentes
        if "data" in message and message["data"]:
            display_data(message["data"])

# Boutons d'action
if st.session_state.current_actions:
    st.markdown("### 🎯 Actions suggérées")
    cols = st.columns(min(len(st.session_state.current_actions), 3))
    
    for idx, action in enumerate(st.session_state.current_actions):
        col_idx = idx % 3
        with cols[col_idx]:
            if st.button(
                action['label'],
                key=f"action_{idx}",
                use_container_width=True
            ):
                handle_action(action['action'])

# Input utilisateur
user_input = st.chat_input("💬 Tapez votre message...")

if user_input:
    # Ajouter message utilisateur
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Traiter avec chatbot
    response = st.session_state.chatbot.process_message(user_input)
    
    # Si l'intent est "search_candidates", lancer la recherche automatiquement
    if response.get('intent') == 'search_candidates':
        search_result = st.session_state.chatbot.execute_action('execute_search')
        st.session_state.messages.append({
            "role": "assistant",
            "content": search_result.get('message', ''),
            "data": search_result.get('data', {})
        })
        st.session_state.current_actions = search_result.get('actions', [])
    else:
        # Ajouter réponse du bot
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.get('response', ''),
            "data": response.get('data', {})
        })
        # Mettre à jour les actions
        st.session_state.current_actions = response.get('actions', [])
    
    # Sauvegarder automatiquement après chaque interaction
    save_conversation()
    
    st.rerun()

# Sauvegarder périodiquement
if st.session_state.messages:
    save_conversation()

# Sauvegarder périodiquement
if st.session_state.messages:
    save_conversation()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #666;'>🤖 SMART-HIRE v2.0</p>", unsafe_allow_html=True)
