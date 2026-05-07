# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
import feedparser
import requests
from datetime import datetime, timezone, timedelta

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

SECURITY_KEYWORDS = [
    "security", "vulnerability", "exploit", "breach", "hack", "malware",
    "ransomware", "phishing", "zero-day", "cve", "patch", "threat", "attack",
    "encryption", "authentication", "firewall", "ddos", "data leak", "privacy",
    "compliance", "audit", "incident", "cyber", "intrusion", "botnet",
    "credential", "privilege", "injection", "xss", "csrf", "secret",
]

def _is_security_related(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in SECURITY_KEYWORDS)

def _fetch_feed(url: str, source_name: str, security_filter: bool = True) -> list[dict]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        feed = feedparser.parse(response.content)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        results = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            published = entry.get("published", "")
            if security_filter and not _is_security_related(title, summary):
                continue
            results.append({
                "source": source_name,
                "title": title,
                "link": link,
                "published": published,
                "summary": summary[:300] if summary else "",
            })
        return results
    except Exception as e:
        return [{"source": source_name, "error": str(e)}]

def _format_articles(articles: list[dict]) -> str:
    if not articles:
        return "No security-related articles found."
    lines = []
    for a in articles:
        if "error" in a:
            lines.append(f"[{a['source']}] Error fetching feed: {a['error']}")
            continue
        lines.append(f"[{a['source']}] {a['title']}")
        if a.get("published"):
            lines.append(f"  Published: {a['published']}")
        lines.append(f"  URL: {a['link']}")
        if a.get("summary"):
            lines.append(f"  Summary: {a['summary']}")
        lines.append("")
    return "\n".join(lines)


def get_cloudflare_security_news() -> str:
    """Fetches the latest security-related articles from the Cloudflare blog RSS feed.

    Returns:
        A formatted string of recent security articles from Cloudflare blog.
    """
    articles = _fetch_feed(
        "https://blog.cloudflare.com/rss/",
        "Cloudflare Blog",
        security_filter=True,
    )
    return _format_articles(articles)


def get_aws_security_news() -> str:
    """Fetches the latest security articles from the AWS Security Blog RSS feed.

    Returns:
        A formatted string of recent security articles from AWS Security Blog.
    """
    articles = _fetch_feed(
        "https://aws.amazon.com/blogs/security/feed/",
        "AWS Security Blog",
        security_filter=False,  # AWS Security Blog is already security-focused
    )
    return _format_articles(articles)


def get_hacker_news_security_news() -> str:
    """Fetches the latest security news from The Hacker News RSS feed.

    Returns:
        A formatted string of recent security articles from The Hacker News.
    """
    articles = _fetch_feed(
        "https://feeds.feedburner.com/TheHackersNews",
        "The Hacker News",
        security_filter=False,  # The Hacker News is already security-focused
    )
    return _format_articles(articles)


root_agent = Agent(
    name="daily_security_news_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a daily security news assistant. When asked for news, call all three tools "
        "(get_cloudflare_security_news, get_aws_security_news, get_hacker_news_security_news) "
        "to gather articles, then present a clean, organized digest. "
        "Group articles by source. For each article include the title, published date, URL, and a brief summary. "
        "Highlight any critical vulnerabilities, zero-days, or major incidents prominently. "
        "Keep your tone concise and professional."
    ),
    tools=[get_cloudflare_security_news, get_aws_security_news, get_hacker_news_security_news],
)

app = App(
    root_agent=root_agent,
    name="app",
)
