#!/usr/bin/env python3
"""Fetch daily contribution counts into data/contributions.json.

Reads GH_TOKEN (or GITHUB_TOKEN) from the environment. In the cards workflow
that is the repository's GITHUB_TOKEN, which can read public contributions for
any user through GraphQL.

The output is intentionally timestamp-free and sorted, so an unchanged day
produces byte-identical JSON and the workflow commits nothing.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = "JAMIEL-J"
OUT = ROOT / "data" / "contributions.json"
DAYS = 370  # a little over a year, so the graph never has a ragged left edge

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
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


def main() -> None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GH_TOKEN or GITHUB_TOKEN must be set")

    now = dt.datetime.now(dt.timezone.utc)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": USER,
                "from": (now - dt.timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "jamiel-j-profile-cards",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)

    if "errors" in body:
        sys.exit("GraphQL errors: " + json.dumps(body["errors"]))

    calendar = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days: dict[str, dict] = {}
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days[day["date"]] = {"date": day["date"], "count": day["contributionCount"]}

    today = dt.date.today().isoformat()
    ordered = [days[key] for key in sorted(days) if key <= today]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"days": ordered}, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({len(ordered)} days, {sum(d['count'] for d in ordered)} contributions)")


if __name__ == "__main__":
    main()
