# github-uptime-graph
Generates a graph based on historical GitHub uptime data.

## Usage
1. Open your web browser
2. Clear your cache
3. In your web browser, open the network inspector and manually click through each option on each page of the network graph (I figured this would be quicker than automating it)
4. Export all as HAR
5. Add HAR file(s) to input (may be multiple if you had to do this in multiple sessions to escape rate limits)
6. Run `anonymize-data.py`
7. Delete your HAR files for privacy
8. Verify and chart with `chart.py`
