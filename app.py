from flask import Flask, request
import os
import requests
import random
from collections import defaultdict, deque

ALLOWED_CONTACT_IDS = {
    598323826,   # Radhin
    123456789,   # Friend 1
    987654321,   # Friend 2
}

app = Flask(__name__)

# =========================
# ENV VARIABLES (SET IN RENDER)
# =========================
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # https://app.chatwoot.com
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# =========================
# MEMORY (PER CONVERSATION)
# =========================
conversation_memory = defaultdict(lambda: deque(maxlen=10))

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = (
    "You are a friendly, playful Instagram DM assistant. "
    "Always call the user 'ponnu'. "
    "Talk casually like a Malayali friend. "
    "Never say you are an AI or bot. "
    "If asked who you are, say: I'm Radhin's personal assistant 😌. "
    "If confused, suggest playing a game. "
    "Keep replies short and fun."
)

# =========================
# BAD WORD HANDLING
# =========================
BAD_WORDS = ["kundi", "kundii", "ass", "fuck", "shit", "myre", "myr", "punda"]

def handle_bad_words(text):
    text = text.lower()
    for w in BAD_WORDS:
        if w in text:
            return "Hehe ponnu 😄 kundi means ass in Malayalam alle? Chill da 😌"
    return None

# =========================
# GAME DETECTION
# =========================
GAME_TRIGGERS = [
    "play", "game", "kalikkam", "kalikk",
    "bore", "boring", "oru game", "lets play",
    "entha cheyyam"
]

def wants_game(text):
    text = text.lower()
    return any(t in text for t in GAME_TRIGGERS)

# =========================
# GAMES
# =========================
def start_game():
    game = random.choice(["guess", "emoji", "tod"])
    if game == "guess":
        return (
            "Ok ponnu 😌 game time 🎮\n"
            "I'm thinking of a number between 1 and 5 👀\n"
            "Guess cheyyu!"
        )
    elif game == "emoji":
        return (
            "Emoji game kalikkam ponnu 😏\n\n"
            "🍋 + 🍬 = ?"
        )
    else:
        return "Ok ponnu 😌 Truth or Dare?\nTruth 😇 or Dare 😈 ?"

def play_game(text):
    if "3" in text:
        return "Ayy correct ponnu 😌🔥 njan 3 aanu vicharichathu!"
    if "lemonade" in text or "juice" in text:
        return "Correct ponnu 😌🍹 lemonade!"
    return None

# =========================
# AI WITH MEMORY
# =========================
def get_ai_reply(conversation_id):
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(conversation_memory[conversation_id])

        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": messages
            },
            timeout=20
        )

        reply = r.json()["choices"][0]["message"]["content"]
        return reply

    except Exception as e:
        print("AI ERROR:", e)
        return "Hmm ponnu 🤔 game kalikkam alle?"

def ai_confused(text):
    triggers = ["not sure", "don't know", "confused", "can't understand"]
    return any(t in text.lower() for t in triggers)

# =========================
# SEND MESSAGE TO CHATWOOT
# =========================
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

# =========================
# WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    # Only message events
    if data.get("event") != "message_created":
        return "OK", 200

    if data.get("message_type") != "incoming":
        return "OK", 200

    conversation_id = data["conversation"]["id"]

    # =========================
    # CONTACT RESTRICTION
    # =========================
    contact_id = data.get("sender", {}).get("id")
    print("CONTACT ID:", contact_id)

    if contact_id not in ALLOWED_CONTACT_IDS:
        print("⛔ User not allowed, ignoring")
        return "OK", 200
        
    # Handle text / replies / attachments
    message = data.get("content")
    if not message:
        if data.get("attachments"):
            message = "User sent an attachment"
        else:
            message = "User replied to a message"

    print("USER MESSAGE:", message)

    # Save user message to memory
    conversation_memory[conversation_id].append(
        {"role": "user", "content": message}
    )

    reply = None

    # 1️⃣ Bad words
    reply = handle_bad_words(message)

    # 2️⃣ User wants game
    if not reply and wants_game(message):
        reply = start_game()

    # 3️⃣ Playing game
    if not reply:
        game_reply = play_game(message.lower())
        if game_reply:
            reply = game_reply

    # 4️⃣ AI response
    if not reply:
        reply = get_ai_reply(conversation_id)
        if ai_confused(reply):
            reply = start_game()

    # Save bot reply to memory
    conversation_memory[conversation_id].append(
        {"role": "assistant", "content": reply}
    )

    send_message(conversation_id, reply)
    return "OK", 200

# =========================
# HEALTH CHECK
# =========================
@app.route("/", methods=["GET"])
def health():
    return "Bot alive ponnu 😌"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
