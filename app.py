from flask import Flask, request
import requests
import os
from collections import defaultdict, deque
import time
import random

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
ALLOWED_USERNAMES = {"Radhin³³", "jasm!..n", "radhin"}

# =========================
# Memory & State (PRUNED)
# =========================
conversation_memory = defaultdict(lambda: deque(maxlen=12))
last_game_offer = defaultdict(lambda: 0)
active_games = {}

GAME_COOLDOWN = 1800

# =========================
# System Prompt
# =========================
SYSTEM_PROMPT = """
You are a playful, witty, mildly flirty Instagram DM assistant talking to jasmin.
Tone: confident, teasing, friendly, sarcastic — never desperate.

Rules:
1. Max 2 short sentences.
2. Use jasmin’s name naturally when possible.
3. Flirting must be indirect and playful.
4. No paragraphs, no robotic tone.
5. Use only emojis: 🫣😹😏😌😒🫠🧑‍🦯👊
6. Understand misspellings, slang, and mixed languages.
7. If the message is Malayalam or mixed Malayalam-English, understand it but reply in English.
8. Only suggest games if chat feels dry.
9. Keep replies mobile-friendly and human.
"""

# =========================
# AI Call (with fallback)
# =========================
def call_model(model, messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def get_ai_reply(user_message, memory):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if memory:
        messages.append({
            "role": "system",
            "content": "Conversation summary: " + " | ".join(memory)
        })

    messages.append({"role": "user", "content": user_message})

    try:
        return call_model(PRIMARY_MODEL, messages)
    except Exception:
        return call_model(FALLBACK_MODEL, messages)

# =========================
# Games
# =========================
def start_number_game(username):
    number = random.randint(1, 10)
    active_games[username] = number
    return "Alright jasmin, guess a number between 1 and 10 😏"


def handle_number_game(username, message):
    try:
        guess = int(message.strip())
    except ValueError:
        return "Just a number, jasmin 😹"

    number = active_games.get(username)
    if guess == number:
        del active_games[username]
        return "Correct… okay that was impressive 😌👊"
    elif guess < number:
        return "Too low, jasmin 😏"
    else:
        return "Too high… confidence though 😹"

# =========================
# Webhook
# =========================
@app.route("/", methods=["POST"])
def chatwoot_ai_bot():
    data = request.json

    if data.get("message_type") != "incoming":
        return "OK", 200

    message = data.get("content", "").strip()
    conversation = data.get("conversation")
    sender = data.get("sender")
    username = sender.get("name") if sender else None

    if not username or username not in ALLOWED_USERNAMES:
        return "OK", 200

    if not message or not conversation:
        return "OK", 200

    conversation_id = conversation["id"]

    # Store memory
    conversation_memory[username].append(message)

    # Active game handling
    if username in active_games:
        reply = handle_number_game(username, message)
        send_message(conversation_id, reply)
        return "OK", 200

    # Generate reply
    try:
        reply = get_ai_reply(message, conversation_memory[username])
    except Exception:
        reply = "Something slipped there… continue 😌"

    # Smart boredom detection
    boring_inputs = {"ok", "hmm", "idk", "lol", "fine", "🙂"}
    now = time.time()

    if message.lower() in boring_inputs and now - last_game_offer[username] > GAME_COOLDOWN:
        reply += "\n\nWanna play a quick guessing game, jasmin? 😏"
        last_game_offer[username] = now

    # Start game trigger
    if "guess" in message.lower() and now - last_game_offer[username] < 60:
        reply = start_number_game(username)

    send_message(conversation_id, reply)
    return "OK", 200

# =========================
# Send Message
# =========================
def send_message(conversation_id, content):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {"content": content, "message_type": "outgoing"}
    requests.post(url, headers=headers, json=payload)

# =========================
# Health
# =========================
@app.route("/", methods=["GET"])
def health():
    return "Bot alive 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
