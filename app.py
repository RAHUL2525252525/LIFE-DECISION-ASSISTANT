from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import json
import os
import requests

from google_auth_oauthlib.flow import Flow

# Allow HTTP for localhost
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# -------------------------------
# FILE PATHS
# -------------------------------
USER_FILE = "users.json"
GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

# -------------------------------
# CREATE FLASK APP
# -------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# -------------------------------
# API KEYS
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# -------------------------------
# USER DATABASE FUNCTIONS
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
# GOOGLE LOGIN
# -------------------------------
@app.route("/google/login")
def google_login():

    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=url_for("google_callback", _external=True)
    )

    authorization_url, state = flow.authorization_url()

    session["state"] = state

    return redirect(authorization_url)


# -------------------------------
# GOOGLE CALLBACK
# -------------------------------
@app.route("/google/callback")
def google_callback():

    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=url_for("google_callback", _external=True)
    )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    userinfo_endpoint = "https://www.googleapis.com/oauth2/v1/userinfo"

    response = requests.get(
        userinfo_endpoint,
        params={"access_token": credentials.token}
    )

    user_info = response.json()

    email = user_info["email"]
    name = user_info.get("name", "User")

    session["user"] = email

    users = load_users()

    if email not in users:
        users[email] = {
            "name": name,
            "password": "google_user",
            "provider": "google"
        }

    save_users(users)

    return redirect(url_for("index"))

    # -------------------------------
# AI FUNCTIONS
# -------------------------------

def ask_groq(prompt):

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama3-8b-8192",
            "messages":[
                {
                    "role":"system",
                    "content":"You are a friendly AI assistant. Use emojis, simple language, and bullet points."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        print("Groq Failed:", e)
        return None


def ask_openrouter(prompt):

    try:

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "meta-llama/llama-3-8b-instruct",
            "messages":[
                {
                    "role":"system",
                    "content":"You are a helpful AI assistant. Use emojis and simple explanations."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        print("OpenRouter Failed:", e)
        return None


def ask_gemini(prompt):

    try:

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

        data = {
            "contents":[
                {
                    "parts":[
                        {"text":prompt}
                    ]
                }
            ]
        }

        response = requests.post(url, json=data)
        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Failed:", e)
        return None


# -------------------------------
# AI AUTO SWITCH
# -------------------------------

def ask_ai(prompt):

    print("Trying GROQ...")
    reply = ask_groq(prompt)

    if reply:
        return reply

    print("Trying OPENROUTER...")
    reply = ask_openrouter(prompt)

    if reply:
        return reply

    print("Trying GEMINI...")
    reply = ask_gemini(prompt)

    if reply:
        return reply

    return "⚠️ AI engine failed. Please try again."


# -------------------------------
# HOME
# -------------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# -------------------------------
# LOGIN
# -------------------------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        users = load_users()

        if email not in users:
            flash("Identity not found in the Nexus.", "error")
            return render_template("login.html")

        if users[email]["password"] != password:
            flash("Invalid Keyphrase. Access Denied.", "error")
            return render_template("login.html")

        session["user"] = email

        flash("Access Granted. Welcome to the Nexus.", "success")

        return redirect(url_for("index"))

    return render_template("login.html")


# -------------------------------
# REGISTER
# -------------------------------
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        users = load_users()

        if email in users:
            flash("User already registered with this email. Please Login.", "error")
            return render_template("register.html")

        users[email] = {
            "name": name,
            "password": password,
            "provider": "email"
        }

        save_users(users)

        flash("Registration successful! Welcome to the Nexus.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# -------------------------------
# DASHBOARD
# -------------------------------
@app.route("/index")
def index():

    if "user" not in session:
        return redirect(url_for("login"))

    users = load_users()

    email = session["user"]

    name = users.get(email, {}).get("name", "User")

    return render_template("index.html", name=name)


# -------------------------------
# CAREER TOOL
# -------------------------------
@app.route("/career")
def career():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("career.html")


@app.route("/career_api", methods=["POST"])
def career_api():

    data = request.get_json()

    interest = data.get("interest","")
    skills = data.get("skills","")

    prompt = f"""
You are a friendly career advisor.

User Interest: {interest}
User Skills: {skills}

Give a very simple and clear answer.

🎯 Best Career
💡 Why This Career
📚 Skills to Learn
🚀 Simple Roadmap
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})


# -------------------------------
# DECISION TOOL
# -------------------------------
@app.route("/decision")
def decision():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("decision.html")


@app.route("/decision_api", methods=["POST"])
def decision_api():

    data = request.get_json()

    situation = data.get("situation","")

    prompt = f"""
User Situation: {situation}

Give clear decision advice with reasoning.
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})


# -------------------------------
# GOAL PLANNER
# -------------------------------
@app.route("/goalplanner")
def goalplanner():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("goalplanner.html")


@app.route("/goalplanner_api", methods=["POST"])
def goalplanner_api():

    data = request.get_json()

    goal = data.get("goal","")

    prompt = f"""
Create a simple step-by-step plan for this goal:

{goal}
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})


# -------------------------------
# SKILL GAP ANALYZER
# -------------------------------
@app.route("/skillgap")
def skillgap():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("skillgap.html")


@app.route("/skillgap_api", methods=["POST"])
def skillgap_api():

    data = request.get_json()

    career = data.get("career","")
    skills = data.get("skills","")

    prompt = f"""
Career: {career}

Current Skills: {skills}

Suggest missing skills.
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})


# -------------------------------
# COMPARISON TOOL
# -------------------------------
@app.route("/comparison")
def comparison():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("comparison.html")


@app.route("/compare_api", methods=["POST"])
def compare_api():

    data = request.get_json()

    option1 = data.get("option1","")
    option2 = data.get("option2","")
    goal = data.get("goal","")

    prompt = f"""
Compare these two options.

Option A: {option1}
Option B: {option2}

Goal: {goal}

Choose the best option and explain briefly.
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})


# -------------------------------
# CHATBOT
# -------------------------------
@app.route("/chatbot")
def chatbot():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("chatbot.html")


@app.route("/chatbot_api", methods=["POST"])
def chatbot_api():

    data = request.get_json()

    message = data.get("message","")

    reply = ask_ai(message)

    return jsonify({"reply": reply})


# -------------------------------
# LOGOUT
# -------------------------------
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
