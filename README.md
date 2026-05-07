# sre-news-agent

An AI-powered SRE news assistant that aggregates the latest articles across security, cloud platforms, observability, incident management, and the broader SRE community — all in one daily digest.

Built with [Google ADK](https://adk.dev/) and deployed on Google Cloud Run.

## News Sources

The agent pulls from **12 RSS feeds** across 5 categories:

### Security
| Source | What it covers |
|--------|---------------|
| [Cloudflare Blog](https://blog.cloudflare.com) | Network security, DDoS, threat intelligence |
| [AWS Security Blog](https://aws.amazon.com/blogs/security/) | AWS-specific security announcements and best practices |
| [The Hacker News](https://thehackernews.com) | CVEs, breaches, zero-days, malware |

### Cloud Platforms
| Source | What it covers |
|--------|---------------|
| [Google Cloud Blog](https://cloud.google.com/blog) | GCP product updates and releases |
| [Azure Updates](https://azure.microsoft.com/en-us/updates/) | Azure service announcements |
| [AWS What's New](https://aws.amazon.com/new/) | New AWS features and services |

### Observability
| Source | What it covers |
|--------|---------------|
| [Grafana Blog](https://grafana.com/blog/) | Grafana, Loki, Tempo, Mimir updates |
| [OpenTelemetry Blog](https://opentelemetry.io/blog/) | OTel specs, SDKs, and community news |

### Incident Management
| Source | What it covers |
|--------|---------------|
| [PagerDuty Blog](https://www.pagerduty.com/blog/) | On-call, incident response practices |
| [Last9 Blog](https://last9.io/blog/) | Reliability engineering, SLOs |
| [Squadcast Blog](https://www.squadcast.com/blog/) | Incident management, runbooks |

### SRE Community
| Source | What it covers |
|--------|---------------|
| [CNCF Blog](https://www.cncf.io/blog/) | Kubernetes, Prometheus, cloud-native ecosystem |
| [InfoQ DevOps](https://www.infoq.com/devops/) | Platform engineering, DevOps practices |
| [SRE Weekly](https://sreweekly.com) | Curated SRE articles and postmortems |
| [Reddit r/sre](https://www.reddit.com/r/sre/) | Community discussions and links |

---

## Project Structure

```
sre-news-agent/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── fast_api_app.py        # FastAPI Backend server
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Cloud Run                                                                   |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
