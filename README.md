# github-uptime-graph
Generates graphs based on historical GitHub uptime data.

## Setup

### Gathering Data
Run `./scrape-data.py` from the repository root. Requires Python 3.11+.

It downloads [GitHub's Uptime History](https://www.githubstatus.com/uptime) for every component back to April 2016 and writes `historical-data.json`. Responses are cached in `.cache/`, and the cache is never cleared automatically. githubstatus.com numbers its pages back from the current month, so once the month changes the cached pages no longer line up and months go missing from the output. Delete `.cache/` before re-running in a new month. The first run takes a while because githubstatus.com rate limits requests.

Before February 2020, the status page recorded many incidents as zero minutes of outage, so the script also uses the incident history to correct uptime for that period. The comment at the top of `scrape-data.py` explains how.

## Running the Website
Requires NodeJS and NPM (or an alternative).

```sh
# TL;DR
cd webapp/
npm install
npm run dev
```

More details: See [webapp/README.md](webapp/README.md)
