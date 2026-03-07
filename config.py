import re
import os, os.path
from datetime import datetime

INPUT_GLOB = "input/*.har"
DATA_PATH = "historical-data.json"

OUT_DIR = "out/"
OUT_PLOT_AVG = os.path.join(OUT_DIR, "historical-uptime.png")
OUT_PLOT_BY_COMP = os.path.join(OUT_DIR, "historical-uptime-by-component.png")
OUT_PLOT_INDIVIDUAL_COMP = os.path.join(OUT_DIR, "historical-uptime-component-%s.png")

REQUIRE_FULL_MONTH = True
PATH_FILTER_EXP = re.compile("^/uptime.*$")
RELEVANT_COMPONENTS = [
    "API Requests",
    "Actions",
    #"Codespaces", # Was not available at the beginning of historical data
    #"Copilot", # Was not available at the beginning of historical data
    "Git Operations",
    "Issues",
    "Packages",
    "Pages",
    "Pull Requests",
    "Webhooks",
]

MICROSOFT_ACQUISITION_DT = datetime.strptime("October 26, 2018", "%B %d, %Y")
