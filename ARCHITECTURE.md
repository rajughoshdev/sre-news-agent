# SRE News Agent — Architecture

An AI-powered SRE news assistant built with Google ADK that aggregates, filters, and summarizes articles from 15 RSS feeds across security, cloud platforms, observability, incident management, and the SRE community.

---

## What is an Agent? (Core Idea)

An agent is nothing more than **a way for an LLM to know which function to call based on what the user says**.

It has three parts:

| Part | What it is | Example |
|------|-----------|---------|
| **System prompt** | Tells the LLM its role and how to behave | "You are an SRE news assistant..." |
| **Tool definitions** | Python functions with docstrings the LLM can read | `get_observability_news()` |
| **ReAct loop** | The LLM decides → calls a function → reads result → repeats until ready to answer | See flow below |

**The LLM never executes code.** It only outputs `"I want to call this function with these arguments"`. The ADK Runner is what actually runs the Python function and feeds the result back to the LLM.

```
You (prompt)
  → LLM reads your message + sees available function definitions
  → LLM decides which tools to call based on the request
  → ADK Runner executes the Python functions
  → LLM reads the results
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
    │
    ├──► Tool: get_cloudflare_security_news()   ──► Cloudflare Blog RSS
    ├──► Tool: get_aws_security_news()           ──► AWS Security Blog RSS
    ├──► Tool: get_hacker_news_security_news()   ──► The Hacker News RSS
    │
    ├──► Tool: get_cloud_platform_news()         ──► GCP Blog RSS
    │                                            ──► Azure Updates RSS
    │                                            ──► AWS What's New RSS
    │
    ├──► Tool: get_observability_news()          ──► Grafana Blog RSS
    │                                            ──► OpenTelemetry Blog RSS
    │
    ├──► Tool: get_incident_management_news()    ──► PagerDuty Blog RSS
    │                                            ──► Last9 Blog RSS
    │                                            ──► Squadcast Blog RSS
    │
    └──► Tool: get_sre_community_news()          ──► CNCF Blog RSS
                                                 ──► InfoQ DevOps RSS
                                                 ──► SRE Weekly RSS
                                                 ──► Reddit r/sre RSS
    │
    │  Final response (structured digest by category)
    ▼
User sees SRE news digest
```

---

## Step-by-Step Request Flow

### Step 1 — User Prompt
The user types a message in the Playground UI running on `localhost:8000`.

```
"Give me today's SRE news"
```

---

### Step 2 — Playground → FastAPI Server
The browser sends an HTTP POST to the FastAPI server (`fast_api_app.py`, served by uvicorn).

```
POST /run
{
  "session_id": "<uuid>",
  "user_id":    "<user>",
  "message":    "Give me today's SRE news"
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
┌──────────────────────────────────────────────────────────────────────┐
│ SYSTEM INSTRUCTION                                                   │
│   "You are an SRE news assistant. For a full digest, call all       │
│    tools and present results grouped by category..."                │
│                                                                      │
│ TOOL DEFINITIONS  (auto-generated from Python docstrings)           │
│   • get_cloudflare_security_news()                                  │
│   • get_aws_security_news()                                         │
│   • get_hacker_news_security_news()                                 │
│   • get_cloud_platform_news()                                       │
│   • get_observability_news()                                        │
│   • get_incident_management_news()                                  │
│   • get_sre_community_news()                                        │
│                                                                      │
│ CONVERSATION HISTORY  (from session)                                │
│                                                                      │
│ USER MESSAGE                                                         │
│   "Give me today's SRE news"                                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Step 5 — Gemini Receives the Context (Vertex AI)

The ADK Runner sends the full context to **Gemini Flash** on **Google Cloud Vertex AI**, authenticated using **Application Default Credentials (ADC)**.

---

### Step 6 — Gemini Reasons (ReAct Loop)

Gemini uses a **ReAct** (Reason + Act) loop — it does not answer immediately. Instead it reasons about what it needs to do:

```
Thought:  "I need news across all SRE categories. I'll call all 7 tools."

Action:   call get_cloudflare_security_news
Observation: <tool result>

Action:   call get_aws_security_news
Observation: <tool result>

Action:   call get_hacker_news_security_news
Observation: <tool result>

Action:   call get_cloud_platform_news
Observation: <tool result — GCP + Azure + AWS What's New>

Action:   call get_observability_news
Observation: <tool result — Grafana + OpenTelemetry>

Action:   call get_incident_management_news
Observation: <tool result — PagerDuty + Last9 + Squadcast>

