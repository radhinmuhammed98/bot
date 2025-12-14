from flask import Flask, request
import requests
import os
import time
import random
from collections import defaultdict, deque

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

PRIMARY_MODEL = "meta-llama/Llama-3.1-8b-instruct"
FALLBACK_MODEL = "deepseek/deepseek-chat"

# =========================
# Allowed Users
# =========================
ALLOWED_USERNAMES = {"Radhin³³", "✈︎"}

# =========================
# Memory & State
# =========================
conversation_memory = defaultdict(lambda: deque(maxlen=12))
last_game_offer = defaultdict(int)
active_games = {}  # username -> number
personality_level = defaultdict(int)  # flirt intensity

GAME_COOLDOWN = 1800  # 30 min

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are a witty, flirty, sarcastic Instagram DM assistant chatting with Abhinav.

Personality:
- Confident, teasing, playful 😏
- Friendly sarcasm, never needy
- Slight flirt, never creepy
- Reads the room well

Rules:
1. Max 2 short sentences.
2. Never paragraphs.
3. Never repeat greetings.
4. Use ONLY these emojis: 🫣😹😏😌😒🫠🧑‍🦯👊
5. Use Abhinav's name naturally when possible.
6. If user writes Malayalam or mixed language, understand it and reply in English.
7. Ignore spelling mistakes and slang.
8. If chat feels dry, suggest a game casually.
9. Never explain rules unless asked.
10. Replies must feel human, not AI.
"""

# =========================
# AI CALL WITH FALLBACK
# =========================
def call_ai(model, messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def get_ai_reply(user_message, username):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_memory[username]:
        messages.append({
            "role": "system",
            "content": "Conversation memory: " + " | ".join(conversation_memory[username])
        })

    messages.append({"role": "user", "content": user_message})

    try:
        return call_ai(PRIMARY_MODEL, messages)
    except:
        return call_ai(FALLBACK_MODEL, messages)

# =========================
# GAME LOGIC
# =========================
def handle_game(username, message):
    if username not in active_games:
        return None

    try:
        guess = int(message.strip())
    except:
        return "Just a number, vroo 😹"

    target = active_games[username]

    if guess == target:
        del active_games[username]
        return "Boom 😏 You got it. Lucky or smart?"
    elif guess < target:
        return "Higher 😌"
    else:
        return "Lower 😹"

# =========================
# WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def chatwoot_bot():
    data = request.json

    if data.get("message_type") != "incoming":
        return "OK", 200

    message = data.get("content", "").strip()
    sender = data.get("sender", {})
    username = sender.get("name")

    if username not in ALLOWED_USERNAMES or not message:
        return "OK", 200

    conversation = data.get("conversation")
    conversation_id = conversation["id"]

    # Store memory
    conversation_memory[username].append(message)

    # GAME ACTIVE?
    game_reply = handle_game(username, message)
    if game_reply:
        send_message(conversation_id, game_reply)
        return "OK", 200

    # Personality drift (slowly gets flirtier)
    personality_level[username] = min(personality_level[username] + 1, 5)

    try:
        ai_reply = get_ai_reply(message, username)
    except:
        ai_reply = "Hmm… try again 😌"

    reply = ai_reply

    # Detect boredom
    boredom = message.lower() in {"ok", "hmm", "idk", "fine", "nothing", "lol"}

    if boredom:
        now = time.time()
        if now - last_game_offer[username] > GAME_COOLDOWN:
            active_games[username] = random.randint(1, 10)
            reply += "\n\nQuick game, huh? Guess 1–10 😏"
            last_game_offer[username] = now

    send_message(conversation_id, reply)
    return "OK", 200

# =========================
# SEND MESSAGE
# =========================
def send_message(conversation_id, content):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {"content": content, "message_type": "outgoing"}
    requests.post(url, headers=headers, json=payload)

# =========================
# HEALTH
# =========================
@app.route("/", methods=["GET"])
def health():
    return "Bot alive 😏"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
