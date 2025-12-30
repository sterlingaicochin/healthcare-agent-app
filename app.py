import streamlit as st
import json
import os
from datetime import datetime
from statistics import mean
from fpdf import FPDF
import google.generativeai as genai

# -----------------------------------
# GEMINI CONFIG
# -----------------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
gemini = genai.GenerativeModel("gemini-1.5-flash")

# -----------------------------------
# SESSION STATE
# -----------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "result" not in st.session_state:
    st.session_state.result = None

# -----------------------------------
# FILE UTILS
# -----------------------------------
def user_file(username):
    os.makedirs("data", exist_ok=True)
    return f"data/{username}_history.json"

def load_history(username):
    try:
        with open(user_file(username), "r") as f:
            return json.load(f)
    except:
        return []

def save_history(username, data):
    with open(user_file(username), "w") as f:
        json.dump(data, f, indent=2)

# -----------------------------------
# ENTRY
# -----------------------------------
def create_entry(username, age, date, fasting, post_meal, sleep, activity, mood, medication):
    return {
        "user": username,
        "age": age,
        "date": date,
        "fasting": fasting,
        "post_meal": post_meal,
        "sleep": sleep,
        "activity": activity,
        "mood": mood,
        "medication": medication
    }

# -----------------------------------
# PATTERN (RULE BASED – SAFE)
# -----------------------------------
def detect_pattern(history):
    if len(history) < 3:
        return "insufficient data"

    recent = history[-3:]
    avg_f = mean(d["fasting"] for d in recent)
    avg_p = mean(d["post_meal"] for d in recent)
    avg_s = mean(d["sleep"] for d in recent)

    if avg_f > 180 or avg_p > 250:
        return "very high readings"
    elif avg_f < 70:
        return "very low readings"
    elif avg_f < 120 and avg_s >= 7:
        return "stable routine"
    else:
        return "mixed pattern"

# -----------------------------------
# CONFIDENCE SCORE
# -----------------------------------
def confidence_score(entry):
    score = 100
    if entry["fasting"] > 160 or entry["fasting"] < 70:
        score -= 30
    if entry["sleep"] < 6:
        score -= 15
    if entry["activity"] == "low":
        score -= 15
    if entry["medication"] == "no":
        score -= 20
    return max(score, 0)

# -----------------------------------
# AI FOCUS (REAL MODEL CALL)
# -----------------------------------
def ai_focus_generator(username, age, entry, today=True):
    day = "today" if today else "tomorrow"

    prompt = f"""
User name: {username}
Age: {age}

Health data:
- Fasting sugar: {entry["fasting"]}
- Post-meal sugar: {entry["post_meal"]}
- Sleep hours: {entry["sleep"]}
- Physical activity: {entry["activity"]}
- Medication taken: {entry["medication"]}

Task:
Explain {day}'s focus in simple daily-life language.

Rules:
- Base explanation ONLY on the values above
- If sugar is very high or very low, mention concern
- For today: explain what this data suggests
- For tomorrow: suggest specific actionable habits
- No medical diagnosis
- Suggest doctor consultation if concerning
"""

    try:
        response = gemini.generate_content(prompt)
        return response.text.strip()
    except Exception:
        if today:
            return f"{username}, today showed imbalance. Observe your routine calmly."
        else:
            return f"{username}, tomorrow try better sleep and light activity."

# -----------------------------------
# AGENT
# -----------------------------------
def diabetes_agent(username, entry):
    history = load_history(username)
    history.append(entry)

    pattern = detect_pattern(history)
    confidence = confidence_score(entry)

    today_focus = ai_focus_generator(username, entry["age"], entry, today=True)
    tomorrow_focus = ai_focus_generator(username, entry["age"], entry, today=False)

    save_history(username, history)

    return pattern, confidence, today_focus, tomorrow_focus

# -----------------------------------
# PDF
# -----------------------------------
def generate_pdf(username, history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    title = f"Diabetic Support Report - {username.title()}"
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(5)

    for d in history[-7:]:
        line = f"{d['date']} | Fasting {d['fasting']} | Post {d['post_meal']} | Sleep {d['sleep']}h"
        pdf.cell(0, 8, line, ln=True)

    file = f"{username}_diabetes_report.pdf"
    pdf.output(file)
    return file

# -----------------------------------
# UI
# -----------------------------------
st.set_page_config("Diabetic Support Agent", layout="centered")

# ---------- LOGIN ----------
if not st.session_state.user:
    st.title("🔐 Login")
    username = st.text_input("Enter your name")

    if st.button("Login"):
        if username.strip():
            st.session_state.user = username.strip().lower()
            st.rerun()
        else:
            st.error("Please enter a valid name.")
    st.stop()

# ---------- MAIN APP ----------
username = st.session_state.user
st.title("📱 Diabetic Daily Support Agent")
st.caption(f"Logged in as **{username}**")

age = st.number_input("Age", 10, 100, 40)
date = st.text_input("Date", value=str(datetime.today().date()))
fasting = st.number_input("Fasting Sugar", 60, 300, 110)
post_meal = st.number_input("Post-Meal Sugar", 80, 350, 160)
sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Physical Activity", ["low", "medium", "high"])
mood = st.selectbox("Mood", ["good", "okay", "low"])
medication = st.selectbox("Medication Taken Today?", ["yes", "no"])

if st.button("Submit Daily Log"):
    entry = create_entry(username, age, date, fasting, post_meal, sleep, activity, mood, medication)
    st.session_state.result = diabetes_agent(username, entry)

# ---------- OUTPUT ----------
if st.session_state.result:
    pattern, confidence, today_focus, tomorrow_focus = st.session_state.result

    st.success(f"Current Pattern: {pattern.title()}")
    st.metric("Daily Stability Confidence", f"{confidence}%")

    st.warning("### Today’s Focus")
    st.write(today_focus)

    st.info("### Tomorrow’s Focus")
    st.write(tomorrow_focus)

    history = load_history(username)
    pdf = generate_pdf(username, history)
    with open(pdf, "rb") as f:
        st.download_button("Download My PDF Report", f, file_name=pdf)

    st.caption(
        "This tool does not provide medical advice. "
        "Consult a healthcare professional for clinical decisions."
    )

if st.button("Logout"):
    st.session_state.user = None
    st.session_state.result = None
    st.rerun()
