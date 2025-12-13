from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Chatwoot credentials (set these in Render environment variables)
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # e.g., https://app.chatwoot.com

@app.route("/", methods=["POST"])
def chatwoot_echo_bot():
    data = request.json
    print("\n=== Webhook received! ===")
    print("Full payload:", data)

    # Extract message content
    message_content = data.get("content")
    conversation = data.get("conversation")
    message_type = data.get("message_type", "incoming")

    if not message_content or not conversation:
        print("No message or conversation data, ignoring.")
        return jsonify({"status": "ignored"}), 200

    # Only respond to incoming messages
    if message_type != "incoming":
        print("Message is not incoming, ignoring.")
        return jsonify({"status": "ignored"}), 200

    conversation_id = conversation.get("id")
    if not conversation_id:
        print("Conversation ID missing, cannot send message.")
        return jsonify({"status": "ignored"}), 200

    # Prepare API request to send echo
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {
        "content": f" {message_content}",
        "message_type": "outgoing"
    }

    print(f"Sending echo message to conversation {conversation_id}...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        print("API response status:", response.status_code)
        print("API response body:", response.text)
        if response.status_code == 200:
            print("Message sent successfully ✅")
            return jsonify({"status": "success"}), 200
        else:
            print("Failed to send message ❌")
            return jsonify({"status": "error"}), 500
    except Exception as e:
        print("Exception while sending message:", e)
        return jsonify({"status": "exception"}), 500

@app.route("/", methods=["GET"])
def health():
    return "Bot is alive 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
