# Daily Security News Bot — Architecture

A daily security news agent built with Google ADK that fetches, filters, and summarizes security articles from Cloudflare Blog, AWS Security Blog, and The Hacker News.

---

## What is an Agent? (Core Idea)

An agent is nothing more than **a way for an LLM to know which function to call based on what the user says**.

It has three parts:

| Part | What it is | Example |
|------|-----------|---------|
| **System prompt** | Tells the LLM its role and how to behave | "You are a daily security news assistant..." |
| **Tool definitions** | Python functions with docstrings the LLM can read | `get_cloudflare_security_news()` |
| **ReAct loop** | The LLM decides → calls a function → reads result → repeats until ready to answer | See flow below |

**The LLM never executes code.** It only outputs `"I want to call this function with these arguments"`. The ADK Runner is what actually runs the Python function and feeds the result back to the LLM.

```
You (prompt)
  → LLM reads your message + sees available function definitions
  → LLM decides: "I need get_cloudflare_security_news()"
  → ADK Runner executes the Python function
  → LLM reads the result
  → LLM decides if it needs more data (calls another tool) or answers
  → Final answer delivered to you
```

> **Why docstrings matter:** The LLM reads the function's docstring — not the code — to decide whether to call it. A clear docstring = the LLM picks the right tool. A vague docstring = the LLM may skip it or misuse it.

---

## System Overview

```
User Prompt
    │
    ▼
Playground UI (Browser)
    │  HTTP POST /run
    ▼
FastAPI Server  (fast_api_app.py)
    │
    ▼
ADK App + Runner  (app/agent.py)
    │  Builds full prompt context
    ▼
Gemini on Vertex AI  (gemini-flash-latest)
    │  ReAct reasoning loop
    ├──► Tool: get_cloudflare_security_news() ──► Cloudflare Blog RSS
    ├──► Tool: get_aws_security_news()         ──► AWS Security Blog RSS
    └──► Tool: get_hacker_news_security_news() ──► The Hacker News RSS
    │
    │  Final response (structured digest)
    ▼
User sees security news
```

---

## Step-by-Step Request Flow

### Step 1 — User Prompt
The user types a message in the Playground UI running on `localhost:8000`.

```
"Give me today's security news"
```

---

### Step 2 — Playground → FastAPI Server
The browser sends an HTTP POST to the FastAPI server (`fast_api_app.py`, served by uvicorn).

```
POST /run
{
  "session_id": "<uuid>",
  "user_id":    "<user>",
  "message":    "Give me today's security news"
}
```

---

### Step 3 — FastAPI → ADK App
FastAPI hands the message to the ADK `App` object, which:
- Loads the current session state from the in-memory session store
- Attaches conversation history (all prior turns)
- Wraps everything in an ADK event and passes it to the Runner

---

### Step 4 — ADK Runner Builds the Full Context
The Runner assembles the complete prompt that will be sent to Gemini:

```
┌──────────────────────────────────────────────────────────────┐
│ SYSTEM INSTRUCTION                                           │
│   "You are a daily security news assistant. Call all three  │
│    tools, then present a clean organized digest..."         │
│                                                              │
│ TOOL DEFINITIONS  (auto-generated from Python docstrings)   │
│   • get_cloudflare_security_news()                          │
│   • get_aws_security_news()                                 │
│   • get_hacker_news_security_news()                         │
│                                                              │
│ CONVERSATION HISTORY  (from session)                        │
│                                                              │
│ USER MESSAGE                                                 │
│   "Give me today's security news"                           │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 5 — Gemini Receives the Context (Vertex AI)

The ADK Runner sends the full context to **Gemini Flash** on **Google Cloud Vertex AI**, authenticated using **Application Default Credentials (ADC)** tied to project `covergo-ai-ocr-dev`.

---

### Step 6 — Gemini Reasons (ReAct Loop)

Gemini uses a **ReAct** (Reason + Act) loop — it does not answer immediately. Instead it reasons about what it needs to do:

```
Thought:  "I need news from 3 sources. I'll call all 3 tools."
Action:   call get_cloudflare_security_news
Observation: <tool result>

