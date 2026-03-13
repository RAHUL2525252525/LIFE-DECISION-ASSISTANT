from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import requests

import os
import pathlib
import requests

from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from flask import Flask, session, redirect, url_for, request,flash

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


USER_FILE = "users.json"

GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

flow = Flow.from_client_secrets_file(
    GOOGLE_CLIENT_SECRETS_FILE,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="http://127.0.0.1:5000/google/callback"
)

# 🔑 PUT YOUR OPENROUTER API KEY HERE
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

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
# OPENROUTER AI FUNCTION
# -------------------------------
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
# MAIN AI FUNCTION (AUTO SWITCH)
# -------------------------------

def ask_ai(prompt):

    print("Trying GROQ AI...")
    reply = ask_groq(prompt)

    if reply:
        return reply

    print("Trying OPENROUTER AI...")
    reply = ask_openrouter(prompt)

    if reply:
        return reply

    print("Trying GEMINI AI...")
    reply = ask_gemini(prompt)

    if reply:
        return reply

    return "⚠️ AI engine failed. Please try again."
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

        # Logic for "Identity not found" or "Invalid Password"
        if email not in users:
            flash("Identity not found in the Nexus.", "error")
            return render_template("login.html")
        
        if users[email].get("password") != password:
            flash("Invalid Keyphrase. Access Denied.", "error")
            return render_template("login.html")

        # Success path
        session['user'] = email
        flash("Access Granted. Welcome to the Nexus.", "success")
        return redirect(url_for('index'))

    return render_template("login.html")

@app.route("/google/login")
def google_login():

    authorization_url, state = flow.authorization_url()

    session["state"] = state

    return redirect(authorization_url)

@app.route("/google/callback")
def google_callback():

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    request_session = requests.session()

    userinfo_endpoint = "https://www.googleapis.com/oauth2/v1/userinfo"

    params = {"access_token": credentials.token}

    userinfo_response = request_session.get(userinfo_endpoint, params=params)

    user_info = userinfo_response.json()

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

# @app.route("/google/callback")
# def google_callback():

#     flow.fetch_token(authorization_response=request.url)

#     credentials = flow.credentials

#     request_session = requests.session()

#     userinfo_endpoint = "https://www.googleapis.com/oauth2/v1/userinfo"

#     params = {"access_token": credentials.token}

#     userinfo_response = request_session.get(userinfo_endpoint, params=params)

#     user_info = userinfo_response.json()

#     email = user_info["email"]

#     session["user"] = email

#     users = load_users()
#     if email not in users:
#         users[email] = {"password": "google_user"}
#     save_users(users)

#     return redirect(url_for("index"))

# -------------------------------
# REGISTER
# -------------------------------
# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         name = request.form["name"]
#         email = request.form["email"]
#         password = request.form["password"]
#         users = load_users()
#         if email in users:
#             return "User already exists"
#         users[email] = {"name": name, "password": password}
#         save_users(users)
#         return redirect(url_for("login"))
#     return render_template("register.html")

