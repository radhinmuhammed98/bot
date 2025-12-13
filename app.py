from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Chatwoot
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")

# OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

AI_MODEL = "meta-llama/llama-3.1-8b-instruct"

SYSTEM_PROMPT = (
    "You are a friendly, playful Instagram DM assistant. "
    "Always address the user as 'ponnu' naturally (like Malayali style). "
    "Your tone should be chill, fun, and human-like. "
    "Do NOT say you are an AI or bot. "
    "If someone asks your name or who you are, say: "
    "'I'm Radhin's personal assistant 😌'. "
    "If someone uses slang or bad words, reply calmly and humorously, "
    "not aggressively or judgmentally. "
    "Keep replies short and casual."
)

def get_ai_reply(user_message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

@app.route("/", methods=["POST"])
def chatwoot_ai_bot():
    data = request.json
    print("\n=== Incoming webhook ===")
    print(data)

    # Ignore non-incoming / bot messages
    if data.get("message_type") != "incoming":
        return jsonify({"status": "ignored"}), 200

    message = data.get("content")
    conversation = data.get("conversation")

    if not message or not conversation:
        return jsonify({"status": "ignored"}), 200

    conversation_id = conversation["id"]

    try:
        ai_reply = get_ai_reply(message)
    except Exception as e:
        print("AI ERROR:", e)
        ai_reply = "Sorry, I didn’t get that. Could you rephrase?"

    # Send reply to Chatwoot
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {
        "content": ai_reply,
        "message_type": "outgoing"
    }

    res = requests.post(url, headers=headers, json=payload)
    print("Chatwoot response:", res.status_code, res.text)

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def health():
    return "AI Bot is running 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
