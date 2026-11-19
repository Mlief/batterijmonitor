#!/usr/bin/env python3
"""Daily public-source battery project monitor. Uses only Python standard library."""
from __future__ import annotations
import email.utils
import html
import json
import os
import re
import smtplib
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

QUERIES = [
    '("batterijopslag" OR "energieopslag" OR BESS) (glastuinbouw OR kwekerij OR tuinder OR tuinbouw)',
    '(batterij OR energieopslag) (agrarisch OR landbouw OR akkerbouw OR veehouderij) Nederland',
    '("batterij geplaatst" OR "batterij geïnstalleerd" OR batterijproject) (kwekerij OR glastuinbouw OR agrarisch)',
    '("batterijproject" OR "energieopslagproject") (tuinbouw OR agrarisch OR kwekerij) Nederland',
    '("500 kW" OR 500kW OR "1 MW" OR 1MW OR "2 MW" OR "5 MW") (batterij OR energieopslag) Nederland',
    '(batterij OR energieopslag) (vergunning OR ontwikkeling OR bouw OR aangekondigd OR uitbreiding) (agrarisch OR tuinbouw)',
    '(batterijopslag OR BESS) (kwekerij OR tuinder OR glastuinbouw OR landbouw) Nederland',
]
SEEN_FILE = Path("data/seen.json")
REPORT_FILE = Path("report.html")
UA = "Mozilla/5.0 (compatible; Batterijmonitor/1.0; +https://github.com/)"

SECTOR = re.compile(r"glastuinbouw|tuinbouw|kweker|tuinder|agrar|landbouw|akkerbouw|veehouder|horti", re.I)
PROJECT = re.compile(r"batterij|bess|energie.?opslag|accu.?opslag", re.I)
STATUS = [
    ("Uitbreiding", re.compile(r"uitbreid|extra batterij|capaciteit erbij", re.I)),
    ("Geplaatst / gerealiseerd", re.compile(r"geplaatst|geïnstalleerd|gerealiseerd|in gebruik|opgeleverd", re.I)),
    ("In ontwikkeling", re.compile(r"vergunning|ontwikkeling|bouw|realisatie|bouwplan|voorbereid", re.I)),
    ("Aangekondigd", re.compile(r"aangekondig|investeert|investering|plan voor|gaat bouwen", re.I)),
]
POWER = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(MW|MWe|kW|kWe)(?!\w)", re.I)
ENERGY = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(MWh|kWh)(?!\w)", re.I)

def get_text(el, tag):
    node = el.find(tag)
    return (node.text or "").strip() if node is not None else ""

