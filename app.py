import streamlit as st
import json
from datetime import datetime
from statistics import mean
from fpdf import FPDF

# -----------------------------------
# Session State
# -----------------------------------
if "result" not in st.session_state:
    st.session_state.result = None

# -----------------------------------
# Configuration
# -----------------------------------
DATA_FILE = "diabetes_history.json"

# -----------------------------------
# Storage
# -----------------------------------
def load_history():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# -----------------------------------
# Entry
# -----------------------------------
def create_entry(name, age, date, fasting, post_meal, sleep, activity, mood, medication):
    return {
        "name": name,
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
# Pattern Detection
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
# Confidence
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
# Daily Focus
# -----------------------------------
def daily_focus(entry):
    tips = []

    if entry["sleep"] < 6:
        tips.append("Try to sleep earlier tonight and aim for at least 7 hours.")

    if entry["activity"] == "low":
        tips.append("Add a 10–15 minute walk after meals.")

    if entry["medication"] == "no":
        tips.append("Set a reminder to take medication consistently.")

    if entry["fasting"] > 180 or entry["fasting"] < 70:
        tips.append("Sugar levels are concerning today. Please consult a doctor.")

    if entry["sleep"] >= 7 and entry["activity"] != "low":
        tips.append("Great job maintaining good sleep and activity 👏")

    return tips

# -----------------------------------
# Weekly Trend
# -----------------------------------
def weekly_trend(history):
    if len(history) < 7:
        return None

    last = history[-7:]
    return {
        "Average Fasting": round(mean(d["fasting"] for d in last), 1),
        "Average Post-Meal": round(mean(d["post_meal"] for d in last), 1),
        "Average Sleep (hrs)": round(mean(d["sleep"] for d in last), 1)
    }

# -----------------------------------
# Explanation (Fast & Safe)
# -----------------------------------
def explain_pattern(name, age, current, previous):
    msg = f"{name}, based on recent entries:\n\n"

    if previous and previous != current:
        msg += f"Earlier pattern was '{previous}'. Now it is '{current}'.\n\n"

    if current == "very high readings":
        msg += "Sugar levels are frequently high. Focus on sleep, regular meals, and activity."
    elif current == "very low readings":
        msg += "Sugar levels are running low. Monitor carefully and seek medical guidance."
    elif current == "stable routine":
        msg += "Your routine looks stable. Keep maintaining sleep, activity, and consistency."
    else:
        msg += "Your readings vary day to day. Improving routine consistency may help."

    msg += f"\n\n(Age considered: {age})"
    return msg

# -----------------------------------
# Agent
# -----------------------------------
def diabetes_agent(entry):
    history = load_history()
    history.append(entry)

    current = detect_pattern(history)
    previous = previous_pattern(history)
    confidence = confidence_score(entry)
    focus = daily_focus(entry)
    weekly = weekly_trend(history)
    explanation = explain_pattern(entry["name"], entry["age"], current, previous)

    save_history(history)
    return current, explanation, confidence, focus, weekly

# -----------------------------------
# PDF
# -----------------------------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

def generate_pdf(history):
    user = history[-1]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    title = f"Diabetic Support Report - {user['name']} (Age {user['age']})"
    pdf.cell(0, 10, clean_text(title), ln=True)
    pdf.ln(5)

    for d in history[-7:]:
        line = (
            f"{d['date']} | "
            f"Fasting: {d['fasting']} | "
            f"Post: {d['post_meal']} | "
            f"Sleep: {d['sleep']}h"
        )
        pdf.cell(0, 8, clean_text(line), ln=True)

    file_name = "diabetes_report.pdf"
    pdf.output(file_name)
    return file_name


# -----------------------------------
# UI
# -----------------------------------
st.set_page_config("Diabetic Support Agent", layout="centered")
st.title("📱 Diabetic Daily Support Agent")
st.caption("Pattern awareness • Habit guidance • Non-diagnostic")

name = st.text_input("Your Name")
age = st.number_input("Age", 10, 100, 40)
date = st.text_input("Date", value=str(datetime.today().date()))
fasting = st.number_input("Fasting Sugar", 60, 300, 110)
post_meal = st.number_input("Post-Meal Sugar", 80, 350, 160)
sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Physical Activity", ["low", "medium", "high"])
mood = st.selectbox("Mood", ["good", "okay", "low"])
medication = st.selectbox("Medication Taken Today?", ["yes", "no"])

if st.button("Submit Daily Log"):
    if not name.strip():
        st.error("Please enter your name.")
        st.stop()

    entry = create_entry(name, age, date, fasting, post_meal, sleep, activity, mood, medication)
    st.session_state.result = diabetes_agent(entry)

# -----------------------------------
# Output
# -----------------------------------
if st.session_state.result:
    pattern, explanation, confidence, focus, weekly = st.session_state.result

    st.success(f"Current Pattern: {pattern.title()}")
    st.metric("Daily Stability Confidence", f"{confidence}%")
    st.write(explanation)

    if focus:
        st.warning("### Tomorrow’s Focus")
        for f in focus:
            st.write(f"- {f}")

    if weekly:
        st.info("### Weekly Trend")
        st.json(weekly)

    history = load_history()
    pdf = generate_pdf(history)
    with open(pdf, "rb") as f:
        st.download_button("Download PDF Report", f, file_name=pdf)

    st.caption(
        "This tool does not provide medical advice. "
        "Consult a healthcare professional for clinical decisions."
    )
