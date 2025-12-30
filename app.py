import streamlit as st
import json
from datetime import datetime
from statistics import mean
from transformers import pipeline
from fpdf import FPDF

# -----------------------------------
# Configuration
# -----------------------------------

DATA_FILE = "diabetes_history.json"

# -----------------------------------
# Memory Handling
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
# Entry Creation
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
    avg_fasting = mean(d["fasting"] for d in recent)
    avg_post = mean(d["post_meal"] for d in recent)
    avg_sleep = mean(d["sleep"] for d in recent)

    if avg_fasting > 180 or avg_post > 250:
        return "very high readings"
    elif avg_fasting < 70:
        return "very low readings"
    elif avg_fasting < 120 and avg_sleep >= 7:
        return "stable routine"
    else:
        return "mixed pattern"

def previous_pattern(history):
    if len(history) < 4:
        return None
    return detect_pattern(history[:-1])

# -----------------------------------
# Confidence Scoring (0–100)
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
# Daily Focus & Alerts
# -----------------------------------

def daily_focus(entry):
    focus = []

    if entry["sleep"] < 6:
        focus.append("Try to sleep earlier tonight and aim for 7 hours.")

    if entry["activity"] == "low":
        focus.append("Consider a 10–15 minute walk after meals.")

    if entry["medication"] == "no":
        focus.append("Set a reminder to take medication consistently.")

    if entry["fasting"] > 180 or entry["fasting"] < 70:
        focus.append("Sugar levels are concerning today. Please consult a doctor.")

    if entry["sleep"] >= 7 and entry["activity"] != "low":
        focus.append("Great job maintaining sleep and activity today 👏")

    return focus

# -----------------------------------
# Weekly Trend
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
# Stronger AI Model
# -----------------------------------

explainer = pipeline(
    "text-generation",
    model="microsoft/phi-2",
    device=-1
)


def ai_explanation(name, age, current, previous):
    prompt = (
        f"{name}, age {age}, daily health summary:\n"
        f"Earlier pattern: {previous}\n"
        f"Current pattern: {current}\n"
        f"Summary:"
    )

    result = explainer(
        prompt,
        max_new_tokens=120,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
        repetition_penalty=1.1
    )

    text = result[0]["generated_text"]

    # Remove prompt if echoed
    if "Summary:" in text:
        text = text.split("Summary:")[-1].strip()

    return text


# -----------------------------------
# Agent Orchestrator
# -----------------------------------

def diabetes_agent(entry):
    history = load_history()
    history.append(entry)

    current = detect_pattern(history)
    previous = previous_pattern(history)
    confidence = confidence_score(entry)
    focus = daily_focus(entry)
    weekly = weekly_trend(history)
    explanation = ai_explanation(entry["name"], entry["age"], current, previous)

    save_history(history)

    return current, explanation, confidence, focus, weekly

# -----------------------------------
# PDF Generator
# -----------------------------------

def generate_pdf(history):
    user = history[-1]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Diabetic Support Report for {user['name']} (Age {user['age']})", ln=True)

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
st.caption("Awareness • Habit guidance • Non-diagnostic")

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
    entry = create_entry(name, age, date, fasting, post_meal, sleep, activity, mood, medication)

    pattern, explanation, confidence, focus, weekly = diabetes_agent(entry)

    st.success(f"Current Pattern: {pattern.title()}")
    st.metric("Daily Stability Confidence", f"{confidence}%")
    st.write(explanation)

    if focus:
        st.warning("### Tomorrow’s Focus")
        for f in focus:
            st.write(f"- {f}")

    if weekly:
        st.info("### Weekly Trend")
        st.write(weekly)

    history = load_history()
    pdf_file = generate_pdf(history)

    with open(pdf_file, "rb") as f:
        st.download_button("Download PDF Report", f, file_name=pdf_file)

    st.caption(
        "This tool does not replace professional medical advice. "
        "Consult a healthcare provider for clinical decisions."
    )
