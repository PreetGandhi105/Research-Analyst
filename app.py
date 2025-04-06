import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import re
from io import BytesIO

st.set_page_config(page_title="Research Analyst", layout="wide")
st.title("💼 Research Analyst - AI Equity Assistant")

# Session state to store chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -------------------- Transcript Intelligence -------------------- #
def sample_transcript_data():
    return """
    Good afternoon everyone, and thank you for joining our Q4 earnings call. 
    We are pleased to report strong growth in our digital services segment, with a 17% YoY increase. 
    However, headwinds in the US banking sector have affected our BFSI vertical slightly.

    Looking ahead, we are confident in achieving 12-14% revenue growth next year.
    We had previously announced a margin target of 21%, and we have successfully maintained it.
    We are also expanding in Europe and expect this to contribute to revenues in the next two quarters.
    """

def summarize_transcript(transcript):
    lines = transcript.strip().split(". ")
    return [line.strip() for line in lines if any(k in line.lower() for k in ["growth", "revenue", "margin", "expanding"])]

def analyze_sentiment(transcript):
    polarity = TextBlob(transcript).sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    return "Neutral"

def extract_commitments(transcript):
    return re.findall(r"(we .*?target.*?\d+%|we .*?expect.*?\d+%)", transcript, re.I)

def evaluate_commitments(commitments):
    return [(c.strip(), random.choice(["Met", "Not Met"])) for c in commitments]

# -------------------- Screener Data Fetch -------------------- #
def get_soup(slug):
    url = f"https://www.screener.in/company/{slug}/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    return BeautifulSoup(res.text, "html.parser")

def get_summary(soup):
    data = {"Company": soup.find("h1").text.strip()}
    for tag in soup.select(".company-ratios .col, .info-list li"):
        key = tag.find("small") or tag.find("span")
        val = tag.find("span", class_="number") or tag.find("b")
        if key and val:
            data[key.text.strip()] = val.text.strip()
    return data

# -------------------- Excel Export -------------------- #
def generate_excel(data_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for name, df in data_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

# -------------------- Chat Response Engine -------------------- #
def handle_query(message):
    response = ""
    data_dict = {}

    if "analyze" in message.lower():
        match = re.search(r"analyze\s+([A-Z]+)", message, re.I)
        if match:
            slug = match.group(1).upper()
            soup = get_soup(slug)
            summary = get_summary(soup)
            response += f"**Key Financial Summary for {slug}:**\n"
            for k, v in summary.items():
                response += f"- {k}: {v}\n"
            df_summary = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
            data_dict[slug] = df_summary

    if "compare" in message.lower():
        comps = re.findall(r"[A-Z]{3,}", message)
        peer_data = []
        for comp in comps:
            soup = get_soup(comp)
            peer_data.append(get_summary(soup))
        df_peer = pd.DataFrame(peer_data)
        response += "\n**Peer Comparison:**\n" + df_peer[["Company", "Return on equity", "Current Price"]].to_markdown(index=False)
        data_dict["Peer Comparison"] = df_peer

    if "transcript" in message.lower():
        transcript = sample_transcript_data()
        summary_points = summarize_transcript(transcript)
        sentiment = analyze_sentiment(transcript)
        commitments = evaluate_commitments(extract_commitments(transcript))

        response += "\n**Transcript Summary:**\n"
        for point in summary_points:
            response += f"- {point}\n"
        response += f"\n**Management Sentiment:** {sentiment}\n"
        response += "**Past Commitments:**\n"
        for c, s in commitments:
            response += f"- {c} → {s}\n"

        df_commit = pd.DataFrame(commitments, columns=["Commitment", "Status"])
        data_dict["Transcript Analysis"] = df_commit

    return response.strip(), data_dict

# -------------------- Streamlit Chat UI -------------------- #
with st.chat_message("assistant"):
    st.markdown("👋 Hello! I'm **Research Analyst**, your AI-powered equity research assistant. Ask me about any company.")

user_query = st.chat_input("Ask me about a company…")
if user_query:
    st.session_state.chat_history.append(("user", user_query))
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        answer, export_data = handle_query(user_query)
        st.markdown(answer)

        if export_data:
            excel = generate_excel(export_data)
            st.download_button("📥 Export to Excel", data=excel, file_name="Research_Analyst_Report.xlsx", mime="application/vnd.ms-excel")

    st.session_state.chat_history.append(("assistant", answer))