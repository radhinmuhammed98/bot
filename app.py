from flask import Flask, request, jsonify
import os
import random
from collections import defaultdict, deque
import openai  # assuming you use OpenAI API for AI responses

# =========================
# CONFIGURATION
# =========================
ALLOWED_CONTACT_IDS = {
    17849491164062639,   # Radhin
    17842619055463689,   # Friend 1
    17848297094995525,   # Friend 2
}

CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # Example: https://app.chatwoot.com

openai.api_key = os.environ.get("OPENAI_API_KEY")  # put your key here

# =========================
# MEMORY: Store last few messages per contact
# =========================
conversation_memory = defaultdict(lambda: deque(maxlen=10))

app = Flask(__name__)

# -------------------------
# HELPER FUNCTION: Send reply
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
# WEBHOOK
# -------------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    # Only handle incoming messages
    if data.get("event") != "message_created" or data.get("message_type") != "incoming":
        return "OK", 200

    conversation_id = data["conversation"]["id"]
    contact_id = data.get("sender", {}).get("id")
    print("CONTACT ID:", contact_id)

    # Allowlist check
    if contact_id not in ALLOWED_CONTACT_IDS:
        print("⛔ User not allowed, ignoring")
        return "OK", 200

    # Get user message
    message = data.get("content") or "User sent an attachment or reply"
    print("USER MESSAGE:", message)

    # Store message in memory
    conversation_memory[contact_id].append({"role": "user", "content": message})

    # Decide response
    response = generate_response(contact_id, message)

    # Store bot response in memory
    conversation_memory[contact_id].append({"role": "assistant", "content": response})

    # Send response
    send_message(conversation_id, response)

    return "OK", 200


# -------------------------
# AI RESPONSE GENERATOR
# -------------------------
def generate_response(contact_id, message):
    """
    Generate thoughtful, friendly replies.
    Use 'ponnu' carefully.
    Only play game if user explicitly asks.
    """

    # Detect explicit game request
    if any(word in message.lower() for word in ["game", "kalikkaan", "play"]):
        return "Sure ponnu 😌, let's play! Which game do you want to start?"

    # Detect bad words / friendly handling
    if any(word in message.lower() for word in ["kundi"]):
        return "Haha ponnu 😎, don't worry! I know what you mean 😅"

    # Bot introduction
    if "your name" in message.lower() or "who are you" in message.lower():
        return "I'm your personal assistant ponnu, here to help and chat with you 😌"

    # Use AI for thoughtful replies
    try:
        memory_list = list(conversation_memory[contact_id])
        # Construct prompt
        prompt = "You are a friendly, thoughtful assistant. Use 'ponnu' naturally. Reply to the user message logically and kindly.\n\n"
        for msg in memory_list:
            role = msg["role"]
            content = msg["content"]
            prompt += f"{role}: {content}\n"
        prompt += "assistant:"

        # Call OpenAI API (GPT)
        ai_resp = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        )
        reply = ai_resp.choices[0].text.strip()
        return reply or "Hmm ponnu 😌, I need a moment to think about that..."
    except Exception as e:
        print("Error in AI response:", e)
        return "Oops ponnu 😅, something went wrong, let's continue chatting!"
        

# -------------------------
# Health check
# -------------------------
@app.route("/", methods=["GET"])
def health():
    return "Bot is alive 🚀"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
