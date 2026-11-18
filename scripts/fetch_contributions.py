#!/usr/bin/env python3
"""Fetch the last 12 months of GitHub contribution data via the GraphQL API
and normalize it into data/contributions.json.

Requires a GITHUB_TOKEN (or GH_TOKEN) environment variable with at least
public read access. Run with no arguments:

    GITHUB_TOKEN=... python scripts/fetch_contributions.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_PATH = os.path.join(ROOT, "data", "profile.json")
OUTPUT_PATH = os.path.join(ROOT, "data", "contributions.json")

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def load_username() -> str:
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return json.load(f)["github_username"]


def fetch(login: str, token: str) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=365)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": login,
                "from": since.strftime("%Y-%m-%dT00:00:00Z"),
                "to": now.strftime("%Y-%m-%dT23:59:59Z"),
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "errors" in body:
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def normalize(calendar: dict) -> dict:
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({"date": day["date"], "count": day["contributionCount"]})
    days.sort(key=lambda d: d["date"])

    total = calendar["totalContributions"]

    # Streaks
    current_streak = 0
    longest_streak = 0
    running = 0
    today = dt.date.today().isoformat()
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0
    # current streak counted backward from the most recent day with data
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    active_days = sum(1 for d in days if d["count"] > 0)
    busiest = max(days, key=lambda d: d["count"]) if days else None

    monthly: dict[str, int] = {}
    for d in days:
        month_key = d["date"][:7]
        monthly[month_key] = monthly.get(month_key, 0) + d["count"]

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": active_days,
        "busiest_day": busiest,
        "monthly": monthly,
        "days": days,
    }


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN (or GH_TOKEN) is required.", file=sys.stderr)
        return 1

    login = load_username()
    try:
        calendar = fetch(login, token)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch contributions: {exc}", file=sys.stderr)
        return 1

    normalized = normalize(calendar)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
        f.write("\n")

    print(f"Wrote {OUTPUT_PATH} ({normalized['total_contributions']} contributions).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
