import streamlit as st
import json
import os
from datetime import datetime
from statistics import mean
from fpdf import FPDF
import google.generativeai as genai

# -----------------------------------
# CONFIGURE GEMINI
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
# UTILITIES
# -----------------------------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

def user_file(username):
    os.makedirs("data", exist_ok=True)
    return f"data/{username}_history.json"

# -----------------------------------
# STORAGE
# -----------------------------------
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
# PATTERN DETECTION (RULE-BASED)
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

def previous_pattern(history):
    if len(history) < 4:
        return None
    return detect_pattern(history[:-1])

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
# RAW FOCUS SIGNALS (RULES)
# -----------------------------------
def daily_focus_signals(entry):
    signals = []

    if entry["sleep"] < 6:
        signals.append("Low sleep")

    if entry["activity"] == "low":
        signals.append("Low physical activity")

    if entry["medication"] == "no":
        signals.append("Missed medication")

    if entry["fasting"] > 180 or entry["fasting"] < 70:
        signals.append("Critical sugar level")

    if entry["sleep"] >= 7 and entry["activity"] != "low":
        signals.append("Good routine")

    return signals

# -----------------------------------
# AI MODEL CALL (THIS IS THE REAL AI)
# -----------------------------------
def ai_focus_generator(username, age, signals, today=True):
    if not signals:
        return f"Great job {username}! Your routine looks balanced."

    if today:
        task = """
Explain what happened today in simple daily-life language.
Focus on awareness, reflection, and calm reassurance.
Do NOT repeat advice for tomorrow.
"""
    else:
        task = """
Give a clear, actionable focus plan for tomorrow.
Mention specific actions like sleep timing, walking, routine, or reminders.
Encourage gently.
"""

    prompt = f"""
User name: {username}
Age: {age}

Health signals detected:
{", ".join(signals)}

{task}

Rules:
- No medical diagnosis
- If sugar is very high or very low, suggest consulting a doctor
- Keep tone friendly and human
"""

    try:
        response = gemini.generate_content(prompt)
        return response.text.strip()
    except Exception:
        if today:
            return f"{username}, today showed some imbalance. Take it easy and observe patterns."
        else:
            return f"{username}, tomorrow try improving sleep and light activity."


# -----------------------------------
# AGENT
# -----------------------------------
def diabetes_agent(username, entry):
    history = load_history(username)
    history.append(entry)

    current = detect_pattern(history)
    previous = previous_pattern(history)
    confidence = confidence_score(entry)
    signals = daily_focus_signals(entry)

    today_focus = ai_focus_generator(username, entry["age"], signals, today=True)
    tomorrow_focus = ai_focus_generator(username, entry["age"], signals, today=False)

    save_history(username, history)

    return current, confidence, today_focus, tomorrow_focus

# -----------------------------------
# PDF
# -----------------------------------
def generate_pdf(username, history):
    user = history[-1]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    title = f"Diabetic Support Report - {username} (Age {user['age']})"
    pdf.cell(0, 10, clean_text(title), ln=True)
    pdf.ln(5)

    for d in history[-7:]:
        line = f"{d['date']} | Fasting {d['fasting']} | Post {d['post_meal']} | Sleep {d['sleep']}h"
        pdf.cell(0, 8, clean_text(line), ln=True)

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
st.caption(f"Logged in as: **{username}**")

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
