#!/usr/bin/env python3
# Download GitHub's uptime history from githubstatus.com -> historical-data.json
#
# Before 2020-02 the status page recorded outage time inconsistently, so the
# uptime pages count many incidents as zero minutes. This also reads the
# incident history and works out durations from each incident's own timestamps:
#
# - Incidents from 2016 to 2018-12-06 were imported into Statuspage on
#   2018-12-05 with zero duration and no component status changes. Each one's
#   real timeline survives only as a bulleted list in its single update, and
#   most of them name the components they affected.
# - From 2018-12 to 2020-01, most incidents were attached only to a hidden
#   placeholder component ("Visit www.githubstatus.com for more information"),
#   so they name no component shown on the uptime page.
#
# Incidents that name no component on the uptime page were classified by hand
# from their updates; incident-components.json lists the components for each,
# counting those that name no service as web and API, and the ones that weren't
# outages. Incidents about notifications only are left as recorded, which is how
# GitHub has filed such incidents since 2020.
#
# For each component and day before 2020-02, the time of the incidents naming
# that component is counted as "m" (major/critical) or "p" (minor/none)
# seconds and compared with the outage time Statuspage recorded. Where the
# incidents' time is longer, it replaces the recorded time, the month's
# uptime_percentage is recomputed with Statuspage's formula, and the day gets a
# "reconstructed" entry holding the originally recorded seconds and the
# incidents used.
#
# Responses are cached in .cache/ and never expire. Pages are numbered back
# from the current month, so delete .cache/ before re-running in a new month.

import calendar
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

BASE_URL = "https://www.githubstatus.com"
DATA_PATH = "historical-data.json"
CLASSIFICATION_PATH = "incident-components.json"
CACHE_DIR = ".cache"
UTC = dt.timezone.utc

# Statuspage counts partial outages at 30% of a major outage
PARTIAL_WEIGHT = 0.3
# The site's data has always started here
FLOOR = "2016-04"
# From this month on, component outages were recorded consistently
TRACKING_START = "2020-02"
# Before these months the status page reports a placeholder 100% for these
# components, so their earlier months are left out: Actions and Packages became
# generally available in 2019-11, and pull request problems were recorded on
# Issues until the Pull Requests component was added
COMPONENT_START = {"Actions": "2019-11", "Packages": "2019-11", "Pull Requests": "2020-09"}

TS_FULL = re.compile(r"<strong>(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})</strong>")
TS_TIME = re.compile(r"<strong>(\d{2}:\d{2})</strong>")  # some imports give times only


def fetch(path, cache=True):
    cache_path = os.path.join(CACHE_DIR, re.sub(r"[^A-Za-z0-9_.-]", "_", path.strip("/")) + ".json")

    if cache and os.path.exists(cache_path):
        with open(cache_path) as fin:
            return json.load(fin)

    url = BASE_URL + path
    headers = {"Accept": "application/json", "User-Agent": "github-historical-uptime"}
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After") or 15 * (attempt + 1))
            print(f"\tRate limited, waiting {wait}s")
            time.sleep(wait)
    else:
        raise RuntimeError(f"Gave up on {url} after repeated rate limiting")

    time.sleep(0.5)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "wb") as fout:
        fout.write(body)

    return json.loads(body)


def year_month(month):
    """A page's month as "YYYY-MM", which sorts in date order."""
    return f"{month['year']}-{list(calendar.month_name).index(month['name']):02d}"


def fetch_uptime():
    """Every uptime page for every component on the uptime page, back to its start."""
    first = fetch("/uptime?page=1", cache=False)
    pages = []

    for choice in first["component_select_list"]:
        print(f"Uptime: {choice['name']}")
        start = max(FLOOR, COMPONENT_START.get(choice["name"], FLOOR))
        page_num = 1

        while True:
            # Page 1 holds the latest three months, so always refresh it
            page = fetch(f"/uptime/{choice['value']}?page={page_num}", cache=page_num > 1)
            # Statuspage has no uptime for months before a component's start_date
            # (Codespaces, Copilot), so those are left out too
            page["months"] = [m for m in page["months"]
                              if year_month(m) >= start and m["uptime_percentage"] is not None]

            if not page["months"]:
                break

            pages.append(page)
            page_num += 1

    return pages


def fetch_incidents():
    """Details of every incident that started between FLOOR and TRACKING_START."""
    codes = []
    page_num = 1

    while True:
        # History pages hold three months each, newest first
        history = fetch(f"/history.json?page={page_num}", cache=page_num > 1)

        for month in history["months"]:
            if FLOOR <= year_month(month) < TRACKING_START:
                codes += [i["code"] for i in month["incidents"]]

        if history["start_time"][:7] <= FLOOR:
            break

        page_num += 1

    print(f"Fetching {len(codes)} incidents")
    return [fetch(f"/incidents/{code}.json") for code in codes]


