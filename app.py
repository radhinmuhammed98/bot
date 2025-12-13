from flask import Flask, request, jsonify
import os
import random
import requests

app = Flask(__name__)

# ======================
# ENV VARIABLES (SET IN RENDER DASHBOARD)
# ======================
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # https://app.chatwoot.com
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ======================
# FUN SYSTEM PROMPT
# ======================
SYSTEM_PROMPT = (
    "You are a friendly, playful Instagram DM assistant. "
    "Always call the user 'ponnu'. "
    "Speak casually like a Malayali friend. "
    "Never say you are an AI or bot. "
    "If asked who you are, say: I'm Radhin's personal assistant 😌. "
    "If confused, smoothly suggest playing a game. "
    "Keep replies short, fun, and human."
)

# ======================
# BAD WORD HANDLING
# ======================
BAD_WORDS = ["kundi", "kundii", "ass", "fuck", "shit", "myre", "myr", "punda"]

def handle_bad_words(msg):
    msg = msg.lower()
    for w in BAD_WORDS:
        if w in msg:
            return "Hehe ponnu 😄 kundi means ass in Malayalam alle? Chill da 😌"
    return None

# ======================
# GAME DETECTION
# ======================
GAME_TRIGGERS = [
    "play", "game", "kalikkam", "kalikk", "bore",
    "boring", "entha cheyyam", "oru game", "lets play"
]

def wants_game(msg):
    msg = msg.lower()
    return any(t in msg for t in GAME_TRIGGERS)

# ======================
# GAMES
# ======================
def start_game():
    game = random.choice(["guess", "emoji", "tod"])
    if game == "guess":
        return (
            "Ok ponnu 😌 game time 🎮\n\n"
            "I'm thinking of a number between 1 and 5 👀\n"
            "Guess cheyyu!"
        )
    elif game == "emoji":
        return (
            "Emoji game kalikkam ponnu 😏\n\n"
            "🍋 + 🍬 = ?"
        )
    else:
        return (
            "Ok ponnu 😌 Truth or Dare?\n\n"
            "Truth 😇 or Dare 😈 ?"
        )

def play_games(msg):
    if "3" in msg:
        return "Ayy correct ponnu 😌🔥 njan 3 aanu vicharichathu!"
    if "lemonade" in msg or "juice" in msg:
        return "Correct ponnu 😌🍹 lemonade!"
    return None

# ======================
# AI RESPONSE (OPENROUTER)
# ======================
def get_ai_reply(user_msg):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ]
            },
            timeout=20
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI ERROR:", e)
        return "Hmm ponnu 🤔 game kalikkam alle?"

def ai_confused(reply):
    triggers = ["not sure", "don't know", "confused", "can't understand"]
    return any(t in reply.lower() for t in triggers)

# ======================
# SEND MESSAGE TO CHATWOOT
# ======================
def send_message(conversation_id, text):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {
        "api_access_token": CHATWOOT_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "content": text,
        "message_type": "outgoing"
    }
    r = requests.post(url, headers=headers, json=payload)
    print("SEND STATUS:", r.status_code)

# ======================
# WEBHOOK
# ======================
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    if data.get("event") != "message_created":
        print("Ignoring non-message event")
        return "OK", 200

    if data.get("message_type") != "incoming":
        print("Ignoring outgoing message")
        return "OK", 200

    message = data.get("content", "")
    conversation_id = data["conversation"]["id"]

    print("Incoming message:", message)

    # 1️⃣ Bad words
    reply = handle_bad_words(message)

    # 2️⃣ User wants game
    if not reply and wants_game(message):
        reply = start_game()

    # 3️⃣ Game response
    if not reply:
        game_reply = play_games(message)
        if game_reply:
            reply = game_reply

    # 4️⃣ AI reply
    if not reply:
        reply = get_ai_reply(message)

        # 5️⃣ AI confused → game
        if ai_confused(reply):
            reply = start_game()

    send_message(conversation_id, reply)
    return "OK", 200

# ======================
# HEALTH CHECK
# ======================
@app.route("/", methods=["GET"])
def health():
    return "Bot alive ponnu 😌"

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
