#!/usr/bin/env python3
# Validates data then generates charts based on it.

import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from typing import TypedDict, cast
from datetime import datetime

from config import (
    DATA_PATH, RELEVANT_COMPONENTS,
    OUT_DIR, OUT_PLOT_AVG, OUT_PLOT_BY_COMP, OUT_PLOT_INDIVIDUAL_COMP,
    MICROSOFT_ACQUISITION_DT,
)

type MonthlyData = dict[str, MonthlyEntry]

class MonthlyEntry(TypedDict):
    month: str
    year: int
    component_uptimes: dict[str, float]


def main():
    monthly_data = gather_data()
    plot(monthly_data)


def plot(monthly_data: MonthlyData):
    os.makedirs(OUT_DIR, exist_ok=True)

    # Average
    points_avg = list()

    for group_name, group in monthly_data.items():
        dt = datetime.strptime(group_name, "%Y:%B")
        comp_uptimes = group["component_uptimes"]
        uptime_sum = sum([comp_uptimes[comp_name] for comp_name in RELEVANT_COMPONENTS])
        avg_uptime = uptime_sum / len(RELEVANT_COMPONENTS)
        points_avg.append((dt, avg_uptime))

    points_avg.sort(key=lambda point: point[0])

    plt.figure(figsize=(20, 10))
    plt.title("Average Monthly Uptime\nCombined averages of API Requests, Actions, Git Operations, Issues, Packages, Pages, Pull Requests, and Webhooks.\nCodespaces and Copilot excluded due to launch post-acquisition.")
    plt.xlabel("Month")
    plt.ylabel("Average Monthly Uptime")
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100, decimals=3))
    plt.plot(
        [point[0] for point in points_avg], [point[1] for point in points_avg],
    )

    _plot_micro_acquisition()

    plt.savefig(OUT_PLOT_AVG)
    print(f"Saved plot to {OUT_PLOT_AVG}")

    # All components
    points_by_comp = dict()

    for comp_name in RELEVANT_COMPONENTS:
        points = list()
        points_by_comp[comp_name] = points

        for group_name, group in monthly_data.items():
            dt = datetime.strptime(group_name, "%Y:%B")
            points.append((dt, group["component_uptimes"][comp_name]))

    plt.figure(figsize=(20, 10))
    plt.title("Average Monthly Uptime by Component")
    plt.xlabel("Month")
    plt.ylabel("Average Monthly Uptime")
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100, decimals=3))

    for comp_name in RELEVANT_COMPONENTS:
        points = points_by_comp[comp_name]
        points.sort(key=lambda point: point[0])
        plt.plot(
            [point[0] for point in points], [point[1] for point in points],
            label=comp_name,
        )

    _plot_micro_acquisition()
    plt.legend(loc="lower left")
    plt.savefig(OUT_PLOT_BY_COMP)
    print(f"Saved plot to {OUT_PLOT_BY_COMP}")

    # Individual components
    for comp_name in RELEVANT_COMPONENTS:
        fpath = OUT_PLOT_INDIVIDUAL_COMP % comp_name
        plt.figure(figsize=(20, 10))
        plt.title("Average Monthly Uptime: %s" % comp_name)
        plt.xlabel("Month")
        plt.ylabel("Average Monthly Uptime")
        plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100, decimals=3))

        points = points_by_comp[comp_name]
        points.sort(key=lambda point: point[0])
        plt.plot(
            [point[0] for point in points], [point[1] for point in points],
            label=comp_name,
        )

        _plot_micro_acquisition()
        plt.legend(loc="lower left")
        plt.savefig(fpath)
        print(f"Saved plot to {fpath}")

def _plot_micro_acquisition():
    plt.axvline(
        x=MICROSOFT_ACQUISITION_DT,
        c="black",
    )
    plt.text(
        MICROSOFT_ACQUISITION_DT, 1,
        "\nMicrosoft Acquires GitHub  ",
        rotation=90,
        horizontalalignment="left",
        verticalalignment="top",
        fontsize="large",
        linespacing=0.1, # How do you offset text properly?
        c="black",
    )


def gather_data() -> MonthlyData:
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    monthly_data, num_conflict = aggregate_monthly(data)
    num_missing = check_missing(monthly_data)
    is_ok = num_conflict + num_missing == 0

    if is_ok:
        print("Data is OK.")
    else:
        print()
        print("ERROR: Data is not OK!")

    print(f"  - {num_conflict} disagreements about monthly uptimes")
    print(f"  - {num_missing} missing entries")

    if not is_ok:
        raise SystemExit(1)

    return monthly_data

def aggregate_monthly(data) -> tuple[MonthlyData, int]:
    monthly_data: MonthlyData = dict()
    num_conflict = 0

    for page in data:
        # Filter for relevant components
        comp_name = page["component"]["name"]

        if comp_name not in RELEVANT_COMPONENTS:
            continue

        # Add to relevant bin, creating it if needed
        for month in page["months"]:
            # Determine if the month has full data
            group_name = f"{month["year"]}:{month["name"]}"
            dt = datetime.strptime(group_name, "%Y:%B")
            dt_now = datetime.now()

            if dt.year == dt_now.year and dt.month == dt_now.month:
                print(f"WARNING: Ignoring current month {group_name} as it may be incomplete.")
                continue

            # Find monthly bin first
            group = monthly_data.get(group_name)

            if group is None:
                group = cast(MonthlyEntry, { # I regret not using TypeScript...
                    "month": month["name"],
                    "year": month["year"],
                    "component_uptimes": dict(),
                })
                monthly_data[group_name] = group

            # Update component uptime entry for the bin
            comp_uptime = month["uptime_percentage"]
            comp_uptimes = group["component_uptimes"]
            existing_uptime = comp_uptimes.get(comp_name)

            if existing_uptime is not None and existing_uptime != comp_uptime:
                print(f"WARNING: Conflicting uptime! Month {group_name} already registered as {existing_uptime}, but was also declared as {comp_uptime}")
                num_conflict += 1

            comp_uptimes[comp_name] = comp_uptime

    return monthly_data, num_conflict

def check_missing(monthly_data: MonthlyData) -> int:
    # Find any month entries missing comps
    num_missing = 0

    for group_name, group in monthly_data.items():
        comp_uptimes = group["component_uptimes"]

        for comp_name in RELEVANT_COMPONENTS:
            if comp_uptimes.get(comp_name) is None: # Also consider nil/None
                print(f"WARNING: Missing data for {comp_name!r} at {group_name}")
                num_missing += 1

    return num_missing


if __name__ == "__main__":
    main()
