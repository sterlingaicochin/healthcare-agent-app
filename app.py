import streamlit as st
import json
import os
from datetime import datetime
from statistics import mean
from fpdf import FPDF
import google.generativeai as genai

# -----------------------------
# GEMINI CONFIG
# -----------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.9,
        "top_p": 0.9,
        "max_output_tokens": 200
    }
)

# -----------------------------
# SESSION
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "result" not in st.session_state:
    st.session_state.result = None

# -----------------------------
# STORAGE
# -----------------------------
def user_file(username):
    os.makedirs("data", exist_ok=True)
    return f"data/{username}.json"

def load_history(username):
    try:
        with open(user_file(username), "r") as f:
            return json.load(f)
    except:
        return []

def save_history(username, history):
    with open(user_file(username), "w") as f:
        json.dump(history, f, indent=2)

# -----------------------------
# ENTRY
# -----------------------------
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

# -----------------------------
# PATTERN
# -----------------------------
def detect_pattern(history):
    if len(history) < 3:
        return "insufficient data"
    recent = history[-3:]
    af = mean(d["fasting"] for d in recent)
    ap = mean(d["post_meal"] for d in recent)
    if af > 180 or ap > 250:
        return "very high readings"
    if af < 70:
        return "very low readings"
    return "mixed pattern"

# -----------------------------
# CONFIDENCE
# -----------------------------
def confidence_score(e):
    score = 100
    if e["fasting"] > 160 or e["fasting"] < 70: score -= 30
    if e["sleep"] < 6: score -= 20
    if e["activity"] == "low": score -= 15
    if e["medication"] == "no": score -= 20
    return max(score, 0)

# -----------------------------
# AI FOCUS (FORCED VARIATION)
# -----------------------------
def ai_focus(username, age, entry, mode):
    prompt = f"""
You are a health-support AI.

USER DATA:
Age: {age}
Fasting sugar: {entry["fasting"]}
Post-meal sugar: {entry["post_meal"]}
Sleep hours: {entry["sleep"]}
Activity level: {entry["activity"]}
Medication taken: {entry["medication"]}

STEP 1 — CLASSIFY SEVERITY:
- Sugar HIGH if fasting > 140 or post-meal > 200
- Sugar LOW if fasting < 70
- Sleep LOW if < 6 hours
- Activity LOW if activity = low

STEP 2 — MODE = {mode}

IF MODE = TODAY:
- Explain what today’s numbers indicate
- Mention which values are concerning and why
- Tone: calm, observational

IF MODE = TOMORROW:
- Give 3 specific actions based on the data
- Mention sleep timing, walking, reminders
- Tone: encouraging and actionable

RULES:
- Use different wording for TODAY and TOMORROW
- Do NOT give generic advice
- If sugar is HIGH or LOW → suggest doctor consultation
- Keep language simple, human, daily-life
"""

    return model.generate_content(prompt).text.strip()

# -----------------------------
# AGENT
# -----------------------------
def diabetes_agent(username, entry):
    history = load_history(username)
    history.append(entry)
    save_history(username, history)

    pattern = detect_pattern(history)
    confidence = confidence_score(entry)

    today = ai_focus(username, entry["age"], entry, "TODAY")
    tomorrow = ai_focus(username, entry["age"], entry, "TOMORROW")

    return pattern, confidence, today, tomorrow

# -----------------------------
# PDF
# -----------------------------
def generate_pdf(username, history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Diabetes Report - {username}", ln=True)
    pdf.ln(5)
    for d in history[-7:]:
        pdf.cell(0, 8, f'{d["date"]} | F:{d["fasting"]} | P:{d["post_meal"]} | S:{d["sleep"]}', ln=True)
    file = f"{username}_report.pdf"
    pdf.output(file)
    return file

# -----------------------------
# UI
# -----------------------------
st.set_page_config("Diabetic Support Agent")

if not st.session_state.user:
    st.title("Login")
    u = st.text_input("Your name")
    if st.button("Login") and u:
        st.session_state.user = u.lower()
        st.rerun()
    st.stop()

st.title("Diabetic Daily Support Agent")
st.caption(f"Logged in as {st.session_state.user}")

age = st.number_input("Age", 10, 100, 40)
date = st.text_input("Date", value=str(datetime.today().date()))
fasting = st.number_input("Fasting Sugar", 60, 300, 110)
post = st.number_input("Post-Meal Sugar", 80, 350, 160)
sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Activity", ["low", "medium", "high"])
mood = st.selectbox("Mood", ["good", "okay", "low"])
med = st.selectbox("Medication Taken?", ["yes", "no"])

if st.button("Submit Daily Log"):
    entry = create_entry(st.session_state.user, age, date, fasting, post, sleep, activity, mood, med)
    st.session_state.result = diabetes_agent(st.session_state.user, entry)

if st.session_state.result:
    p, c, tdy, tmr = st.session_state.result
    st.success(f"Pattern: {p}")
    st.metric("Confidence", f"{c}%")
    st.warning("### Today’s Focus")
    st.write(tdy)
    st.info("### Tomorrow’s Focus")
    st.write(tmr)

    pdf = generate_pdf(st.session_state.user, load_history(st.session_state.user))
    with open(pdf, "rb") as f:
        st.download_button("Download PDF", f, file_name=pdf)

if st.button("Logout"):
    st.session_state.user = None
    st.session_state.result = None
    st.rerun()
