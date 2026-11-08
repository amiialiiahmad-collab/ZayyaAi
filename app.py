import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-deploying")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

database_url = os.environ.get("DATABASE_URL", "sqlite:///zayya.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    chats = db.relationship("Chat", backref="user", cascade="all, delete-orphan")

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(160), default="New chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship("Message", backref="chat", cascade="all, delete-orphan",
                               order_by="Message.created_at")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@app.get("/")
def home():
    if not current_user():
        return redirect(url_for("login"))
    return redirect(url_for("chat_page"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or len(password) < 8:
            flash("Enter a valid email and a password with at least 8 characters.")
            return render_template("auth.html", mode="register")
        if User.query.filter_by(email=email).first():
            flash("That email already has an account. Please sign in.")
            return render_template("auth.html", mode="register")
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return redirect(url_for("chat_page"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Email or password is incorrect.")
            return render_template("auth.html", mode="login")
        session.clear()
        session["user_id"] = user.id
        return redirect(url_for("chat_page"))
    return render_template("auth.html", mode="login")

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/chat")
def chat_page():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).all()
    return render_template("chat.html", chats=chats, active_chat=None)

@app.post("/api/chats")
def create_chat():
    user = current_user()
    if not user:
        return jsonify(error="Please sign in again."), 401
    chat = Chat(user_id=user.id)
    db.session.add(chat)
    db.session.commit()
    return jsonify(id=chat.id, title=chat.title)

@app.get("/api/chats/<int:chat_id>")
def get_chat(chat_id):
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id if user else -1).first()
    if not chat:
        return jsonify(error="Chat not found."), 404
    return jsonify(id=chat.id, title=chat.title,
                   messages=[{"role": m.role, "content": m.content} for m in chat.messages])

@app.delete("/api/chats/<int:chat_id>")
def delete_chat(chat_id):
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id if user else -1).first()
    if not chat:
        return jsonify(error="Chat not found."), 404
    db.session.delete(chat)
    db.session.commit()
    return jsonify(ok=True)

@app.post("/api/chats/<int:chat_id>/messages")
def send_message(chat_id):
    user = current_user()
    if not user:
        return jsonify(error="Please sign in again."), 401
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        return jsonify(error="Chat not found."), 404
    data = request.get_json(silent=True) or {}
    prompt = (data.get("message") or "").strip()
    if not prompt:
        return jsonify(error="Write a message first."), 400

    api_key = os.environ.get("YAKAL_API_KEY")
    if not api_key:
        return jsonify(error="AI service is not configured yet. Add YAKAL_API_KEY in Render environment variables."), 503

    prior = [{"role": m.role, "content": m.content} for m in chat.messages]
    user_message = Message(chat_id=chat.id, role="user", content=prompt)
    db.session.add(user_message)
    db.session.commit()
    messages = prior + [{"role": "user", "content": prompt}]

    try:
        response = requests.post(
            "https://api.yakal.et/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": os.environ.get("YAKAL_MODEL", "glm-5.3-flash"),
                  "messages": messages, "temperature": 0.7},
            timeout=90
        )
        if response.status_code >= 400:
            return jsonify(error=f"AI provider returned status {response.status_code}. Check API key, model and wallet."), 502
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        db.session.add(Message(chat_id=chat.id, role="assistant", content=answer))
        if chat.title == "New chat":
            chat.title = prompt[:48] + ("…" if len(prompt) > 48 else "")
        db.session.commit()
        return jsonify(reply=answer, title=chat.title)
    except requests.RequestException:
        return jsonify(error="Could not reach the AI service. Please try again."), 502
    except (KeyError, IndexError, ValueError):
        return jsonify(error="The AI service returned an unexpected response."), 502

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
