from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Chatwoot credentials (set these in Render environment variables)
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL")  # Example: https://app.chatwoot.com

@app.route("/", methods=["POST"])
def chatwoot_echo_bot():
    data = request.json
    print("=== Webhook received! ===")
    print("Payload:", data)

    message_data = data.get("message")
    conversation_data = data.get("conversation")

    if not message_data or not conversation_data:
        print("No message or conversation data, ignoring.")
        return jsonify({"status": "ignored"}), 200

    # Only respond to incoming messages (ignore outgoing)
    if message_data.get("message_type") != "incoming":
        print("Message is not incoming, ignoring.")
        return jsonify({"status": "ignored"}), 200

    message_content = message_data.get("content")
    conversation_id = conversation_data.get("id")

    if not message_content:
        print("Message content empty, ignoring.")
        return jsonify({"status": "ignored"}), 200

    # Prepare API request to send the echo message
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_KEY}
    payload = {
        "content": f"Echo 🤖: {message_content}",
        "message_type": "outgoing"
    }

    print("Sending echo message...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        print("API response status:", response.status_code)
        print("API response body:", response.text)
        if response.status_code == 200:
            return jsonify({"status": "success"}), 200
        else:
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
