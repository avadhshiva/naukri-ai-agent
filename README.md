# 🤖 AI Job Application Automation Agent

An autonomous AI-powered system that automates end-to-end job applications by combining browser automation with LLM-driven decision-making.

---

## 🚀 What This System Does

- Automatically discovers and applies to jobs on Naukri
- Parses job descriptions in real time
- Answers screening questions using LLM reasoning
- Handles multi-step forms and recruiter chatbot interactions
- Tracks applications and success metrics via dashboard

---

## 📊 Visual Dashboard
A beautiful Next.js-powered dashboard to visualize your application history, success rates, and job details.
![Dashboard Screenshot](./dashboard.png)

---

## 🧠 System Architecture

User Input / Resume  
→ Job Scraper (Playwright)  
→ LLM Decision Engine (Groq - Llama-3-70B)  
→ Form Automation Engine  
→ Chatbot Handler (multi-turn interaction)  
→ Session Manager (state persistence)  
→ Metrics Dashboard (Next.js)

---

## 🤖 LLM Design

- **Model**: Llama-3-70B via Groq
- **Temperature**: 0 (deterministic outputs)
- **Prompt Strategy**:
  - Role-based prompting (candidate persona)
  - Context injection (resume + job description)
  - Structured precision outputs for automation
- **Use Cases**:
  - Answering screening questions
  - Mapping skills to job requirements
  - Handling recruiter chat flows

---

## ⚙️ Key Features

- 🔄 **End-to-end Automation**: Complete job application flow (90% time reduction)
- 💬 **Dynamic Chatbot Handler**: Real-time recruiter conversation management
- 🧠 **Context-Aware Reasoning**: Intelligent answer generation using LLMs
- 🛡️ **Stealth Operations**: Anti-bot evasion & session persistence (99% success rate)
- 📊 **Real-time Analytics**: Dashboard for tracking outcomes and performance

---

## 🚀 Getting Started

1. **Setup**: `pip install -r requirements.txt`
2. **Configure**: Copy `.env.example` to `.env` and add your credentials.
3. **Run**: `python agent/main.py naukri`

---

## ⚠️ Challenges Solved

- Handling dynamic DOM changes across job forms
- Maintaining session state across long workflows
- Ensuring deterministic LLM responses for automation
- Managing multi-turn recruiter interactions

---

## 🛠 Tech Stack

- **Automation**: Python, Playwright
- **AI**: Groq (Llama-3-70B)
- **Frontend**: Next.js (Dashboard)
- **Data**: REST APIs & JSON Snapshots

---

## 🎯 Why This Project Matters

This project demonstrates how LLMs can be integrated into real-world automation systems to replace repetitive human workflows with intelligent, adaptive agents.
