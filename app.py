import streamlit as st
import json
from transformers import pipeline

# -------------------------------
# Agent Memory (Persistence)
# -------------------------------

def load_history():
    try:
        with open("diabetes_history.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open("diabetes_history.json", "w") as f:
        json.dump(data, f, indent=2)

# -------------------------------
# Create Daily Entry
# -------------------------------

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

# -------------------------------
# Pattern Detection (Python Brain)
# -------------------------------

def detect_diabetes_pattern(history):
    if len(history) < 3:
        return "insufficient data"

    recent = history[-3:]

    avg_fasting = sum(d["fasting"] for d in recent) / 3
    avg_post = sum(d["post_meal"] for d in recent) / 3
    avg_sleep = sum(d["sleep"] for d in recent) / 3

    if avg_fasting > 140 or avg_post > 200:
        return "elevated readings"
    elif avg_fasting < 120 and avg_sleep >= 7:
        return "stable routine"
    else:
        return "mixed pattern"

def get_previous_pattern(history):
    if len(history) < 4:
        return None
    return detect_diabetes_pattern(history[:-1])

# -------------------------------
# AI Explanation Tool
# -------------------------------

explainer = pipeline(
    "text-generation",
    model="google/flan-t5-small"
)

def explain_diabetes_pattern(current, previous):
    if previous:
        prompt = (
            f"Previously the pattern was '{previous}'. "
            f"Now the pattern is '{current}'. "
            "Explain in simple, non-medical language what changed, "
            "what habits earlier supported stability, "
            "and what daily lifestyle focus may help."
        )
    else:
        prompt = (
            f"The current pattern is '{current}'. "
            "Explain in simple, non-medical language what this means "
            "and what daily habits usually support stability."
        )

    result = explainer(prompt, max_length=130)
    return result[0]["generated_text"]

# -------------------------------
# Agent Orchestrator (PHASE 3)
# -------------------------------

def diabetes_agent(entry):
    history = load_history()
    history.append(entry)

    current_pattern = detect_diabetes_pattern(history)
    previous_pattern = get_previous_pattern(history)

    explanation = explain_diabetes_pattern(current_pattern, previous_pattern)

    save_history(history)

    return current_pattern, explanation

# -------------------------------
# Streamlit Mobile-Friendly UI
# -------------------------------

st.set_page_config(page_title="Diabetic Support Agent", layout="centered")

st.title("📱 Diabetic Daily Support Agent")
st.caption("Non-diagnostic • Awareness support only • Human-reviewed")

date = st.text_input("Date (YYYY-MM-DD)")

fasting = st.number_input("Fasting Blood Sugar", min_value=60, max_value=300, value=110)
post_meal = st.number_input("Post-Meal Blood Sugar", min_value=80, max_value=350, value=160)

sleep = st.slider("Sleep Hours", 0, 10, 7)
activity = st.selectbox("Physical Activity Level", ["low", "medium", "high"])
mood = st.selectbox("Mood", ["good", "okay", "low"])
medication = st.selectbox("Medication Taken Today?", ["yes", "no"])

if st.button("Submit Daily Log"):
    entry = create_entry(
        date,
        fasting,
        post_meal,
        sleep,
        activity,
        mood,
        medication
    )

    pattern, explanation = diabetes_agent(entry)

    st.success(f"Current Pattern: {pattern.title()}")
    st.write(explanation)

    st.info(
        "This tool does not provide medical advice. "
        "Please consult a healthcare professional for clinical decisions."
    )
