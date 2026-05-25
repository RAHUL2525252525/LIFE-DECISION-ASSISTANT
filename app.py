from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import json
import os
import requests
from dotenv import load_dotenv
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

# -------------------------------
# CONFIGURATION & ENV
# -------------------------------
load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "nexus_default_key")

USER_FILE = "users.json"

# API KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Google OAuth Setup
GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

def get_google_flow():
    return Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/google/callback")
    )

# -------------------------------
# DATA PERSISTENCE
# -------------------------------
def load_users():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# INTELLIGENT AI ENGINE (WITH FALLBACK)
# FIX: Updated models + added response validation + better error logging
# -------------------------------
def ask_groq(prompt):
    if not GROQ_API_KEY:
        print("DEBUG Groq: API key not set")
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        # FIX: Updated to a current, stable model
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if content:
                return content
            print("DEBUG Groq: Empty content in response")
        else:
            print(f"DEBUG Groq: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"DEBUG Groq Exception: {e}")
    return None

def ask_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        print("DEBUG OpenRouter: API key not set")
        return None
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # FIX: OpenRouter recommends these headers
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Life Decision Assistant"
        }
        # FIX: Use a reliably available free model on OpenRouter
        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if content:
                return content
            print("DEBUG OpenRouter: Empty content in response")
        else:
            print(f"DEBUG OpenRouter: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"DEBUG OpenRouter Exception: {e}")
    return None

def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        print("DEBUG Gemini: API key not set")
        return None
    try:
        # FIX: Use gemini-1.5-flash (stable endpoint)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            # FIX: Safer nested access to avoid KeyError on unexpected response shapes
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    content = parts[0].get("text", "").strip()
                    if content:
                        return content
            print(f"DEBUG Gemini: Unexpected response structure: {result}")
        else:
            print(f"DEBUG Gemini: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"DEBUG Gemini Exception: {e}")
    return None

def ask_ai(prompt):
    """Try Groq → OpenRouter → Gemini with fallback chain."""
    for engine_fn in [ask_groq, ask_openrouter, ask_gemini]:
        reply = engine_fn(prompt)
        if reply:
            return reply
    return "⚠️ Neural Link Offline. All AI engines are currently unresponsive. Please check your API keys in the .env file."

# -------------------------------
# AUTHENTICATION ROUTES
# -------------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        users = load_users()

        if email in users and users[email].get("password") == password:
            session['user'] = email
            flash("Access Granted. Welcome to the Nexus.", "success")
            return redirect(url_for('index'))
        
        flash("Identity not found or Invalid Keyphrase.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        users = load_users()

        if email in users:
            flash("Identity already registered.", "error")
            return render_template("register.html")

        users[email] = {"name": name, "password": password, "provider": "email"}
        save_users(users)
        flash("Registration successful!", "success")
        return redirect(url_for("login"))
    return render_template("register.html")
    
@app.route("/forgot-password", methods=["GET","POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        users = load_users()

        if email not in users:
            flash("Identity not found in the Nexus.", "error")
            return redirect(url_for("forgot_password"))

        if new_password != confirm_password:
            flash("Keyphrases do not match. Try again.", "error")
            return redirect(url_for("forgot_password"))

        users[email]["password"] = new_password
        save_users(users)
        flash("Keyphrase successfully reset! You can now login.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

# -------------------------------
# GOOGLE OAUTH
# -------------------------------
@app.route("/google/login")
def google_login():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/google/callback")
def google_callback():
    flow = get_google_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    userinfo_endpoint = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info = requests.get(userinfo_endpoint, params={"access_token": credentials.token}).json()
    
    email = user_info["email"]
    name = user_info.get("name", "User")
    session["user"] = email
    
    users = load_users()
    if email not in users:
        users[email] = {"name": name, "password": "google_user", "provider": "google"}
        save_users(users)
    return redirect(url_for("index"))

# -------------------------------
# PAGE ROUTES (GET)
# -------------------------------
@app.route("/index")
def index():
    if "user" not in session: return redirect(url_for("login"))
    users = load_users()
    name = users.get(session["user"], {}).get("name", "User")
    return render_template("index.html", name=name)

@app.route("/career")
def career():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("career.html")

@app.route("/decision")
def decision():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("decision.html")

@app.route("/goalplanner")
def goalplanner():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("goalplanner.html")

@app.route("/skillgap")
def skillgap():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("skillgap.html")

@app.route("/comparison")
def comparison():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("comparison.html")

@app.route("/chatbot")
def chatbot():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("chatbot.html")

# -------------------------------
# AI API ROUTES (POST)
# -------------------------------
@app.route("/career_api", methods=["POST"])
def career_api():
    if "user" not in session: return jsonify({"reply": "Session expired."})
    data = request.get_json()
    prompt = f"Career advisor. Interest: {data.get('interest')}, Skills: {data.get('skills')}. Provide Roadmap."
    return jsonify({"reply": ask_ai(prompt)})

@app.route("/decision_api", methods=["POST"])
def decision_api():
    if "user" not in session: return jsonify({"reply": "Session expired."})
    data = request.get_json()
    prompt = f"Professional life decision advisor. Situation: {data.get('situation')}"
    return jsonify({"reply": ask_ai(prompt)})

@app.route("/goalplanner_api", methods=["POST"])
def goalplanner_api():
    if "user" not in session: return jsonify({"reply": "Session expired."})
    data = request.get_json()
    prompt = f"Create step-by-step plan for: {data.get('goal')}. Include milestones."
    return jsonify({"reply": ask_ai(prompt)})

@app.route("/skillgap_api", methods=["POST"])
def skillgap_api():
    if "user" not in session: return jsonify({"reply": "Session expired."})
    data = request.get_json()
    prompt = f"Analyze skill gaps for {data.get('career')} based on {data.get('skills')}."
    return jsonify({"reply": ask_ai(prompt)})

@app.route("/compare_api", methods=["POST"])
def compare_api():
    if "user" not in session: return jsonify({"reply": "Session expired."})
    data = request.get_json()
    prompt = f"Compare A: {data.get('option1')} and B: {data.get('option2')} for Goal: {data.get('goal')}."
    return jsonify({"reply": ask_ai(prompt)})

@app.route("/chatbot_api", methods=["POST"])
def chatbot_api():
    if "user" not in session: return jsonify({"reply": "Login required"})
    data = request.get_json()
    return jsonify({"reply": ask_ai(data.get("message", ""))})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
