from flask import Flask, request, jsonify
import requests
import os
from collections import defaultdict
import time

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

# In-memory conversation memory (username -> list of previous messages)
conversation_memory = defaultdict(list)
MEMORY_LIMIT = 10  # max messages to remember per user

# Track last game prompt timestamp to avoid spamming
last_game_prompt = defaultdict(lambda: 0)
GAME_COOLDOWN = 3600  # seconds, 1 hour

def get_ai_reply(user_message, memory_context=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add memory context if available
    if memory_context:
        messages.append({"role": "system", "content": f"Previous conversation: {memory_context}"})
    
    messages.append({"role": "user", "content": user_message})

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "messages": messages
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
    contact = data.get("sender")
    username = contact.get("name") if contact else None

    if not message or not conversation or not username:
        return jsonify({"status": "ignored"}), 200

    conversation_id = conversation["id"]

    # Update memory
    memory_context = ""
    if username:
        conversation_memory[username].append(message)
        # Trim memory if too long
        if len(conversation_memory[username]) > MEMORY_LIMIT:
            conversation_memory[username] = conversation_memory[username][-MEMORY_LIMIT:]
        memory_context = " ".join(conversation_memory[username])

    # Language check: force English
    non_english_chars = sum(1 for c in message if ord(c) > 127)
    if non_english_chars > len(message) / 2:
        ai_reply = "Ponnu 😅, can we talk in English? It's easier for me to understand."
    else:
        try:
            ai_reply = get_ai_reply(message, memory_context)
        except Exception as e:
            print("AI ERROR:", e)
            ai_reply = "Oops ponnu 😅, something went wrong, let's continue chatting!"

    # Optional: if user seems sad or message contains sad words, suggest game
    sad_keywords = ["sad", "tired", "bad", "angry", "upset"]
    if any(word in message.lower() for word in sad_keywords):
        now = time.time()
        if now - last_game_prompt[username] > GAME_COOLDOWN:
            ai_reply += " Hey ponnu, want to play a fun game to cheer up? 🎮"
            last_game_prompt[username] = now

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
