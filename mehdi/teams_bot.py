"""
🤖 BOT TEAMS SMART-HIRE - VERSION FINALE FONCTIONNELLE
Pas de BotFrameworkAdapter - Traitement manuel des activités
"""

import os
import asyncio
import json
from flask import Flask, request, Response
from botbuilder.core import TurnContext, BotAdapter, InvokeResponse
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount
from dotenv import load_dotenv
from chatbot_engine import ChatbotEngine

load_dotenv()

# Configuration (depuis .env)
APP_ID = os.getenv("MICROSOFT_APP_ID", "")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")

print(f"🔑 APP_ID: {APP_ID if APP_ID else 'NON DEFINI'}")
if APP_PASSWORD:
    print("🔑 APP_PASSWORD: ********")
else:
    print("🔑 APP_PASSWORD: NON DEFINI")

# Initialiser le chatbot
chatbot = ChatbotEngine()

app = Flask(__name__)

# Stockage des dernier réponses pour debugging
last_responses = []
last_request = None


class SimpleAdapter(BotAdapter):
    """Adaptateur personnalisé sans validation JWT"""
    
    def __init__(self):
        self.responses = []
    
    async def send_activities(self, context: TurnContext, activities):
        """Envoyer les activités"""
        print(f"📤 Envoi de {len(activities)} activité(s)")
        
        response_ids = []
        for activity in activities:
            print(f"   ✅ {activity.type}: {activity.text[:50] if activity.text else ''}")
            response_ids.append(activity.id or "unknown")
            self.responses.append(activity)
        
        return response_ids
    
    async def delete_activity(self, context: TurnContext, reference):
        """Supprimer une activité"""
        pass
    
    async def update_activity(self, context: TurnContext, activity):
        """Mettre à jour une activité"""
        pass


# Créer l'adaptateur personnalisé
ADAPTER = SimpleAdapter()




async def on_message_activity(context: TurnContext):
    """Traiter les messages"""
    try:
        user_message = context.activity.text
        user_id = context.activity.from_property.id if context.activity.from_property else "unknown"
        
        print(f"📩 Message de {user_id}: {user_message}")
        
        # Obtenir la réponse du chatbot
        result = chatbot.process_message(user_message)
        response_text = result.get("response", "Je n'ai pas compris votre message.")
        
        print(f"✅ Réponse générée: {response_text}")
        
        # Créer un ChannelAccount pour le destinataire (l'utilisateur)
        recipient_account = ChannelAccount(
            id=context.activity.from_property.id if context.activity.from_property else "user",
            name=context.activity.from_property.name if context.activity.from_property else "User"
        )
        
        # Créer une activité de réponse avec tous les champs requis
        reply_activity = Activity(
            type=ActivityTypes.message,
            text=response_text,
            reply_to_id=context.activity.id,
            conversation=context.activity.conversation,
            recipient=recipient_account,
            from_property=ChannelAccount(
                id=context.activity.recipient.id if context.activity.recipient else "28:49c10136-0c24-4053-be90-3133bb75ebed",
                name=context.activity.recipient.name if context.activity.recipient else "SMART-HIRE Bot"
            )
        )
        
        # Envoyer la réponse
        await context.send_activity(reply_activity)
        print("✅ Réponse envoyée !")
        
    except Exception as e:
        print(f"❌ Erreur message: {e}")
        import traceback
        traceback.print_exc()


async def on_conversation_update(context: TurnContext):
    """Traiter la mise à jour de conversation"""
    try:
        for member in context.activity.members_added:
            if member.id != context.activity.recipient.id:
                welcome = (
                    "👋 **Bienvenue sur SMART-HIRE Bot !**\n\n"
                    "Je suis votre assistant de recrutement IA.\n\n"
                    "Comment puis-je vous aider ?"
                )
                
                # Créer une activité de bienvenue avec tous les champs requis
                welcome_activity = Activity(
                    type=ActivityTypes.message,
                    text=welcome,
                    conversation=context.activity.conversation,
                    recipient=context.activity.from_property,
                    from_property=ChannelAccount(
                        id="28:49c10136-0c24-4053-be90-3133bb75ebed",
                        name="SMART-HIRE Bot"
                    )
                )
                
                await context.send_activity(welcome_activity)
                print("✅ Message de bienvenue envoyé")
    except Exception as e:
        print(f"⚠️ Erreur bienvenue: {e}")


