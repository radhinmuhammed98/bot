from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/", methods=["POST"])
def chatwoot_bot():
    data = request.json
    print("Incoming payload:", data)

    message = "Couldn't read your message 😅"

    # Chatwoot message formats (safe handling)
    if "message" in data and data["message"]:
        message = data["message"].get("content", message)

    elif "conversation" in data:
        last_msg = data["conversation"].get("last_message")
        if last_msg:
            message = last_msg.get("content", message)

    return jsonify({
        "messages": [
            {
                "content": f"Echo 🤖: {message}",
                "content_type": "text"
            }
        ]
    })


@app.route("/", methods=["GET"])
def health():
    return "Bot is alive 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
