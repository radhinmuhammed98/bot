from flask import Flask, request, jsonify
import os
import requests
from collections import defaultdict, deque

# =========================
# CONFIGURATION
# =========================
ALLOWED_CONTACT_IDS = {
    17849491164062639,   # Radhin,   # Radhin
    17842619055463689,   # Friend 1
    17848297094995525,   # Friend 2
}

CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # Example: https://app.chatwoot.com

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")  # LLaMA API key
OPENROUTER_MODEL = "llama-2-7b-chat"  # Change if using another LLaMA model

# =========================
# MEMORY: Last 10 messages per user
# =========================
conversation_memory = defaultdict(lambda: deque(maxlen=10))

app = Flask(__name__)

# -------------------------
# HELPER FUNCTION: Send message via Chatwoot
# -------------------------
def send_message(conversation_id, content):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {"content": content, "message_type": 1}  # 1 = outgoing
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Message sent, status: {resp.status_code}")
    except Exception as e:
        print("Error sending message:", e)

# -------------------------
# AI RESPONSE GENERATOR using OpenRouter LLaMA
# -------------------------
def generate_response(contact_id, message):
    """
    Friendly, thoughtful replies using OpenRouter LLaMA.
    Only plays game if user explicitly asks.
    """

    # Only play games if user asks
    if any(word in message.lower() for word in ["game", "kalikkaan", "play"]):
        return "Sure ponnu 😌, let's play! Which game do you want to start?"

    # Friendly handling of bad words
    if any(word in message.lower() for word in ["kundi"]):
        return "Haha ponnu 😎, I know what you mean 😅"

    # Bot introduction
    if "your name" in message.lower() or "who are you" in message.lower():
        return "I'm your personal assistant ponnu, here to help and chat with you 😌"

    # Construct messages for LLaMA
    try:
        memory_list = list(conversation_memory[contact_id])
        messages = [{"role": m["role"], "content": m["content"]} for m in memory_list]
        messages.append({"role": "user", "content": message})

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.7
        }
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

        resp = requests.post("https://api.openrouter.ai/v1/chat/completions", json=payload, headers=headers)
        resp_json = resp.json()
        reply = resp_json["choices"][0]["message"]["content"]

        return reply or "Hmm ponnu 😌, I need a moment to think about that..."
    except Exception as e:
        print("Error in AI response:", e)
        return "Oops ponnu 😅, something went wrong, let's continue chatting!"

# -------------------------
# WEBHOOK
# -------------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    # Only message events
    if data.get("event") != "message_created" or data.get("message_type") != "incoming":
        return "OK", 200

    conversation_id = data["conversation"]["id"]
    contact_id = data.get("sender", {}).get("id")
    print("CONTACT ID:", contact_id)

    # Restrict access
    if contact_id not in ALLOWED_CONTACT_IDS:
        print("⛔ User not allowed, ignoring")
        return "OK", 200

    # Get user message (handle attachments & replies)
    message = data.get("content")
    if not message:
        if data.get("attachments"):
            message = "User sent an attachment"
        else:
            message = "User replied to a message"

    print("USER MESSAGE:", message)

    # Store message in memory
    conversation_memory[contact_id].append({"role": "user", "content": message})

    # Generate response
    response = generate_response(contact_id, message)

    # Store bot response in memory
    conversation_memory[contact_id].append({"role": "assistant", "content": response})

    # Send reply
    send_message(conversation_id, response)

    return "OK", 200

# -------------------------
# HEALTH CHECK
# -------------------------
@app.route("/", methods=["GET"])
def health():
    return "Bot is alive 🚀"

# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
