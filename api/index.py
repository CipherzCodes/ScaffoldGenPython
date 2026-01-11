from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

CORS(app)


@app.route("/")
def home():
    return jsonify({
        "message": "Flask app running on Vercel 🚀"
    })


@app.route("/hello", methods=["GET"])
def hello():
    name = request.args.get("name", "World")
    return jsonify({
        "hello": name
    })

# IMPORTANT:
# Do NOT use app.run()
# Vercel will import `app` automatically
