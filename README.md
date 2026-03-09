# AI Customer Support Agent 🇮🇳

I've spent years being everyone's go-to person for customer support —
my uncle's Flipkart returns, a neighbor's Swiggy refund, a stranger at
a billing counter who just needed help getting her money back.

The process was always the same: too long, too English, too exhausting.

So I built this.

---

## What It Does

This is an AI-powered customer support agent that lets you speak naturally —
in Hindi, Tamil, Telugu, Kannada, or English — and handles your returns,
refunds, and order tracking end to end.

No navigating through 7 screens. No typing in perfect English.
No waiting on hold.

And if the platform is at fault? It knows. And it acts on it.

---

## Demo

> User asks to return an order. Return window has expired — agent says no.
> User switches to Hindi and points out the delivery arrived 2 days late.
> Agent checks the dates, confirms the platform's fault, overrides its own
> decision, and approves the return.

No escalation. No "please contact support." Just the right outcome.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Speech to Text | Sarvam Saarika v2.5 |
| Text to Speech | Sarvam Bulbul v2 |
| LLM | GPT-4o |
| Agent Framework | LangGraph |
| Backend | FastAPI |
| Frontend | React |

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- API keys for OpenAI and Sarvam AI

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # add your API keys here
uvicorn main:app --reload
```

# Frontend

```bash
cd frontend
npm install
npm start
```

# Why I Built This

500 million Indians shop online. Most of them can't get their money back
without asking someone for help — a family member, a neighbor, or a
stranger at a billing counter.

That's not a UX problem. That's an infrastructure problem.
This is my attempt at fixing it.

