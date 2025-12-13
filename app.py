from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["POST"])
def chatwoot_bot():
    data = request.json
    print("Incoming:", data)

    message = "Couldn't read your message 😅"
    try:
        message = data["conversation"]["messages"][0]["content"]
    except:
        pass

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
    app.run()
