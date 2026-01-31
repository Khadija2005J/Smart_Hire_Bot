"""
🤖 MOTEUR DE CHATBOT INTELLIGENT SMHIRE
Gestion des intentions, actions et contexte pour l'assistant.
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import requests
from linkedin_auto_post import generate_linkedin_post_content

# Import LinkedIn OAuth avec gestion d'erreur
_linkedin_oauth = None
try:
    from linkedin_oauth import linkedin_oauth as _imported_oauth
    _linkedin_oauth = _imported_oauth
except Exception as e:  # pragma: no cover
    print(f"⚠️ Erreur import linkedin_oauth: {e}")
    _linkedin_oauth = None


def get_linkedin_oauth():
    """Retourne l'instance LinkedIn OAuth (ou None si indisponible)."""
    return _linkedin_oauth


class ChatbotEngine:
    """Moteur de chatbot conversationnel pour SMHIRE."""

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.user_context: Dict = {}
        self.pending_action: Optional[str] = None

    # ==================== INTENT DETECTION ====================
    def detect_intent(self, message: str) -> Tuple[str, float]:
        message_lower = message.lower()
        intents = {
            "greeting": ["bonjour", "salut", "hello", "hey", "coucou"],
            "search_candidates": ["recherche", "cherche", "candidat", "talent", "profil", "trouve", "trouver", "développeur", "developpeur", "ingénieur", "ingenieur", "compétence", "competence", "veux", "besoin", "recrute", "recrutement", "médecin", "medecin"],
            "view_candidates": ["liste", "voir", "candidats"],
            "send_invitation": ["invite", "inviter", "entretien", "email"],
            "generate_contract": ["contrat", "cdi", "cdd", "stage", "freelance"],
            "sync_emails": ["sync", "synchronise", "email", "imap"],
            "view_stats": ["stat", "dashboard", "analyse"],
            "linkedin_post": ["linkedin", "publier", "post"],
            "help": ["aide", "help", "comment"],
        }

        for intent, keywords in intents.items():
            if any(k in message_lower for k in keywords):
                return intent, 0.75
        return "unknown", 0.2

    # ==================== PARAM EXTRACTION ====================
    def extract_parameters(self, message: str, intent: str) -> Dict:
        params: Dict = {}
        if intent == "search_candidates":
            match_num = re.search(r"(\d+)", message)
            if match_num:
                params["num_candidates"] = int(match_num.group(1))
            else:
                params["num_candidates"] = 4
            params["job_description"] = message
        elif intent == "generate_contract":
            ml = message.lower()
            if "cdi" in ml:
                params["contract_type"] = "CDI"
            elif "cdd" in ml:
                params["contract_type"] = "CDD"
            elif "stage" in ml:
                params["contract_type"] = "Stage"
            elif "freelance" in ml:
                params["contract_type"] = "Freelance"
        return params

    # ==================== RESPONSE GENERATION ====================
    def generate_response_with_ollama(self, user_message: str, context: Dict) -> str:
        """Appel Ollama pour une réponse courte, fallback si indisponible."""
        OLLAMA_API_URL = "http://localhost:11434/api/generate"
        system_context = (
            "Tu es SMART-HIRE, un assistant IA de recrutement friendly et professionnel.\n"
            "Tu aides sur : recherche candidats, invitations, contrats, sync emails, LinkedIn.\n"
            f"Contexte actuel: {json.dumps(context, ensure_ascii=False)}\n"
            "Réponds en 2-3 phrases max, ton clair et amical."
        )
        prompt = f"{system_context}\n\nUtilisateur: {user_message}\n\nAssistant:"
        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": "gemma:2b",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "num_predict": 150,
                },
                timeout=10,
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass
        return self.generate_fallback_response(user_message, context)

    def generate_fallback_response(self, user_message: str, context: Dict) -> str:
        intent, _ = self.detect_intent(user_message)
        responses = {
            "greeting": "👋 Bonjour ! Je suis SMART-HIRE. Que puis-je faire pour vous ?",
            "search_candidates": "🔍 Parfait, je cherche les meilleurs candidats.",
            "view_candidates": "📋 Voici la liste des candidats disponibles.",
            "send_invitation": "📧 Je prépare les invitations.",
            "generate_contract": "📄 Génération de contrat - Quel type souhaitez-vous ?",
            "sync_emails": "📥 Je synchronise vos emails et CVs.",
            "view_stats": "📊 Voici vos statistiques.",
            "linkedin_post": "🔗 Préparation d'un post LinkedIn...",
            "help": "💡 Je peux chercher des candidats, envoyer des invitations, générer des contrats, etc.",
            "unknown": "🤔 Je n'ai pas bien compris. Pouvez-vous reformuler ?",
        }
        return responses.get(intent, responses["unknown"])

    # ==================== CHAT PIPELINE ====================
    def process_message(self, user_message: str) -> Dict:
        self.conversation_history.append({
            "role": "user",
            "message": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # Vérifier si on attend un nom de candidat
        if self.user_context.get("awaiting_candidate_name"):
            return self._handle_candidate_name_input(user_message)

        intent, confidence = self.detect_intent(user_message)
        params = self.extract_parameters(user_message, intent)
        self.user_context.update(params)
        self.user_context["last_intent"] = intent

        # Gestion spéciale pour generate_contract
        if intent == "generate_contract":
            action_result = self.execute_action("start_contract_generation", params)
            # Enrichir le résultat pour qu'il ait la même structure que process_message
            result = {
                "response": action_result.get("message", ""),
                "intent": intent,
                "confidence": confidence,
                "actions": action_result.get("actions", []),
                "data": action_result.get("data", {}),
                "timestamp": datetime.now().isoformat(),
            }
            self.conversation_history.append({
                "role": "assistant",
                "message": action_result.get("message", ""),
                "timestamp": datetime.now().isoformat(),
            })
            return result

        response_text = self.generate_response_with_ollama(user_message, self.user_context)
        actions = self.get_suggested_actions(intent, params)
        data = self.get_relevant_data(intent, params)

        result = {
            "response": response_text,
            "intent": intent,
            "confidence": confidence,
            "actions": actions,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        self.conversation_history.append({
            "role": "assistant",
            "message": response_text,
            "timestamp": datetime.now().isoformat(),
        })
        return result

    # ==================== UI HELPERS ====================
    def get_suggested_actions(self, intent: str, params: Dict) -> List[Dict]:
        if intent in ("greeting", "help"):
            return [
                {"label": "🔍 Rechercher des candidats", "action": "search_candidates", "style": "primary"},
                {"label": "📊 Voir le dashboard", "action": "view_stats", "style": "secondary"},
                {"label": "📥 Synchroniser les emails", "action": "sync_emails", "style": "secondary"},
                {"label": "🔗 Publier sur LinkedIn", "action": "linkedin_post", "style": "secondary"},
            ]
        if intent == "search_candidates":
            return [
                {"label": "✅ Lancer la recherche", "action": "execute_search", "style": "primary"},
                {"label": "⚙️ Modifier les critères", "action": "modify_search", "style": "secondary"},
                {"label": "❌ Annuler", "action": "cancel", "style": "secondary"},
            ]
        if intent == "view_candidates":
            return [
                {"label": "📧 Inviter aux entretiens", "action": "send_invitations", "style": "primary"},
                {"label": "📄 Générer un contrat", "action": "generate_contract", "style": "secondary"},
                {"label": "⭐ Ajouter aux favoris", "action": "add_favorite", "style": "secondary"},
            ]
        if intent == "send_invitation":
            return [
                {"label": "✅ Confirmer l'envoi", "action": "confirm_send", "style": "primary"},
                {"label": "📅 Planifier la date", "action": "schedule_date", "style": "secondary"},
                {"label": "❌ Annuler", "action": "cancel", "style": "secondary"},
            ]
        if intent == "generate_contract":
            return [
                {"label": "📋 CDI", "action": "contract_cdi", "style": "secondary"},
                {"label": "📋 CDD", "action": "contract_cdd", "style": "secondary"},
                {"label": "📋 Stage", "action": "contract_stage", "style": "secondary"},
                {"label": "📋 Freelance", "action": "contract_freelance", "style": "secondary"},
            ]
        if intent == "sync_emails":
            return [
                {"label": "🔄 Synchroniser maintenant", "action": "sync_now", "style": "primary"},
                {"label": "⚙️ Configurer", "action": "config_email", "style": "secondary"},
            ]
        if intent == "linkedin_post":
            return [
                {"label": "📤 Publier maintenant", "action": "publish_now", "style": "primary"},
                {"label": "✏️ Modifier le post", "action": "edit_post", "style": "secondary"},
                {"label": "💾 Sauvegarder brouillon", "action": "save_draft", "style": "secondary"},
            ]
        if intent == "unknown":
            return [
                {"label": "💡 Voir l'aide", "action": "help", "style": "primary"},
                {"label": "🔍 Rechercher des candidats", "action": "search_candidates", "style": "secondary"},
            ]
        return []

    def get_relevant_data(self, intent: str, params: Dict) -> Dict:
        data: Dict = {}
        if intent == "search_candidates":
            data["search_params"] = params
        elif intent == "view_stats":
            try:
                with open("data/cv_data.json", "r", encoding="utf-8") as f:
                    candidates = json.load(f)
                data["total_candidates"] = len(candidates)
                data["candidates"] = candidates[:5]
            except Exception:
                data["total_candidates"] = 0
        return data

    # ==================== ACTIONS ====================
    def execute_action(self, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        result = {"success": True, "message": "", "actions": [], "data": {}}

        # -------- Recherche de candidats --------
        if action == "execute_search":
            from matching import smart_match_candidates
            try:
                with open("data/cv_data.json", "r", encoding="utf-8") as f:
                    cv_data = json.load(f)
                job_desc = params.get("job_description", self.user_context.get("job_description", ""))
                num_candidates = params.get("num_candidates", self.user_context.get("num_candidates", 4))
                smart = smart_match_candidates(job_desc, cv_data, num_candidates)
                matched = smart.get('candidates', [])
                if smart.get('has_results'):
                    self.user_context["matched_candidates"] = matched
                    result["message"] = f"✅ Excellent ! J'ai trouvé {len(matched)} candidat(s) correspondant à votre recherche !"
                    result["data"] = {"matched_candidates": matched}
                    result["actions"] = [
                        {"label": "📧 Inviter aux entretiens", "action": "send_invitations", "style": "primary"},
                        {"label": "⭐ Ajouter aux favoris", "action": "add_favorite", "style": "secondary"},
                        {"label": "📄 Voir les détails", "action": "view_details", "style": "secondary"},
                    ]
                else:
                    self.user_context["pending_linkedin_post"] = job_desc
                    self.user_context["job_title"] = job_desc[:50]
                    reason = smart.get('reason', "Aucun profil correspondant.")
                    result["message"] = (
                        "😔 Aucun candidat ne correspond actuellement.\n\n"
                        f"Motif: {reason}\n\n"
                        "**Solution:** Publier l'offre sur LinkedIn pour attirer des candidats !"
                    )
                    result["actions"] = [
                        {"label": "🔗 Publier sur LinkedIn", "action": "publish_linkedin_job", "style": "primary"},
                        {"label": "✏️ Personnaliser le post", "action": "customize_linkedin_post", "style": "secondary"},
                        {"label": "⏭️ Essayer une autre recherche", "action": "new_search", "style": "secondary"},
                    ]
            except Exception as e:
                result["success"] = False
                result["message"] = f"❌ Erreur lors de la recherche: {e}"

        # -------- Inviter aux entretiens (sélection multiple) --------
        elif action == "send_invitations":
            matched = self.user_context.get("matched_candidates", [])
            if matched:
                self.user_context["matched_candidates"] = matched
                self.user_context["selected_candidates"] = []
                self.user_context["desired_invite_count"] = None
                max_invitable = len(matched)
                quick_choices = list(range(1, min(max_invitable, 5) + 1))
                count_actions = [
                    {
                        "label": f"Inviter {count} candidat(s)",
                        "action": f"set_invitation_count_{count}",
                        "style": "primary" if count == 1 else "secondary",
                    }
                    for count in quick_choices
                ]
                if max_invitable > 1:
                    count_actions.append({
                        "label": f"🎯 Inviter tout le monde ({max_invitable})",
                        "action": "set_invitation_count_all",
                        "style": "secondary",
                    })
                result["message"] = (
                    "📧 **Invitations aux entretiens**\n\n"
                    f"Vous avez {len(matched)} candidat(s) disponible(s).\n\n"
                    "👉 Combien de candidat(s) souhaitez-vous inviter ?"
                )
                result["actions"] = count_actions
                result["data"] = {"matched_candidates": matched}
            else:
                result["message"] = "❌ Aucun candidat disponible. Faites d'abord une recherche."
                result["actions"] = [{"label": "🔍 Nouvelle recherche", "action": "new_search", "style": "primary"}]

        elif action.startswith("set_invitation_count_"):
            matched = self.user_context.get("matched_candidates", [])
            if not matched:
                result["message"] = "❌ Aucun candidat disponible. Veuillez relancer une recherche."
                return result
            desired_raw = action.replace("set_invitation_count_", "")
            desired_count = len(matched) if desired_raw == "all" else max(1, int(desired_raw))
            desired_count = min(desired_count, len(matched))
            self.user_context["desired_invite_count"] = desired_count
            self.user_context["selected_candidates"] = []

            if desired_count >= len(matched):
                self.user_context["selected_candidates"] = matched
                now = datetime.now()
                names_list = "\n".join([
                    f"- {c.get('nom', '')} {c.get('prenom', '')} ({c.get('email', 'N/A')})" for c in matched
                ])
                result["message"] = (
                    f"✅ **{len(matched)} candidat(s) sélectionné(s)**\n\n{names_list}\n\n"
                    "📅 Choisissez une date et heure commune pour l'entretien :"
                )
                result["actions"] = self._date_choices(now)
            else:
                candidate_actions = []
                for idx, candidate in enumerate(matched):
                    name = f"{candidate.get('nom', '')} {candidate.get('prenom', '')}"
                    candidate_actions.append({
                        "label": f"✅ {name}",
                        "action": f"select_candidate_{idx}",
                        "style": "secondary",
                    })
                result["message"] = (
                    f"🎯 Vous souhaitez inviter {desired_count} candidat(s).\n\n"
                    "👉 Sélectionnez les candidats à inviter :"
                )
                result["actions"] = candidate_actions
                result["data"] = {"matched_candidates": matched}

        elif action.startswith("select_candidate_"):
            try:
                candidate_idx = int(action.split("_")[-1])
                matched = self.user_context.get("matched_candidates", [])
                desired_count = self.user_context.get("desired_invite_count", len(matched))
                selected_candidates = self.user_context.get("selected_candidates", [])
                if 0 <= candidate_idx < len(matched):
                    candidate = matched[candidate_idx]
                    if candidate not in selected_candidates:
                        selected_candidates.append(candidate)
                        self.user_context["selected_candidates"] = selected_candidates
                    remaining = max(0, desired_count - len(selected_candidates))
                    if remaining <= 0:
                        now = datetime.now()
                        names_list = "\n".join([
                            f"- {c.get('nom', '')} {c.get('prenom', '')} ({c.get('email', 'N/A')})"
                            for c in selected_candidates
                        ])
                        result["message"] = (
                            f"✅ Sélection terminée : {len(selected_candidates)} candidat(s)\n\n{names_list}\n\n"
                            "📅 Choisissez une date et heure commune pour l'entretien :"
                        )
                        result["actions"] = self._date_choices(now)
                    else:
                        candidate_actions = []
                        for idx, cand in enumerate(matched):
                            if cand in selected_candidates:
                                continue
                            name = f"{cand.get('nom', '')} {cand.get('prenom', '')}"
                            candidate_actions.append({
                                "label": f"✅ {name}",
                                "action": f"select_candidate_{idx}",
                                "style": "secondary",
                            })
                        selected_names = ", ".join(
                            [f"{c.get('nom', '')} {c.get('prenom', '')}" for c in selected_candidates]
                        ) or "Aucun pour l'instant"
                        result["message"] = (
                            f"🧩 {len(selected_candidates)}/{desired_count} sélectionné(s)\n"
                            f"Actuellement : {selected_names}\n\n"
                            f"👉 Choisissez encore {remaining} candidat(s) :"
                        )
                        result["actions"] = candidate_actions
                else:
                    result["message"] = "❌ Candidat non trouvé."
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action.startswith("set_date_"):
            try:
                parts = action.replace("set_date_", "").split("_")
                date_str, time_str = parts[0], parts[1]
                interview_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                self.user_context["interview_date"] = interview_datetime
                selected_candidates = self.user_context.get("selected_candidates", [])
                names_list = "\n".join([f"- {c.get('nom', '')} {c.get('prenom', '')}" for c in selected_candidates]) or "Aucun candidat"
                result["message"] = (
                    "📅 **Date d'entretien confirmée**\n\n"
                    f"🕒 {interview_datetime.strftime('%d/%m/%Y à %H:%M')}\n\n"
                    f"👥 Candidats concernés :\n{names_list}\n\n"
                    "📍 **Où se déroulera l'entretien ?**"
                )
                result["actions"] = [
                    {"label": "🏢 Au bureau", "action": "set_location_bureau", "style": "primary"},
                    {"label": "💻 En visio (Teams/Zoom)", "action": "set_location_visio", "style": "primary"},
                    {"label": "☕ Dans un café", "action": "set_location_cafe", "style": "secondary"},
                    {"label": "✏️ Autre lieu", "action": "set_location_custom", "style": "secondary"},
                ]
            except Exception as e:
                result["message"] = f"❌ Erreur lors de la définition de la date : {e}"

        elif action.startswith("set_location_"):
            location_type = action.replace("set_location_", "")
            location_map = {
                "bureau": "Nos bureaux - Smart-Hire, 123 Avenue des Champs-Élysées, 75008 Paris",
                "visio": "Visioconférence - Lien envoyé par email",
                "cafe": "Café Le Procope, 13 Rue de l'Ancienne Comédie, 75006 Paris",
            }
            self.user_context["interview_location"] = location_map.get(location_type, "Lieu à définir")

            selected_candidates = self.user_context.get("selected_candidates", [])
            if not selected_candidates:
                fallback_single = self.user_context.get("selected_candidate")
                if fallback_single:
                    selected_candidates = [fallback_single]
            interview_date = self.user_context.get("interview_date")
            location = self.user_context.get("interview_location", "À définir")

            if selected_candidates and interview_date:
                from email_sender import send_interview_email
                try:
                    try:
                        from smtp_config import SMTP_CONFIG
                        sender_email = SMTP_CONFIG.get("sender_email")
                        sender_password = SMTP_CONFIG.get("sender_password")
                    except Exception:
                        sender_email = "smarthire221@gmail.com"
                        sender_password = "votre_mot_de_passe_app"

                    successes: List[str] = []
                    failures: List[str] = []
                    for cand in selected_candidates:
                        candidate_name = f"{cand.get('nom', '')} {cand.get('prenom', '')}"
                        recipient_email = cand.get("email", "")
                        email_sent = send_interview_email(
                            sender_email=sender_email,
                            sender_password=sender_password,
                            recipient_email=recipient_email,
                            candidate_name=candidate_name,
                            interview_date=interview_date,
                            location=location,
                            duration="1 heure",
                        )
                        (successes if email_sent else failures).append(f"- {candidate_name} ({recipient_email})")

                    if successes:
                        success_list = "\n".join(successes)
                        failure_block = "\n\n⚠️ Non envoyés :\n" + "\n".join(failures) if failures else ""
                        result["message"] = (
                            "✅ **Email(s) envoyé(s) avec succès !**\n\n"
                            f"📅 Date : {interview_date.strftime('%d/%m/%Y à %H:%M')}\n"
                            f"📍 Lieu : {location}\n\n"
                            f"Destinataires :\n{success_list}{failure_block}\n\n"
                            "Que voulez-vous faire ensuite ?"
                        )
                        result["actions"] = [
                            {"label": "📧 Inviter d'autres candidats", "action": "send_invitations", "style": "primary"},
                            {"label": "🔍 Nouvelle recherche", "action": "new_search", "style": "secondary"},
                            {"label": "📊 Voir les statistiques", "action": "help", "style": "secondary"},
                        ]
                    else:
                        result["message"] = (
                            "❌ **Erreur lors de l'envoi de l'email**\n\n"
                            "Vérifiez :\n- Credentials SMTP\n- Emails valides\n- Connexion Internet\n\nVoulez-vous réessayer ?"
                        )
                        result["actions"] = [
                            {"label": "🔄 Réessayer", "action": action, "style": "primary"},
                            {"label": "❌ Annuler", "action": "help", "style": "secondary"},
                        ]
                except Exception as e:
                    result["message"] = (
                        "❌ **Erreur lors de l'envoi**\n\n"
                        f"Détails : {e}\n\n💡 Configurez vos credentials SMTP."
                    )
                    result["actions"] = [
                        {"label": "⚙️ Configurer SMTP", "action": "help", "style": "primary"},
                        {"label": "❌ Annuler", "action": "help", "style": "secondary"},
                    ]
            else:
                result["message"] = "❌ Informations manquantes (candidat ou date)"

        # -------- Sync emails --------
        elif action == "sync_now":
            try:
                import os
                from sync_emails import sync_emails_with_database
                email_address = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_SENDER")
                app_password = os.getenv("SENDER_PASSWORD") or os.getenv("SMTP_PASSWORD")
                imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
                if not email_address or not app_password:
                    try:
                        from smtp_config import SMTP_CONFIG
                        email_address = email_address or SMTP_CONFIG.get("sender_email")
                        app_password = app_password or SMTP_CONFIG.get("sender_password")
                    except Exception:
                        pass
                if not email_address or not app_password:
                    result["message"] = "❌ Credentials email manquants. Configurez SENDER_EMAIL et SENDER_PASSWORD."
                    result["actions"] = [{"label": "❌ Fermer", "action": "acknowledge", "style": "secondary"}]
                    return result
                summary = sync_emails_with_database(email_address, app_password, imap_server)
                msg = [
                    "📥 **Synchronisation terminée**",
                    f"- Connexion: {'✅' if summary.get('connected') else '❌'}",
                    f"- Emails trouvés: {summary.get('emails_found', 0)}",
                    f"- CVs traités: {summary.get('cvs_processed', 0)}",
                    f"- Candidats ajoutés: {summary.get('cvs_added', 0)}",
                ]
                added = summary.get("candidates_added") or []
                if added:
                    noms = ", ".join([f"{c.get('prenom','')} {c.get('nom','')}" for c in added[:5]])
                    msg.append(f"- Nouveaux: {noms}")
                    if len(added) > 5:
                        msg.append(f"- (+{len(added)-5} autres)")
                errs = summary.get("errors") or []
                if errs:
                    msg.append(f"⚠️ Erreurs: {len(errs)} (voir log console)")
                result["message"] = "\n".join(msg)
                result["actions"] = [
                    {"label": "✅ OK", "action": "acknowledge", "style": "primary"},
                    {"label": "🔍 Nouvelle recherche", "action": "new_search", "style": "secondary"},
                ]
            except Exception as e:
                result["message"] = f"❌ Erreur synchronisation: {e}"
                result["actions"] = [{"label": "❌ Fermer", "action": "acknowledge", "style": "secondary"}]

        # -------- LinkedIn publication --------
        elif action == "publish_linkedin_job":
            job_desc = self.user_context.get("pending_linkedin_post", "")
            num_candidates = self.user_context.get("num_candidates", 1)
            try:
                oauth_instance = get_linkedin_oauth()
                if oauth_instance and oauth_instance.is_authenticated():
                    post_content = generate_linkedin_post_content(job_desc, num_candidates)
                    publish_result = oauth_instance.publish_post(post_content)
                    if publish_result.get("success"):
                        result["message"] = (
                            "✅ Post LinkedIn publié avec succès ! 🚀\n\n"
                            "Votre offre est maintenant visible sur LinkedIn."
                        )
                        result["actions"] = [
                            {"label": "📥 Synchroniser les emails", "action": "sync_now", "style": "primary"},
                            {"label": "🔍 Nouvelle recherche", "action": "new_search", "style": "secondary"},
                        ]
                    else:
                        result["success"] = False
                        result["message"] = f"❌ Erreur publication LinkedIn: {publish_result.get('message', 'Erreur inconnue')}"
                else:
                    result["message"] = (
                        "🔗 Authentification LinkedIn requise.\n"
                        "Cliquez pour obtenir le token automatiquement."
                    )
                    result["actions"] = [
                        {"label": "🔐 Obtenir le token LinkedIn", "action": "linkedin_get_token", "style": "primary"},
                        {"label": "❌ Annuler", "action": "new_search", "style": "secondary"},
                    ]
            except Exception as e:
                result["success"] = False
                result["message"] = f"❌ Erreur : {e}"

        elif action == "customize_linkedin_post":
            result["message"] = (
                "✏️ Personnaliser le post LinkedIn.\n"
                "Vous pouvez modifier le texte, les mots-clés et les avantages."
            )
            result["actions"] = [
                {"label": "🔗 Générer et publier", "action": "publish_linkedin_job", "style": "primary"},
                {"label": "📋 Voir le brouillon", "action": "view_draft", "style": "secondary"},
                {"label": "❌ Annuler", "action": "cancel", "style": "secondary"},
            ]

        elif action == "new_search":
            self.user_context.clear()
            result["message"] = (
                "🔍 **Nouvelle recherche**\n\n"
                "Quel profil cherchez-vous ?\n"
                "Exemples : '3 développeurs Python', '2 Data Scientists seniors'"
            )
            result["actions"] = [{"label": "🔍 Lancer une recherche", "action": "search_candidates", "style": "primary"}]

        elif action == "linkedin_oauth_login":
            try:
                oauth_instance = get_linkedin_oauth()
                if oauth_instance and oauth_instance.is_configured():
                    auth_url = oauth_instance.get_auth_url()
                    result["message"] = (
                        "🔗 Authentification LinkedIn\n\n"
                        "1) Ouvrez ce lien et autorisez :\n"
                        f"{auth_url}\n\n"
                        "2) Copiez le code obtenu et revenez."
                    )
                else:
                    result["message"] = "❌ Credentials LinkedIn manquants. Configurez client_id / secret."
            except Exception as e:
                result["message"] = f"❌ Erreur OAuth: {e}"

        elif action == "view_draft":
            result["message"] = (
                "📋 Brouillon du post LinkedIn.\n"
                "Consultez le dossier data/linkedin_drafts/ pour copier le contenu."
            )
            result["actions"] = [
                {"label": "🔗 Publier sur LinkedIn", "action": "publish_linkedin_job", "style": "primary"},
                {"label": "📥 Synchroniser emails", "action": "sync_now", "style": "secondary"},
            ]

        # -------- Démarrage génération de contrat --------
        elif action == "start_contract_generation":
            # Vérifier s'il y a des candidats en contexte
            selected_candidates = self.user_context.get("selected_candidates", [])
            matched_candidates = self.user_context.get("matched_candidates", [])
            
            if selected_candidates or matched_candidates:
                # Si on a des candidats, proposer les types de contrat
                candidates_list = selected_candidates if selected_candidates else matched_candidates
                if len(candidates_list) == 1:
                    # Un seul candidat, on le sélectionne directement
                    self.user_context["selected_candidates"] = [candidates_list[0]]
                    candidate = candidates_list[0]
                    result["message"] = (
                        f"📄 **Génération de contrat**\n\n"
                        f"👤 Candidat : {candidate.get('nom', '')} {candidate.get('prenom', '')}\n"
                        f"📧 Email : {candidate.get('email', '')}\n\n"
                        "Quel type de contrat souhaitez-vous générer ?"
                    )
                    result["actions"] = [
                        {"label": "📋 CDI", "action": "contract_cdi", "style": "primary"},
                        {"label": "📋 CDD", "action": "contract_cdd", "style": "primary"},
                        {"label": "📋 Stage", "action": "contract_stage", "style": "secondary"},
                        {"label": "📋 Freelance", "action": "contract_freelance", "style": "secondary"},
                    ]
                else:
                    # Plusieurs candidats, demander lequel
                    result["message"] = (
                        f"📄 **Génération de contrat**\n\n"
                        f"Vous avez {len(candidates_list)} candidat(s) disponible(s).\n"
                        "Sélectionnez le candidat pour lequel générer le contrat :"
                    )
                    result["actions"] = [
                        {
                            "label": f"👤 {c.get('nom', '')} {c.get('prenom', '')}",
                            "action": f"select_candidate_for_contract_{idx}",
                            "style": "primary" if idx == 0 else "secondary"
                        }
                        for idx, c in enumerate(candidates_list[:5])
                    ]
            else:
                # Pas de candidat en contexte, demander le nom
                result["message"] = (
                    "📄 **Génération de contrat**\n\n"
                    "Aucun candidat en contexte.\n\n"
                    "**Option 1:** Entrez le nom complet du candidat\n"
                    "(Format: Nom Prénom)\n\n"
                    "**Option 2:** Recherchez d'abord des candidats"
                )
                result["actions"] = [
                    {"label": "🔍 Rechercher des candidats", "action": "new_search", "style": "primary"},
                    {"label": "✏️ Saisir manuellement", "action": "enter_candidate_name", "style": "secondary"},
                ]

        elif action.startswith("select_candidate_for_contract_"):
            try:
                idx = int(action.split("_")[-1])
                candidates_list = self.user_context.get("selected_candidates", []) or self.user_context.get("matched_candidates", [])
                if 0 <= idx < len(candidates_list):
                    self.user_context["selected_candidates"] = [candidates_list[idx]]
                    candidate = candidates_list[idx]
                    result["message"] = (
                        f"📄 **Génération de contrat**\n\n"
                        f"👤 Candidat : {candidate.get('nom', '')} {candidate.get('prenom', '')}\n"
                        f"📧 Email : {candidate.get('email', '')}\n\n"
                        "Quel type de contrat souhaitez-vous générer ?"
                    )
                    result["actions"] = [
                        {"label": "📋 CDI", "action": "contract_cdi", "style": "primary"},
                        {"label": "📋 CDD", "action": "contract_cdd", "style": "primary"},
                        {"label": "📋 Stage", "action": "contract_stage", "style": "secondary"},
                        {"label": "📋 Freelance", "action": "contract_freelance", "style": "secondary"},
                    ]
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action == "enter_candidate_name":
            result["message"] = (
                "✏️ **Saisie manuelle du candidat**\n\n"
                "Entrez le nom complet du candidat (Format: Nom Prénom)\n"
                "Exemple: Benmoussa Rimen\n\n"
                "Le système recherchera ce candidat dans la base de données."
            )
            self.user_context["awaiting_candidate_name"] = True
            result["actions"] = [
                {"label": "❌ Annuler", "action": "cancel_candidate_entry", "style": "secondary"},
            ]

        elif action == "cancel_candidate_entry":
            self.user_context["awaiting_candidate_name"] = False
            result["message"] = "❌ Saisie annulée. Que voulez-vous faire ?"
            result["actions"] = [
                {"label": "🔍 Rechercher des candidats", "action": "new_search", "style": "primary"},
                {"label": "💡 Voir l'aide", "action": "help", "style": "secondary"},
            ]

        # -------- Génération de contrat --------
        elif action.startswith("contract_"):
            contract_type_map = {
                "contract_cdi": "CDI",
                "contract_cdd": "CDD",
                "contract_stage": "Stage",
                "contract_freelance": "Freelance"
            }
            contract_type = contract_type_map.get(action)
            
            if contract_type:
                # Vérifier s'il y a un candidat sélectionné
                selected_candidates = self.user_context.get("selected_candidates", [])
                if not selected_candidates:
                    # Essayer de trouver des candidats matchés
                    matched = self.user_context.get("matched_candidates", [])
                    if matched:
                        result["message"] = (
                            f"📄 **Génération de contrat {contract_type}**\n\n"
                            f"Vous avez {len(matched)} candidat(s) disponible(s).\n"
                            "Sélectionnez le candidat pour lequel générer le contrat :"
                        )
                        result["actions"] = [
                            {
                                "label": f"👤 {c.get('nom', '')} {c.get('prenom', '')}",
                                "action": f"select_for_contract_{action}_{idx}",
                                "style": "primary" if idx == 0 else "secondary"
                            }
                            for idx, c in enumerate(matched[:5])
                        ]
                    else:
                        result["message"] = (
                            "❌ Aucun candidat disponible.\n"
                            "Veuillez d'abord effectuer une recherche de candidats."
                        )
                        result["actions"] = [
                            {"label": "🔍 Rechercher des candidats", "action": "new_search", "style": "primary"}
                        ]
                else:
                    # Demander les informations du contrat
                    self.user_context["contract_type"] = contract_type
                    candidate = selected_candidates[0]
                    result["message"] = (
                        f"📄 **Génération de contrat {contract_type}**\n\n"
                        f"Candidat : {candidate.get('nom', '')} {candidate.get('prenom', '')}\n"
                        f"Email : {candidate.get('email', '')}\n\n"
                        "💰 Quel est le salaire annuel brut proposé ?\n"
                        "Exemples : 35000, 45000, 60000"
                    )
                    result["actions"] = [
                        {"label": "💰 35 000 €", "action": f"set_salary_{contract_type}_35000", "style": "primary"},
                        {"label": "💰 45 000 €", "action": f"set_salary_{contract_type}_45000", "style": "primary"},
                        {"label": "💰 55 000 €", "action": f"set_salary_{contract_type}_55000", "style": "secondary"},
                        {"label": "💰 65 000 €", "action": f"set_salary_{contract_type}_65000", "style": "secondary"},
                    ]

        elif action.startswith("select_for_contract_"):
            # Format: select_for_contract_contract_XXX_idx
            parts = action.replace("select_for_contract_", "").split("_")
            try:
                idx = int(parts[-1])
                original_action = "_".join(parts[:-1])  # contract_cdi, contract_cdd, etc.
                matched = self.user_context.get("matched_candidates", [])
                if 0 <= idx < len(matched):
                    self.user_context["selected_candidates"] = [matched[idx]]
                    # Rediriger vers l'action de contrat originale
                    return self.execute_action(original_action, params)
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action.startswith("set_salary_"):
            # Format: set_salary_CDI_35000 ou set_salary_CDD_45000
            parts = action.replace("set_salary_", "").split("_")
            try:
                contract_type = parts[0]
                salary = int(parts[1])
                self.user_context["contract_salary"] = salary
                self.user_context["contract_type"] = contract_type
                
                result["message"] = (
                    f"📅 **Date de début du contrat {contract_type}**\n\n"
                    f"💰 Salaire : {salary:,} € / an\n\n"
                    "Quand le contrat doit-il commencer ?"
                )
                now = datetime.now()
                result["actions"] = [
                    {"label": "📅 Dans 1 semaine", "action": f"set_contract_start_{contract_type}_{(now + timedelta(days=7)).strftime('%Y-%m-%d')}", "style": "primary"},
                    {"label": "📅 Dans 2 semaines", "action": f"set_contract_start_{contract_type}_{(now + timedelta(days=14)).strftime('%Y-%m-%d')}", "style": "primary"},
                    {"label": "📅 Dans 1 mois", "action": f"set_contract_start_{contract_type}_{(now + timedelta(days=30)).strftime('%Y-%m-%d')}", "style": "secondary"},
                ]
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action.startswith("set_contract_start_"):
            # Format: set_contract_start_CDI_2026-02-01
            parts = action.replace("set_contract_start_", "").split("_")
            try:
                contract_type = parts[0]
                start_date_str = parts[1]
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                self.user_context["contract_start_date"] = start_date
                
                if contract_type == "CDD":
                    # Pour un CDD, demander la date de fin
                    result["message"] = (
                        f"📅 **Date de fin du contrat CDD**\n\n"
                        f"📅 Début : {start_date.strftime('%d/%m/%Y')}\n\n"
                        "Quand le contrat doit-il se terminer ?"
                    )
                    result["actions"] = [
                        {"label": "📅 Dans 6 mois", "action": f"set_contract_end_CDD_{(start_date + timedelta(days=180)).strftime('%Y-%m-%d')}", "style": "primary"},
                        {"label": "📅 Dans 1 an", "action": f"set_contract_end_CDD_{(start_date + timedelta(days=365)).strftime('%Y-%m-%d')}", "style": "primary"},
                        {"label": "📅 Dans 18 mois", "action": f"set_contract_end_CDD_{(start_date + timedelta(days=540)).strftime('%Y-%m-%d')}", "style": "secondary"},
                    ]
                else:
                    # Pour les autres types, générer directement le contrat
                    return self.execute_action("generate_contract_now", params)
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action.startswith("set_contract_end_"):
            # Format: set_contract_end_CDD_2026-08-01
            parts = action.replace("set_contract_end_", "").split("_")
            try:
                contract_type = parts[0]
                end_date_str = parts[1]
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                self.user_context["contract_end_date"] = end_date
                
                # Générer le contrat
                return self.execute_action("generate_contract_now", params)
            except Exception as e:
                result["message"] = f"❌ Erreur : {e}"

        elif action == "generate_contract_now":
            try:
                from contract_generator import generate_contract
                
                selected_candidates = self.user_context.get("selected_candidates", [])
                if not selected_candidates:
                    result["message"] = "❌ Aucun candidat sélectionné."
                    return result
                
                candidate = selected_candidates[0]
                contract_type = self.user_context.get("contract_type")
                salary = self.user_context.get("contract_salary")
                start_date = self.user_context.get("contract_start_date")
                end_date = self.user_context.get("contract_end_date")
                
                if not all([contract_type, salary, start_date]):
                    result["message"] = "❌ Informations de contrat incomplètes."
                    return result
                
                # Générer le contrat
                contract_path = generate_contract(
                    candidate=candidate,
                    contract_type=contract_type,
                    salary=salary,
                    start_date=start_date,
                    end_date=end_date
                )
                
                candidate_name = f"{candidate.get('nom', '')} {candidate.get('prenom', '')}"
                result["message"] = (
                    "✅ **Contrat généré avec succès !**\n\n"
                    f"📄 Type : {contract_type}\n"
                    f"👤 Candidat : {candidate_name}\n"
                    f"💰 Salaire : {salary:,} € / an\n"
                    f"📅 Date de début : {start_date.strftime('%d/%m/%Y')}\n"
                )
                if end_date:
                    result["message"] += f"📅 Date de fin : {end_date.strftime('%d/%m/%Y')}\n"
                result["message"] += f"\n✅ PDF généré et prêt à télécharger !\n\nQue voulez-vous faire ensuite ?"
                
                # Ajouter le chemin du contrat dans les données
                result["data"]["contract_path"] = contract_path
                result["data"]["contract_filename"] = contract_path.split('/')[-1]
                
                result["actions"] = [
                    {"label": "📄 Générer un autre contrat", "action": "search_candidates", "style": "primary"},
                    {"label": "📧 Envoyer aux candidats", "action": "send_invitations", "style": "secondary"},
                    {"label": "🔍 Nouvelle recherche", "action": "new_search", "style": "secondary"},
                ]
                
                # Nettoyer le contexte du contrat
                for key in ["contract_type", "contract_salary", "contract_start_date", "contract_end_date"]:
                    self.user_context.pop(key, None)
                    
            except Exception as e:
                result["success"] = False
                result["message"] = f"❌ Erreur lors de la génération du contrat : {e}"

        elif action == "help":
            result["message"] = (
                "💡 Voici ce que je peux faire :\n"
                "- 🔍 Recherche de candidats\n"
                "- 📧 Invitations d'entretien\n"
                "- 📄 Génération de contrats\n"
                "- 📥 Synchronisation des emails\n"
                "- 🔗 Publication LinkedIn\n"
                "- 📊 Statistiques"
            )
            result["actions"] = [{"label": "🔍 Commencer une recherche", "action": "search_candidates", "style": "primary"}]

        return result

    # ==================== HELPERS ====================
    def _handle_candidate_name_input(self, user_message: str) -> Dict:
        """Gère la saisie du nom du candidat pour la génération de contrat"""
        result = {
            "success": True, 
            "message": "", 
            "response": "",
            "actions": [], 
            "data": {}, 
            "intent": "generate_contract", 
            "confidence": 1.0, 
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Charger les candidats de la base
            with open("data/cv_data.json", "r", encoding="utf-8") as f:
                cv_data = json.load(f)
            
            # Rechercher le candidat par nom
            name_parts = user_message.strip().split()
            found_candidates = []
            
            for candidate in cv_data:
                nom = candidate.get("nom", "").lower()
                prenom = candidate.get("prenom", "").lower()
                full_name = f"{nom} {prenom}".lower()
                search_name = user_message.lower()
                
                # Vérifier si le nom correspond
                if search_name in full_name or all(part.lower() in full_name for part in name_parts):
                    found_candidates.append(candidate)
            
            if len(found_candidates) == 1:
                # Un seul candidat trouvé
                candidate = found_candidates[0]
                self.user_context["selected_candidates"] = [candidate]
                self.user_context["awaiting_candidate_name"] = False
                
                message = (
                    f"✅ **Candidat trouvé !**\n\n"
                    f"👤 Nom : {candidate.get('nom', '')} {candidate.get('prenom', '')}\n"
                    f"📧 Email : {candidate.get('email', '')}\n"
                    f"💼 Poste : {candidate.get('poste', 'N/A')}\n\n"
                    "Quel type de contrat souhaitez-vous générer ?"
                )
                result["message"] = message
                result["response"] = message
                result["actions"] = [
                    {"label": "📋 CDI", "action": "contract_cdi", "style": "primary"},
                    {"label": "📋 CDD", "action": "contract_cdd", "style": "primary"},
                    {"label": "📋 Stage", "action": "contract_stage", "style": "secondary"},
                    {"label": "📋 Freelance", "action": "contract_freelance", "style": "secondary"},
                ]
            elif len(found_candidates) > 1:
                # Plusieurs candidats trouvés
                self.user_context["awaiting_candidate_name"] = False
                message = (
                    f"🔍 **{len(found_candidates)} candidats trouvés**\n\n"
                    "Veuillez sélectionner le bon candidat :"
                )
                result["message"] = message
                result["response"] = message
                result["actions"] = [
                    {
                        "label": f"👤 {c.get('nom', '')} {c.get('prenom', '')} - {c.get('email', '')}",
                        "action": f"select_candidate_for_contract_{idx}",
                        "style": "primary" if idx == 0 else "secondary"
                    }
                    for idx, c in enumerate(found_candidates[:5])
                ]
                self.user_context["matched_candidates"] = found_candidates
            else:
                # Aucun candidat trouvé
                message = (
                    f"❌ **Aucun candidat trouvé avec le nom '{user_message}'**\n\n"
                    "Options :\n"
                    "1️⃣ Vérifiez l'orthographe et réessayez\n"
                    "2️⃣ Recherchez dans tous les candidats\n"
                    "3️⃣ Créez un nouveau profil\n\n"
                    "Que souhaitez-vous faire ?"
                )
                result["message"] = message
                result["response"] = message
                result["actions"] = [
                    {"label": "✏️ Réessayer", "action": "enter_candidate_name", "style": "primary"},
                    {"label": "🔍 Rechercher des candidats", "action": "new_search", "style": "secondary"},
                    {"label": "❌ Annuler", "action": "help", "style": "secondary"},
                ]
        except Exception as e:
            result["success"] = False
            message = f"❌ Erreur lors de la recherche du candidat : {e}"
            result["message"] = message
            result["response"] = message
            result["actions"] = [
                {"label": "🔄 Réessayer", "action": "enter_candidate_name", "style": "primary"},
                {"label": "❌ Annuler", "action": "help", "style": "secondary"},
            ]
        
        self.conversation_history.append({
            "role": "assistant",
            "message": result["message"],
            "timestamp": datetime.now().isoformat(),
        })
        
        return result

    def _date_choices(self, now: datetime) -> List[Dict]:
        return [
            {"label": "📅 Demain 10h", "action": f"set_date_{(now + timedelta(days=1)).strftime('%Y-%m-%d')}_10:00", "style": "primary"},
            {"label": "📅 Demain 14h", "action": f"set_date_{(now + timedelta(days=1)).strftime('%Y-%m-%d')}_14:00", "style": "primary"},
            {"label": "📅 Après-demain 10h", "action": f"set_date_{(now + timedelta(days=2)).strftime('%Y-%m-%d')}_10:00", "style": "secondary"},
            {"label": "📅 Après-demain 15h", "action": f"set_date_{(now + timedelta(days=2)).strftime('%Y-%m-%d')}_15:00", "style": "secondary"},
            {"label": "❌ Annuler", "action": "send_invitations", "style": "secondary"},
        ]

    def get_conversation_history(self) -> List[Dict]:
        return self.conversation_history

    def clear_context(self):
        self.user_context = {}
        self.pending_action = None


# Instance globale du chatbot
chatbot = ChatbotEngine()
