from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/", methods=["POST"])
def debug_webhook():
    data = request.json
    print("\n=== Webhook Received ===")
    print("Full payload from Chatwoot:")
    print(data)
    print("=== End of Payload ===\n")
    
    # Try to extract some useful info
    message = data.get("message", {})
    conversation = data.get("conversation", {})
    
    print("Message info:", message)
    print("Conversation info:", conversation)
    
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def health():
    return "Debug bot is alive 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