def fetch(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "nl", "gl": "NL", "ceid": "NL:nl"
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as response:
        root = ET.fromstring(response.read())
    items = []
    for item in root.findall(".//item"):
        title, link = get_text(item, "title"), get_text(item, "link")
        desc = re.sub(r"<[^>]+>", " ", get_text(item, "description"))
        desc = html.unescape(re.sub(r"\s+", " ", desc)).strip()
        pub = get_text(item, "pubDate")
        if link and title:
            items.append({"title": html.unescape(title), "link": link, "description": desc, "pubDate": pub})
    return items

def classify(item):
    text = item["title"] + " " + item["description"]
    if not PROJECT.search(text):
        return None
    if not SECTOR.search(text):
        return None
    status = next((name for name, pattern in STATUS if pattern.search(text)), "Project / status onbekend")
    powers = [f"{m.group(1).replace(',', '.')} {m.group(2)}" for m in POWER.finditer(text)]
    energies = [f"{m.group(1).replace(',', '.')} {m.group(2)}" for m in ENERGY.finditer(text)]
    kw = []
    for value in powers:
        m = re.match(r"(\d+(?:\.\d+)?)\s*(MW|MWe|kW|kWe)", value, re.I)
        if m:
            n = float(m.group(1))
            kw.append(n * 1000 if m.group(2).lower().startswith("mw") else n)
    if kw and max(kw) > 500:
        priority = "HOOG"
    elif status != "Project / status onbekend":
        priority = "MIDDEL"
    else:
        priority = "LAAG"
    return {**item, "status": status, "power": ", ".join(dict.fromkeys(powers)) or "Niet vermeld",
            "energy": ", ".join(dict.fromkeys(energies)) or "Niet vermeld",
            "priority": priority}

def esc(value):
    return html.escape(str(value or ""))

def main():
    now = datetime.now(timezone.utc)
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        seen_data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        seen_data = {}
    cutoff = (now - timedelta(days=45)).isoformat()
    seen_data = {k:v for k,v in seen_data.items() if v >= cutoff}
    found = {}
    errors = []
    for query in QUERIES:
        try:
            for item in fetch(query):
                lead = classify(item)
                if lead:
                    found[lead["link"]] = lead
        except Exception as exc:
            errors.append(f"{query}: {type(exc).__name__}: {exc}")
    new = [x for url,x in found.items() if url not in seen_data]
    new.sort(key=lambda x: ({"HOOG":0,"MIDDEL":1,"LAAG":2}[x["priority"]], x["title"].lower()))
    for item in new:
        seen_data[item["link"]] = now.isoformat()
    SEEN_FILE.write_text(json.dumps(seen_data, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for x in new:
        date = x["pubDate"] or "Datum onbekend"
        rows.append(f"""<tr><td><b>{esc(x['priority'])}</b></td><td><a href="{esc(x['link'])}">{esc(x['title'])}</a><br><small>{esc(x['description'])}</small></td><td>{esc(x['status'])}</td><td>{esc(x['power'])}</td><td>{esc(x['energy'])}</td><td>{esc(date)}</td></tr>""")
    error_html = "<p><b>Bronmeldingen:</b><br>" + "<br>".join(esc(e) for e in errors) + "</p>" if errors else ""
    body = f"""<!doctype html><html lang="nl"><meta charset="utf-8"><title>Batterijmonitor</title>
    <style>body{{font:14px Arial,sans-serif;color:#222}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}th{{background:#eef}}small{{color:#555}}</style>
    <h2>Batterijmonitor – {now.astimezone().strftime('%d-%m-%Y')}</h2>
    <p>{len(new)} nieuwe relevante openbare vermeldingen gevonden.</p>
    <p>Focus: Nederlandse glastuinbouw en agrarische bedrijven. Vermogen en capaciteit worden alleen vermeld als de bron ze noemt.</p>
    <table><tr><th>Prioriteit</th><th>Bericht / bron</th><th>Status</th><th>Vermogen</th><th>Opslag</th><th>Publicatiedatum</th></tr>
    {''.join(rows) if rows else '<tr><td colspan="6">Geen nieuwe relevante vermeldingen gevonden.</td></tr>'}</table>
    {error_html}<p><small>Automatische signalering op basis van openbare indexeerbare bronnen. Geen volledige LinkedIn-dekking; controleer de bron voor opvolging.</small></p></html>"""
    REPORT_FILE.write_text(body, encoding="utf-8")
    print(f"New leads: {len(new)}; source errors: {len(errors)}")

    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("MAIL_TO")
    sender = os.getenv("MAIL_FROM") or username
    if all([host, username, password, recipient, sender]):
        msg = EmailMessage()
        msg["Subject"] = f"Batterijmonitor – {len(new)} nieuwe signalen – {now.strftime('%d-%m-%Y')}"
        msg["From"], msg["To"] = sender, recipient
        msg.set_content(f"{len(new)} nieuwe relevante vermeldingen. Open het HTML-rapport in de GitHub Actions-artifact.")
        msg.add_alternative(body, subtype="html")
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(msg)
        print("Email sent.")
    else:
        print("Email skipped: SMTP secrets are not configured.")

if __name__ == "__main__":
    main()
