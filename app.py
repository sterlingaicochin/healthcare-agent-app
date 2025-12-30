import streamlit as st
import json
from transformers import pipeline
def load_history():
    try:
        with open("health_history.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open("health_history.json", "w") as f:
        json.dump(data, f, indent=2)
def detect_pattern(history):
    if len(history) < 3:
        return "Not enough data yet"

    recent = history[-3:]
    avg_sleep = sum(d["sleep_hours"] for d in recent) / 3
    avg_energy = sum(d["energy_level"] for d in recent) / 3

    if avg_sleep < 6 and avg_energy < 3:
        return "declining routine"
    return "stable routine"
explainer = pipeline(
    "text-generation",
    model="google/flan-t5-small"
)
def explain_pattern(pattern):
    prompt = f"Explain in simple, non-medical terms why {pattern} matters for daily wellbeing."
    result = explainer(prompt, max_length=60)
    return result[0]["generated_text"]
def health_agent(entry):
    history = load_history()
    history.append(entry)

    pattern = detect_pattern(history)
    explanation = explain_pattern(pattern)

    save_history(history)

    return pattern, explanation
st.set_page_config(page_title="Health Pattern Monitor", layout="centered")

st.title("📱 Personal Health Pattern Monitor")
st.caption("Non-diagnostic • Privacy-safe • Human-reviewed")

date = st.text_input("Date (YYYY-MM-DD)")
sleep = st.slider("Sleep Hours", 0, 10, 7)
energy = st.slider("Energy Level (1–5)", 1, 5, 3)
pain = st.slider("Pain Level (1–5)", 1, 5, 2)
mood = st.selectbox("Mood", ["good", "okay", "low"])

if st.button("Submit Daily Entry"):
    entry = {
        "date": date,
        "sleep_hours": sleep,
        "energy_level": energy,
        "pain_level": pain,
        "mood": mood
    }

    pattern, explanation = health_agent(entry)

    st.success(f"Pattern Detected: {pattern.title()}")
    st.write(explanation)