Thought:  "Good. Now AWS."
Action:   call get_aws_security_news
Observation: <tool result>

Thought:  "Now The Hacker News."
Action:   call get_hacker_news_security_news
Observation: <tool result>

Thought:  "I have everything. I'll write the digest."
Answer:   <final response>
```

Gemini never calls the internet directly — it requests tool calls, and the ADK Runner executes them locally.

---

### Steps 7–12 — Tool Execution (Local Python Functions)

For each tool call Gemini requests, the ADK Runner calls the corresponding Python function in `app/agent.py`. Each function:

1. Makes an HTTP GET to the RSS feed URL
2. Parses the XML with `feedparser`
3. Applies a security keyword filter (Cloudflare only — AWS and THN feeds are already security-specific)
4. Returns a formatted text string back to Gemini

#### RSS Sources

| Tool | RSS Feed URL | Security Filter |
|------|-------------|-----------------|
| `get_cloudflare_security_news` | `https://blog.cloudflare.com/rss/` | Yes — keyword filtered |
| `get_aws_security_news` | `https://aws.amazon.com/blogs/security/feed/` | No — feed is already security-only |
| `get_hacker_news_security_news` | `https://feeds.feedburner.com/TheHackersNews` | No — feed is already security-only |

#### Security Keywords (applied to Cloudflare)

```
security, vulnerability, exploit, breach, hack, malware, ransomware,
phishing, zero-day, cve, patch, threat, attack, encryption,
authentication, firewall, ddos, data leak, privacy, compliance,
audit, incident, cyber, intrusion, botnet, credential, privilege,
injection, xss, csrf, secret
```

---

### Step 13 — Gemini Generates the Final Response

With all three tool results in context, Gemini writes a structured security digest:

- Articles grouped by source
- Title, published date, URL, and summary for each article
- Critical CVEs and zero-days highlighted prominently
- Concise, professional tone

If Vertex AI returns a transient error, ADK automatically retries up to **3 times** (`retry_options=HttpRetryOptions(attempts=3)`).

---

### Steps 14–15 — Response Delivery

```
Vertex AI
    │  Final text
    ▼
ADK Runner  →  saves turn to in-memory session store
    ▼
FastAPI  →  HTTP response
    ▼
Browser  →  renders in Playground UI
    ▼
User reads the security news digest
```

---

## Component Reference

| Component | File | Purpose |
|-----------|------|---------|
| Agent & tools | `app/agent.py` | Core logic — tools, agent definition, ADK App |
| FastAPI server | `app/fast_api_app.py` | HTTP API layer, serves the playground |
| Playground UI | `agents-cli playground` | Browser-based chat interface for local testing |
| Session store | In-memory (ADK default) | Holds conversation history per session |
| Auth | ADC → `covergo-ai-ocr-dev` | Signs every Vertex AI request |

---

## Infrastructure

```
Local Machine
├── agents-cli playground  (dev UI)
├── FastAPI + uvicorn      (app server)
├── ADK Runner             (orchestration)
└── Python tools           (RSS fetching)

Google Cloud (covergo-ai-ocr-dev)
└── Vertex AI — Gemini Flash  (LLM)

External (internet)
├── blog.cloudflare.com       (RSS)
├── aws.amazon.com/blogs      (RSS)
└── feedburner.com/TheHackersNews  (RSS)
```

---

## Data Flow Summary

```
User
 │ prompt
 ▼
FastAPI ──► ADK Runner ──► Vertex AI / Gemini
                │               │
                │    tool call  │
                ◄───────────────┘
                │
                ├──► Cloudflare RSS  (HTTP + feedparser)
                ├──► AWS RSS         (HTTP + feedparser)
                └──► THN RSS         (HTTP + feedparser)
                │
                │    tool results
                ──────────────────► Vertex AI / Gemini
                                        │
                                        │ final digest
                                        ▼
                                      User
```