def incident_span(incident):
    """(start, end) of an incident, or None if it has no duration.

    Normally this is started_at to resolved_at. Imported incidents have those
    two set to the same moment, and instead have one update whose text is the
    original timeline as a list of timestamped lines; for them, the first to
    the last of those timestamps is the duration. Taking the longer of the two
    handles both kinds without having to tell them apart.
    """
    spans = [(dt.datetime.fromisoformat(incident["started_at"]),
              dt.datetime.fromisoformat(incident["resolved_at"]))]

    for update in incident["incident_updates"]:
        body = update["body"]
        stamps = [dt.datetime.fromisoformat(t).replace(tzinfo=UTC) for t in TS_FULL.findall(body)]

        if not stamps:
            day = incident["started_at"][:10]
            stamps = [dt.datetime.fromisoformat(f"{day} {t}:00").replace(tzinfo=UTC)
                      for t in TS_TIME.findall(body)]

        if len(stamps) > 1:
            spans.append((min(stamps), max(stamps)))

    span = max(spans, key=lambda s: s[1] - s[0])
    return span if span[1] > span[0] else None


def split_days(start, end):
    """Yield (YYYY-MM-DD, seconds) for an interval split at midnight UTC."""
    cur = start

    while cur < end:
        next_midnight = dt.datetime(cur.year, cur.month, cur.day, tzinfo=UTC) + dt.timedelta(days=1)
        stop = min(end, next_midnight)
        yield cur.strftime("%Y-%m-%d"), (stop - cur).total_seconds()
        cur = stop


def weighted(p, m):
    return m + PARTIAL_WEIGHT * p


def reconstruct(pages, incidents):
    components = {page["component"]["id"] for page in pages}
    days = {}  # (component id, YYYY-MM-DD) -> that day's record

    for page in pages:
        for month in page["months"]:
            for day in month["days"]:
                if "date" in day:
                    days[(page["component"]["id"], day["date"][:10])] = day

    from_incidents = defaultdict(lambda: {"p": 0.0, "m": 0.0, "incidents": []})

    for incident in incidents:
        span = incident_span(incident)

        if incident["impact"] == "maintenance" or span is None:
            continue

        key = "m" if incident["impact"] in ("major", "critical") else "p"
        # Incidents naming no component on the uptime page (including those only on
        # the hidden placeholder) can't be attributed, so they are left as recorded
        comp_ids = [c["id"] for c in incident["components"] if c["id"] in components]

        for date, secs in split_days(*span):
            for comp_id in comp_ids:
                entry = from_incidents[(comp_id, date)]
                entry[key] += secs
                entry["incidents"].append(incident["id"])

    changed_months = set()

    for (comp_id, date), entry in from_incidents.items():
        # A day can't hold more than 24 hours of outage
        m = min(round(entry["m"]), 86400)
        p = min(round(entry["p"]), 86400 - m)

        day = days.get((comp_id, date))

        # Keep whichever of the recorded time and the incidents' time is longer
        if day is None or weighted(p, m) <= weighted(day["p"], day["m"]):
            continue

        day["reconstructed"] = {
            "recorded": {"p": day["p"], "m": day["m"]},
            "incidents": entry["incidents"],
        }
        day["p"], day["m"] = p, m
        changed_months.add((comp_id, date[:7]))

    for page in pages:
        comp_id = page["component"]["id"]

        for month in page["months"]:
            if (comp_id, year_month(month)) not in changed_months:
                continue

            secs = len(month["days"]) * 86400
            down = sum(weighted(d["p"], d["m"]) for d in month["days"])
            month["uptime_percentage"] = 1 - down / secs

    return len(changed_months)


def classify(pages, incidents):
    """Apply the hand-assigned components and exclusions in CLASSIFICATION_PATH."""
    with open(CLASSIFICATION_PATH) as fin:
        classification = json.load(fin)

    ids = {page["component"]["name"]: page["component"]["id"] for page in pages}
    classified = []

    for incident in incidents:
        if incident["id"] in classification["not_outages"]:
            continue

        if incident["id"] in classification["components"]:
            names = classification["components"][incident["id"]]["components"]
            incident["components"] += [{"id": ids[name]} for name in names]

        classified.append(incident)

    return classified


def main():
    pages = fetch_uptime()
    incidents = classify(pages, fetch_incidents())
    n_months = reconstruct(pages, incidents)
    print(f"Used incident durations in {n_months} component-months")

    with open(DATA_PATH, "w") as fout:
        json.dump(pages, fout)
        print(f"Data saved to {DATA_PATH}")


if __name__ == "__main__":
    main()
