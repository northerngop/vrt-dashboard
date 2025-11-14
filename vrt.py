#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Delaware Voter Registration Totals + Graphs + Trends + % Change

Features:
  • SSL fixed
  • Downloads all months
  • CSV / TXT / MD output
  • Two graphs:
      - vrt_graph_totals.png  → Absolute + trend lines
      - vrt_graph_percent.png → Party % + % change over time
"""

import csv
import os
from io import StringIO
from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress

# === 1. FORCE FRESH CERTIFI ===
import certifi
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()

import requests

# === 2. CONFIG ===
CSV_FILE = "vrt.csv"
TXT_FILE = "vrt.txt"
MD_FILE  = "vrt.md"
GRAPH_TOTALS = "vrt_graph_totals.png"
GRAPH_PERCENT = "vrt_graph_percent.png"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
})


# === 3. DOWNLOAD & PARSE ===
def voter_record_totals(year: int, month: int, day: int,
                       csv_fd, txt_fd, md_fd, data_list) -> None:
    url = f"https://elections.delaware.gov/voter/registrationtotals/pdfs/vrt_RD{year}{month:02d}{day:02d}.csv"
    print(f"Fetching → {url}")

    try:
        resp = session.get(url, timeout=30, verify=certifi.where())
        resp.raise_for_status()
    except requests.exceptions.SSLError as e:
        print(f"SSL ERROR: {e}")
        return
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            print("Not found (404) – skipping")
        else:
            print(f"HTTP {resp.status_code}: {e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return

    data = StringIO(resp.text)
    reader = csv.DictReader(data)

    party = defaultdict(int)
    rows = 0
    for row in reader:
        rows += 1
        dem = row.get("DEMOCRATIC", "0").strip()
        rep = row.get("REPUBLICAN", "0").strip()
        oth = row.get("OTHERS", "0").strip()

        dem = int(dem) if dem.isdigit() else 0
        rep = int(rep) if rep.isdigit() else 0
        oth = int(oth) if oth.isdigit() else 0

        party["dem"]   += dem
        party["rep"]   += rep
        party["other"] += oth
        party["all"]   += dem + rep + oth

    # FIXED: Use YYYY-MM-01 for JavaScript Date parsing
    iso_date = f"{year}-{month:02d}-01"
    display_date = f"{year}-{month:02d}-{day:02d}"

    csv_fd.write(f"{iso_date},{party['dem']},{party['rep']},{party['other']},{party['all']}\n")
    md_fd.write(f"|{display_date} | {party['dem']:,} | {party['rep']:,} | {party['other']:,} | {party['all']:,}|\n")
    txt_fd.write(f"{display_date} – dem:{party['dem']:,} rep:{party['rep']:,} other:{party['other']:,} all:{party['all']:,}\n")

    data_list.append({
        "date": datetime(year, month, day),
        "dem": party["dem"],
        "rep": party["rep"],
        "other": party["other"],
        "all": party["all"]
    })

    print(f"SUCCESS: {display_date} → {party['all']:,} voters ({rows} rows)\n")

# === 4. GRAPH 1: ABSOLUTE + TRENDS ===
def make_graph_totals(data_list):
    if not data_list:
        print("No data for totals graph.")
        return

    df = pd.DataFrame(data_list).sort_values("date")

    # --- Linear trend lines ---
    def add_trend(ax, x, y, label, color):
        slope, intercept, r, p, se = linregress(x, y)
        line = slope * x + intercept
        ax.plot(df["date"], line, "--", color=color, alpha=0.7,
                label=f"{label} trend (r={r:.3f})")

    # Convert dates to numbers
    x_num = np.arange(len(df))

    plt.figure(figsize=(14, 7))
    ax = plt.gca()

    ax.plot(df["date"], df["all"],   label="Total",   color="black", linewidth=2.5)
    ax.plot(df["date"], df["dem"],   label="Democratic", color="#1f77b4", linewidth=2)
    ax.plot(df["date"], df["rep"],   label="Republican", color="#d62728", linewidth=2)
    ax.plot(df["date"], df["other"], label="Other",      color="#2ca02c", linewidth=2)

    # Add trend lines
    add_trend(ax, x_num, df["all"],   "Total",   "black")
    add_trend(ax, x_num, df["dem"],   "Dem",     "#1f77b4")
    add_trend(ax, x_num, df["rep"],   "Rep",     "#d62728")
    add_trend(ax, x_num, df["other"], "Other",   "#2ca02c")

    plt.title("Delaware Voter Registration Totals with Trend Lines", fontsize=16, pad=20)
    plt.xlabel("Date")
    plt.ylabel("Registered Voters")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(GRAPH_TOTALS, dpi=200)
    plt.close()
    print(f"Graph 1 → {GRAPH_TOTALS}")


# === 5. GRAPH 2: % OF TOTAL + % CHANGE ===
def make_graph_percent(data_list):
    if not data_list:
        print("No data for percent graph.")
        return

    df = pd.DataFrame(data_list).sort_values("date")

    # --- % of total ---
    df["dem_pct"] = df["dem"] / df["all"] * 100
    df["rep_pct"] = df["rep"] / df["all"] * 100
    df["other_pct"] = df["other"] / df["all"] * 100

    # --- Month-to-month % change ---
    df["dem_change"] = df["dem"].pct_change() * 100
    df["rep_change"] = df["rep"].pct_change() * 100
    df["other_change"] = df["other"].pct_change() * 100
    df["all_change"] = df["all"].pct_change() * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # --- Stacked area: % of total ---
    ax1.stackplot(df["date"], df["dem_pct"], df["rep_pct"], df["other_pct"],
                  labels=["Democratic", "Republican", "Other"],
                  colors=["#1f77b4", "#d62728", "#2ca02c"], alpha=0.8)
    ax1.set_title("Party Share of Total Registered Voters (%)", fontsize=14)
    ax1.set_ylabel("Percentage (%)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 100)

    # --- % Change over time ---
    ax2.plot(df["date"], df["dem_change"], label="Dem %Δ", color="#1f77b4")
    ax2.plot(df["date"], df["rep_change"], label="Rep %Δ", color="#d62728")
    ax2.plot(df["date"], df["other_change"], label="Other %Δ", color="#2ca02c")
    ax2.plot(df["date"], df["all_change"], label="Total %Δ", color="black", linewidth=2)

    ax2.set_title("Month-to-Month % Change in Registration", fontsize=14)
    ax2.set_ylabel("% Change")
    ax2.set_xlabel("Date")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(0, color="gray", linewidth=0.8)

    plt.tight_layout()
    plt.savefig(GRAPH_PERCENT, dpi=200)
    plt.close()
    print(f"Graph 2 → {GRAPH_PERCENT}")


# === 6. MAIN ===
def main() -> None:
    print("Delaware Voter Registration Totals + Trends → START\n")

    data_for_graph = []

    with open(CSV_FILE, "w", newline="") as csv_fd, \
         open(TXT_FILE, "w") as txt_fd, \
         open(MD_FILE,  "w") as md_fd:

        csv_fd.write("month,dem,rep,other,all\n")
        md_fd.write("|month|dem|rep|other|all|\n")
        md_fd.write("|--:|--:|--:|--:|--:|\n")

        dates = (
            [(2021, m, 1) for m in range(1, 13)] +
            [(2022, m, 1) for m in range(1, 10)] + [(2022, 10, 2), (2022, 11, 1), (2022, 12, 1)] +
            [(2023, m, 1) for m in range(1, 13)] +
            [(2024, m, 1) for m in range(1, 13)] +
            [(2025, m, 1) for m in range(1, 12)]
        )

        today = datetime.now()
        for y, m, d in dates:
            if (y > today.year) or (y == today.year and m > today.month):
                print(f"Skipping future: {y}-{m:02d}-{d:02d}\n")
                continue
            voter_record_totals(y, m, d, csv_fd, txt_fd, md_fd, data_for_graph)

    # Generate graphs
    make_graph_totals(data_for_graph)
    make_graph_percent(data_for_graph)

    print(f"\nDONE! Files created:")
    print(f"  • {CSV_FILE}")
    print(f"  • {TXT_FILE}")
    print(f"  • {MD_FILE}")
    print(f"  • {GRAPH_TOTALS}")
    print(f"  • {GRAPH_PERCENT}")

import webbrowser
import time

if __name__ == "__main__":
    main()

    # Wait a moment for files to be written
    time.sleep(1)

    # Start server in background (non-blocking)
    import subprocess
    subprocess.Popen(["python3", "-m", "http.server", "8001"])

    # Open dashboard
    webbrowser.open("http://localhost:8000/vrt_dashboard.html")
