from flask import Flask, request, jsonify
import requests
import os
from collections import defaultdict
import time

app = Flask(__name__)

# =========================
# Chatwoot Config
# =========================
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")

# =========================
# OpenRouter Config
# =========================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Model (better conversational tone than LLaMA 3.1 8B)
AI_MODEL = "deepcogito/cogito-v2-preview-deepseek-671b"

# =========================
# Allowed Users (username lock)
# =========================
ALLOWED_USERNAMES = {
    "Radhin³³",
    "jasm!n",
    "Friend1"
}

# =========================
# Memory & State
# =========================
conversation_memory = defaultdict(list)
intro_sent = defaultdict(bool)
last_game_offer = defaultdict(lambda: 0)

GAME_COOLDOWN = 1800  # 30 minutes

# =========================
# System Prompt
# =========================
SYSTEM_PROMPT = """
You are a witty, sarcastic, friendly, and playful Instagram DM assistant talking to Jasmin. 
Your goal is to keep her engaged, make the chat fun, and impress her subtly. 

Rules for replies:
1. Maximum 2 sentences.
2. Friendly, sarcastic, funny, casual tone.
3. Only use these emojis: 🫣😹😏😌😒🫠🧑‍🦯👊
4. Never write paragraphs, never repeat greetings.
5. Remember the conversation context for continuity.
6. Never overshare, hype, flirt directly, or sound robotic.
7. Only ask to play a game if the chat seems dead:
   - User hasn’t replied in a while OR
   - Last few messages are short, neutral, or one-word.
8. If she asks about Radhin, reply honestly but short.
9. Keep replies mobile-friendly and punchy.
10. Let the user lead the conversation, don’t push questions.
"""





# =========================
# AI Call
# =========================
def get_ai_reply(user_message, memory):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if memory:
        messages.append({
            "role": "system",
            "content": f"Conversation so far: {' '.join(memory[-20:])}"
        })

    messages.append({"role": "user", "content": user_message})

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# =========================
# Webhook
# =========================
@app.route("/", methods=["POST"])
def chatwoot_ai_bot():
    data = request.json
    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    if data.get("message_type") != "incoming":
        return "OK", 200

    message = data.get("content")
    conversation = data.get("conversation")
    sender = data.get("sender")
    username = sender.get("name") if sender else None

    # Username lock
    if not username or username not in ALLOWED_USERNAMES:
        print(f"⛔ Blocked user: {username}")
        return "OK", 200

    if not message or not conversation:
        return "OK", 200

    conversation_id = conversation["id"]

    # English-only (soft)
    if any(ord(c) > 127 for c in message):
        reply = "Could you type that in English? I don’t want to misunderstand 🙂"
        send_message(conversation_id, reply)
        return "OK", 200

    # Store memory
    conversation_memory[username].append(message)

    # One-time soft intro
  #  reply_prefix = ""
   # if not intro_sent[username]:
      #  reply_prefix = f"You’re Jasmin, right? Radhin mentioned you once 🙂\n\n"
    #    intro_sent[username] = True

    # Generate AI reply
    try:
        ai_reply = get_ai_reply(message, conversation_memory[username])
    except Exception as e:
        print("AI ERROR:", e)
        ai_reply = "Hmm… something slipped there. Continue 🙂"

    reply = ai_reply

    # Game offer ONLY if chat feels dead
    boredom_keywords = ["ok", "hmm", "idk", "nothing", "fine"]
    if message.lower().strip() in boredom_keywords:
        now = time.time()
        if now - last_game_offer[username] > GAME_COOLDOWN:
            reply += "\n\nIf you’re bored, we can play a quick game."
            last_game_offer[username] = now

    send_message(conversation_id, reply)
    return "OK", 200

# =========================
# Send Message
# =========================
def send_message(conversation_id, content):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {
        "content": content,
        "message_type": "outgoing"
    }
    r = requests.post(url, headers=headers, json=payload)
    print("Sent:", r.status_code)

# =========================
# Health
# =========================
@app.route("/", methods=["GET"])
def health():
    return "Bot alive 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