from flask import Flask, render_template, request, redirect, url_for, flash

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        users = load_users()

        # 1. Check if email already exists
        if email in users:
            # Using 'error' category to match your CSS class .flash.error
            flash("User already registered with this email. Please Login.", "error")
            return render_template("register.html")

        # 2. Create new user if it doesn't exist
        users[email] = {
            "name": name,
            "password": password, # In a real app, use generate_password_hash(password)
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
# def index():
#     if "user" not in session:
#         return redirect(url_for("login"))
#     users = load_users()
#     name = users[session["user"]]["name"]
#     return render_template("index.html", name=name)

# -------------------------------
# CAREER TOOL
# -------------------------------
@app.route("/career", methods=["GET", "POST"])
def career():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("career.html")
# -------------------------------
# CAREER API (AJAX)
# -------------------------------
@app.route("/career_api", methods=["POST"])
def career_api():
    if "user" not in session:
        return jsonify({"reply": "Please login first."})

    data = request.get_json()

    interest = data.get("interest", "")
    skills = data.get("skills", "")

    prompt = f"""
You are a friendly career advisor.

User Interest: {interest}
User Skills: {skills}

Give a very simple and clear answer.

Use this format exactly:

🎯 **Best Career**
Write one short sentence suggesting the best career.

💡 **Why This Career**
• Reason 1  
• Reason 2  
• Reason 3  

📚 **Skills to Learn**
• Skill 1  
• Skill 2  
• Skill 3  

🚀 **Simple Roadmap**
1️⃣ Step 1  
2️⃣ Step 2  
3️⃣ Step 3  

Rules:
- Use simple English
- Keep answers short
- Use emojis
- Use bullet points
- Make it easy for beginners
"""

    reply = ask_ai(prompt)

    return jsonify({"reply": reply})
# -------------------------------
# DECISION TOOL
# -------------------------------
@app.route("/decision", methods=["GET", "POST"])
def decision():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("decision.html")

# ---- Decision API ----
@app.route("/decision_api", methods=["POST"])
def decision_api():
    data = request.get_json()
    situation = data.get("situation")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "system",
                        "content": """
You are a professional life decision advisor.
Rules:
- Give clear human-style reasoning.
- NEVER use tags like [ANALYSIS].
- Do not write system logs or debug messages.
- Format strictly: 
  • Insight 1
  • Insight 2
  • Insight 3
Decision: Final recommendation with explanation.
"""
                    },
                    {"role": "user", "content": f"My situation: {situation}"}
                ]
            }
        )

        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": ai_reply})

    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"reply": "❌ AI could not process the decision. Try again."})
    
# -------------------------------
@app.route("/goalplanner", methods=["GET", "POST"])
def goalplanner():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("goalplanner.html")

# -------------------------------
# GOAL PLANNER API
# -------------------------------
@app.route("/goalplanner_api", methods=["POST"])
def goalplanner_api():
    if "user" not in session:
        return jsonify({"reply": "❌ Please login first."})

    data = request.get_json()
    goal = data.get("goal", "").strip()

    if not goal:
        return jsonify({"reply": "⚠️ Please provide a valid goal."})

    prompt = f"""
    Create a clear step-by-step plan to achieve this goal:
    {goal}.
    Include milestones, timeline, and tips. Add emojis for clarity.
    """

    reply = ask_ai(prompt)
    return jsonify({"reply": reply})

# -------------------------------
# SKILL GAP ANALYZER
# -------------------------------
@app.route("/skillgap", methods=["GET", "POST"])
def skillgap():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("skillgap.html")

@app.route("/skillgap_api", methods=["POST"])
def skillgap_api():
    data = request.get_json()
    career = data.get("career", "")
    skills = data.get("skills", "")
    prompt = f"""
    For a career in {career}, analyze the skill gaps if someone
    currently has these skills: {skills}.
    Suggest important skills to learn. Present the answer with bullets, emojis, and spaces for clarity.
    """
    reply = ask_ai(prompt)
    return jsonify({"reply": reply})

# -------------------------------
# COMPARISON TOOL
@app.route("/comparison")
def comparison():
    if "user" not in session:
        return redirect(url_for("login"))  # make sure login exists
    return render_template("comparison.html")

@app.route("/compare_api", methods=["POST"])
def compare_api():

    if "user" not in session:
        return jsonify({"reply": "❌ Please login first."})

    data = request.get_json()

    option1 = data.get("option1","")
    option2 = data.get("option2","")
    goal = data.get("goal","")

    prompt = f"""
You are a helpful decision assistant.

Compare these two options in very simple English.

Option A: {option1}
Option B: {option2}

User Goal: {goal}

Give the answer in this format:

🅰️ Option A
Explain in 1–2 short lines.

🅱️ Option B
Explain in 1–2 short lines.

🎯 Final Suggestion
Choose ONLY ONE option (A or B).
Clearly say which option is BEST for the user's goal and give 1 short reason.

Rules:
- Use simple language
- Keep answers short
- Be clear and confident
- Always choose ONE final option
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
    if "user" not in session:
        return jsonify({"reply": "Login required"})
    data = request.get_json()
    message = data.get("message", "")
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