async def on_turn(context: TurnContext):
    """Traiter toutes les activités"""
    if context.activity.type == ActivityTypes.message:
        await on_message_activity(context)
    elif context.activity.type == ActivityTypes.conversation_update:
        await on_conversation_update(context)
    elif context.activity.type == ActivityTypes.typing:
        print("⌨️ L'utilisateur tape...")


@app.route("/api/messages", methods=["POST", "OPTIONS"])
def messages():
    """Endpoint principal - Retourner les réponses dans la réponse HTTP"""
    global last_responses, last_request
    
    if request.method == "OPTIONS":
        return Response(status=200)
    
    try:
        body = request.get_json(force=True)
        last_request = body
        
        if not body:
            print("❌ Body vide")
            return Response(status=400)
        
        print("\n" + "="*80)
        print("🔍 DEBUGGING - Requête reçue")
        print("="*80)
        print(f"📥 Type d'activité: {body.get('type')}")
        if body.get('type') == 'message':
            print(f"   Message: {body.get('text', '')}")
        
        # Désérialiser l'activité
        activity = Activity().deserialize(body)
        
        # Réinitialiser les réponses
        ADAPTER.responses = []
        
        # Créer un contexte de tour
        context = TurnContext(ADAPTER, activity)
        
        print(f"🔄 Traitement de l'activité...")
        
        # Traiter l'activité
        task = on_turn(context)
        asyncio.run(task)
        
        print(f"📤 Réponses générées: {len(ADAPTER.responses)}")
        
        # Sérialiser et retourner les réponses
        if ADAPTER.responses:
            print(f"\n✅ Envoi des réponses au Web Chat...")
            
            # Retourner les réponses sérialisées
            responses_json = [r.serialize() for r in ADAPTER.responses]
            last_responses = responses_json
            
            # Afficher chaque réponse
            for idx, resp in enumerate(responses_json):
                print(f"   Réponse #{idx + 1}: {resp.get('text', '')[:50]}")
                print(f"   ✅ HTTP 200 - Réponse retournée au Web Chat")
            
            print("\n" + "="*80)
            print("✅ Traitement terminé")
            print("="*80 + "\n")
            
            # Retourner la première réponse (Web Chat accepte une activité)
            return responses_json[0], 200, {'Content-Type': 'application/json'}
        
        print("\n" + "="*80)
        print("✅ Traitement terminé (aucune réponse)")
        print("="*80 + "\n")
        
        return Response(status=200)
        
    except Exception as ex:
        print(f"\n❌ ERREUR: {ex}")
        import traceback
        traceback.print_exc()
        return Response(status=200)
@app.route("/", methods=["GET"])
def home():
    return "<h1>🤖 Smart-Hire Bot</h1><p>En fonctionnement sur le port 3978</p>", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy", "bot": "SMART-HIRE", "version": "4.0"}, 200


@app.route("/debug/last-request", methods=["GET"])
def debug_last_request():
    """Afficher la dernière requête reçue"""
    global last_request
    if last_request:
        return {
            "title": "Dernière requête",
            "request": last_request
        }, 200
    return {"error": "Aucune requête enregistrée"}, 404


@app.route("/debug/last-responses", methods=["GET"])
def debug_last_responses():
    """Afficher les dernières réponses envoyées"""
    global last_responses
    if last_responses:
        return {
            "title": "Dernières réponses",
            "responses": last_responses,
            "count": len(last_responses)
        }, 200
    return {"error": "Aucune réponse enregistrée"}, 404


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3978))
    print(f"\n🚀 Bot Teams SMART-HIRE (V4.0) sur le port {port}")
    print(f"📡 Endpoint: http://localhost:{port}/api/messages")
    print(f"🔗 Ngrok: https://osteopathically-unrepossessed-shanice.ngrok-free.dev/api/messages")
    print(f"✨ Adaptateur personnalisé - Pas de validation JWT")
    print("Press CTRL+C to quit\n")
    app.run(host="0.0.0.0", port=port, debug=False)

