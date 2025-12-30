import streamlit as st
import json
from datetime import datetime
from statistics import mean
from transformers import pipeline
from fpdf import FPDF

# -----------------------------------
# Memory Handling
# -----------------------------------

DATA_FILE = "diabetes_history.json"

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
# Entry Creation
# -----------------------------------

def create_entry(date, fasting, post_meal, sleep, activity, mood, medication):
    return {
        "date": date,
        "fasting": fasting,
        "post_meal": post_meal,
        "sleep": sleep,
        "activity": activity,
        "mood": mood,
        "medication": medication
    }

# -----------------------------------
# Pattern Detection (Python Logic)
# -----------------------------------

def detect_pattern(history):
    if len(history) < 3:
        return "insufficient data"

    recent = history[-3:]
    avg_fasting = mean(d["fasting"] for d in recent)
    avg_post = mean(d["post_meal"] for d in recent)
    avg_sleep = mean(d["sleep"] for d in recent)

    if avg_fasting > 140 or avg_post > 200:
        return "elevated readings"
    elif avg_fasting < 120 and avg_sleep >= 7:
        return "stable routine"
    else:
        return "mixed pattern"

def previous_pattern(history):
    if len(history) < 4:
        return None
    return detect_pattern(history[:-1])

# -----------------------------------
# Daily Alert Generator (Python)
# -----------------------------------

def daily_alerts(entry):
    alerts = []

    if entry["sleep"] < 6:
        alerts.append("Try to sleep at least 7 hours tonight.")

    if entry["activity"] == "low":
        alerts.append("Light walking or movement may help tomorrow.")

    if entry["medication"] == "no":
        alerts.append("Medication was missed today. Set a reminder.")

    if entry["fasting"] > 150:
        alerts.append("Morning sugar was high. Consistency may help.")

    return alerts

# -----------------------------------
# Weekly Trend Analysis
# -----------------------------------

def weekly_trend(history):
    if len(history) < 7:
        return None

    last_week = history[-7:]
    return {
        "avg_fasting": round(mean(d["fasting"] for d in last_week), 1),
        "avg_post": round(mean(d["post_meal"] for d in last_week), 1),
        "avg_sleep": round(mean(d["sleep"] for d in last_week), 1)
    }

# -----------------------------------
# AI Explanation (FIXED)
# -----------------------------------

explainer = pipeline("text-generation", model="google/flan-t5-small")

def ai_explanation(current, previous):
    prompt = (
        f"Explain for a diabetic person in simple daily-life language. "
        f"Earlier pattern: {previous}. Current pattern: {current}. "
        f"Focus on habits like sleep, activity, routine. No medical advice."
    )

    result = explainer(
        prompt,
        max_length=120,
        do_sample=True,
        temperature=0.7
    )

    return result[0]["generated_text"]

# -----------------------------------
# Agent Orchestrator
# -----------------------------------

def diabetes_agent(entry):
    history = load_history()
    history.append(entry)

    current = detect_pattern(history)
    previous = previous_pattern(history)
    alerts = daily_alerts(entry)
    weekly = weekly_trend(history)
    explanation = ai_explanation(current, previous)

    save_history(history)

    return current, explanation, alerts, weekly

# -----------------------------------
# PDF Report Generator
# -----------------------------------

def generate_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Diabetic Daily Summary Report", ln=True)

    for d in history[-7:]:
        pdf.cell(
            0, 8,
            f"{d['date']} | Fasting: {d['fasting']} | Post: {d['post_meal']} | Sleep: {d['sleep']}h",
            ln=True
        )

    file_name = "diabetes_report.pdf"
    pdf.output(file_name)
    return file_name

# -----------------------------------
# Streamlit UI
# -----------------------------------

st.set_page_config(page_title="Diabetic Support Agent", layout="centered")

st.title("📱 Diabetic Daily Support Agent")
st.caption("Non-diagnostic • Habit awareness • AI-assisted insights")

date = st.text_input("Date (YYYY-MM-DD)", value=str(datetime.today().date()))
fasting = st.number_input("Fasting Sugar", 60, 300, 110)
post_meal = st.number_input("Post-Meal Sugar", 80, 350, 160)
sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Physical Activity", ["low", "medium", "high"])
mood = st.selectbox("Mood", ["good", "okay", "low"])
medication = st.selectbox("Medication Taken Today?", ["yes", "no"])

if st.button("Submit Daily Log"):
    entry = create_entry(date, fasting, post_meal, sleep, activity, mood, medication)
    pattern, explanation, alerts, weekly = diabetes_agent(entry)

    st.success(f"Current Pattern: {pattern.title()}")
    st.write(explanation)

    if alerts:
        st.warning("### Daily Focus")
        for a in alerts:
            st.write(f"- {a}")

    if weekly:
        st.info("### Weekly Trend")
        st.write(weekly)

    history = load_history()
    pdf_file = generate_pdf(history)

    with open(pdf_file, "rb") as f:
        st.download_button(
            "Download Weekly PDF Report",
            f,
            file_name=pdf_file,
            mime="application/pdf"
        )

    st.caption(
        "This tool does not provide medical advice. "
        "Consult a healthcare professional for clinical decisions."
    )