Action:   call get_sre_community_news
Observation: <tool result — CNCF + InfoQ + SRE Weekly + Reddit r/sre>

Thought:  "I have everything. I'll write the digest grouped by category."
Answer:   <final response>
```

Gemini never calls the internet directly — it requests tool calls, and the ADK Runner executes them locally.

---

### Steps 7–12 — Tool Execution (Local Python Functions)

For each tool call Gemini requests, the ADK Runner calls the corresponding Python function in `app/agent.py`. Each function:

1. Makes an HTTP GET to the RSS feed URL(s)
2. Parses the XML with `feedparser`
3. Applies a security keyword filter where the feed is not already topic-specific
4. Returns a formatted text string back to Gemini

#### RSS Sources

**Security**

| Tool | RSS Feed | Filter |
|------|----------|--------|
| `get_cloudflare_security_news` | `blog.cloudflare.com/rss/` | Keyword filtered |
| `get_aws_security_news` | `aws.amazon.com/blogs/security/feed/` | None — security-only feed |
| `get_hacker_news_security_news` | `feedburner.com/TheHackersNews` | None — security-only feed |

**Cloud Platforms**

| Tool | RSS Feeds | Filter |
|------|-----------|--------|
| `get_cloud_platform_news` | GCP Blog, Azure Updates, AWS What's New | None |

**Observability**

| Tool | RSS Feeds | Filter |
|------|-----------|--------|
| `get_observability_news` | Grafana Blog, OpenTelemetry Blog | None |

**Incident Management**

| Tool | RSS Feeds | Filter |
|------|-----------|--------|
| `get_incident_management_news` | PagerDuty Blog, Last9 Blog, Squadcast Blog | None |

**SRE Community**

| Tool | RSS Feeds | Filter |
|------|-----------|--------|
| `get_sre_community_news` | CNCF Blog, InfoQ DevOps, SRE Weekly, Reddit r/sre | None |

#### Security Keywords (applied to Cloudflare feed only)

```
security, vulnerability, exploit, breach, hack, malware, ransomware,
phishing, zero-day, cve, patch, threat, attack, encryption,
authentication, firewall, ddos, data leak, privacy, compliance,
audit, incident, cyber, intrusion, botnet, credential, privilege,
injection, xss, csrf, secret
```

---

### Step 13 — Gemini Generates the Final Response

With all tool results in context, Gemini writes a structured digest grouped by category:

- **Security** — CVEs, breaches, zero-days highlighted prominently
- **Cloud Platforms** — GCP, Azure, AWS product updates
- **Observability** — Grafana, OpenTelemetry news
- **Incident Management** — On-call, runbooks, reliability practices
- **SRE Community** — Kubernetes, platform engineering, postmortems

Each article includes: title, published date, URL, and a brief summary.

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
User reads the SRE news digest
```

---

## Component Reference

| Component | File | Purpose |
|-----------|------|---------|
| Agent & tools | `app/agent.py` | Core logic — 7 tools, agent definition, ADK App |
| FastAPI server | `app/fast_api_app.py` | HTTP API layer, serves the playground |
| Playground UI | `agents-cli playground` | Browser-based chat interface for local testing |
| Session store | In-memory (ADK default) | Holds conversation history per session |
| Auth | ADC → Vertex AI | Signs every Vertex AI request |

---

## Infrastructure

```
Local Machine
├── agents-cli playground  (dev UI)
├── FastAPI + uvicorn      (app server)
├── ADK Runner             (orchestration)
└── Python tools           (RSS fetching)

Google Cloud
└── Vertex AI — Gemini Flash  (LLM)

External (internet) — 15 RSS feeds
├── Security:           Cloudflare, AWS Security Blog, The Hacker News
├── Cloud Platforms:    GCP Blog, Azure Updates, AWS What's New
├── Observability:      Grafana Blog, OpenTelemetry Blog
├── Incident Mgmt:      PagerDuty, Last9, Squadcast
└── SRE Community:      CNCF, InfoQ DevOps, SRE Weekly, Reddit r/sre
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
                ├──► Security feeds    (Cloudflare, AWS Sec, THN)
                ├──► Cloud feeds       (GCP, Azure, AWS What's New)
                ├──► Observability     (Grafana, OpenTelemetry)
                ├──► Incident Mgmt     (PagerDuty, Last9, Squadcast)
                └──► SRE Community     (CNCF, InfoQ, SRE Weekly, Reddit)
                │
                │    tool results (all categories)
                ──────────────────► Vertex AI / Gemini
                                        │
                                        │ final digest (5 categories)
                                        ▼
                                      User
```
