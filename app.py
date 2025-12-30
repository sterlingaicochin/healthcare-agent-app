import streamlit as st
import json
import os
from datetime import date
from statistics import mean
from fpdf import FPDF
import google.generativeai as genai

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config("Diabetic Support Agent", layout="centered")
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --------------------------------------------------
# GEMINI SETUP (SAFE)
# --------------------------------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_NAME = "models/gemini-1.5-flash"

def safe_ai(prompt):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return None  # fallback

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "result" not in st.session_state:
    st.session_state.result = None

# --------------------------------------------------
# STORAGE
# --------------------------------------------------
def user_file(username):
    return f"{DATA_DIR}/{username}.json"

def load_history(username):
    try:
        with open(user_file(username), "r") as f:
            return json.load(f)
    except:
        return []

def save_history(username, data):
    with open(user_file(username), "w") as f:
        json.dump(data, f, indent=2)

# --------------------------------------------------
# ANALYSIS LOGIC
# --------------------------------------------------
def detect_pattern(history):
    if len(history) < 3:
        return "insufficient data"

    recent = history[-3:]
    f = mean(d["fasting"] for d in recent)
    p = mean(d["post"] for d in recent)

    if f > 180 or p > 250:
        return "very high readings"
    if f < 70:
        return "very low readings"
    if f < 120:
        return "stable routine"
    return "mixed pattern"

def confidence(entry):
    score = 100
    if entry["fasting"] > 160 or entry["fasting"] < 70:
        score -= 30
    if entry["sleep"] < 6:
        score -= 20
    if entry["activity"] == "low":
        score -= 20
    if entry["medication"] == "no":
        score -= 30
    return max(score, 0)

# --------------------------------------------------
# AI TODAY FOCUS (DYNAMIC)
# --------------------------------------------------
def ai_today_focus(username, age, entry):
    prompt = f"""
User: {username}, Age: {age}
You are a diabetic daily-support assistant.

Today's data:
Fasting sugar: {entry['fasting']}
Post-meal sugar: {entry['post']}
Sleep hours: {entry['sleep']}
Activity level: {entry['activity']}
Medication taken: {entry['medication']}

Give short, practical, daily-life advice for TODAY.
No diagnosis. No medical claims.
"""

    ai_text = safe_ai(prompt)
    if ai_text:
        return ai_text

    # -------- FALLBACK LOGIC --------
    tips = []

    if entry["fasting"] > 180:
        tips.append("Sugar is high today. Keep meals light and avoid late-night eating.")
    if entry["fasting"] < 70:
        tips.append("Sugar is low today. Be cautious and monitor closely.")
    if entry["sleep"] < 6:
        tips.append("Sleep was low. Try resting more today.")
    if entry["activity"] == "low":
        tips.append("Add a short 10–15 minute walk after meals.")
    if entry["medication"] == "no":
        tips.append("Please do not skip your medication today.")
    if entry["sleep"] >= 7 and entry["activity"] != "low":
        tips.append("Good job maintaining sleep and activity today.")

    return " ".join(tips) if tips else "Maintain your routine today."

# --------------------------------------------------
# PDF
# --------------------------------------------------
def generate_pdf(username, history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Diabetic Daily Report - {username}", ln=True)
    pdf.ln(4)

    for d in history[-7:]:
        pdf.cell(
            0, 8,
            f"{d['date']} | F:{d['fasting']} P:{d['post']} Sleep:{d['sleep']}h",
            ln=True
        )

    filename = f"{username}_diabetes_report.pdf"
    pdf.output(filename)
    return filename

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
if not st.session_state.user:
    st.title("🔐 Login")
    name = st.text_input("Enter your name")
    if st.button("Login") and name.strip():
        st.session_state.user = name.lower()
        st.rerun()
    st.stop()

username = st.session_state.user
st.title("📱 Diabetic Daily Support Agent")
st.caption(f"Logged in as **{username}**")

# --------------------------------------------------
# INPUT
# --------------------------------------------------
age = st.number_input("Age", 10, 100, 40)
fasting = st.number_input("Fasting Sugar", 60, 300, 110)
post = st.number_input("Post-meal Sugar", 80, 350, 160)
sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Physical Activity", ["low", "medium", "high"])
medication = st.selectbox("Medication Taken Today?", ["yes", "no"])

# --------------------------------------------------
# SUBMIT
# --------------------------------------------------
if st.button("Submit Daily Log"):
    entry = {
        "date": str(date.today()),
        "age": age,
        "fasting": fasting,
        "post": post,
        "sleep": sleep,
        "activity": activity,
        "medication": medication
    }

    history = load_history(username)
    history.append(entry)
    save_history(username, history)

    pattern = detect_pattern(history)
    conf = confidence(entry)
    today_focus = ai_today_focus(username, age, entry)

    st.session_state.result = (pattern, conf, today_focus)

# --------------------------------------------------
# OUTPUT
# --------------------------------------------------
if st.session_state.result:
    pattern, conf, today_focus = st.session_state.result

    st.success(f"Current Pattern: {pattern.title()}")
    st.metric("Daily Stability Confidence", f"{conf}%")

    st.warning("### Today’s Focus")
    st.write(today_focus)

    pdf = generate_pdf(username, load_history(username))
    with open(pdf, "rb") as f:
        st.download_button("Download My PDF Report", f, file_name=pdf)

    st.caption("This tool does not provide medical advice.")

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()
