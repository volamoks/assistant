#!/usr/bin/env python3
"""
caldav_apple.py — Apple Calendar (iCloud CalDAV) for OpenClaw agents

Commands:
  calendars                                              — list all calendars
  today                                                  — today's events
  week                                                   — this week's events
  upcoming [days=3]                                      — next N days
  find "<query>"                                         — search by title/description
  create "<title>" <YYYY-MM-DD> <HH:MM> [min=60] [desc] — create event

Auth (env vars):
  CALDAV_APPLE_EMAIL     — defaults to komalov@me.com
  EMAIL_PASS_MECOM       — App-Specific Password (already in .env)
"""

import os, sys, re, uuid
import urllib.request, urllib.error
import base64
from datetime import datetime, timedelta, timezone, date
from xml.etree import ElementTree as ET
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
EMAIL    = os.environ.get("CALDAV_APPLE_EMAIL")
PASSWORD = os.environ.get("CALDAV_APPLE_PASSWORD") or os.environ.get("EMAIL_PASS_MECOM", "")
TZ_OFFSET_HOURS = int(os.environ.get("CALDAV_TZ_OFFSET_HOURS", "5"))  # UTC+5 (Tashkent)

if not EMAIL:
    raise ValueError("CALDAV_APPLE_EMAIL environment variable is required")
LOCAL_TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))

CALDAV_BASE = "https://caldav.icloud.com"

# ── HTTP helpers ─────────────────────────────────────────────────────────────

def basic_auth():
    token = base64.b64encode(f"{EMAIL}:{PASSWORD}".encode()).decode()
    return f"Basic {token}"


def caldav_req(method, url, body=None, extra_headers=None):
    """Make a CalDAV HTTP request. Follows redirects for PROPFIND."""
    headers = {
        "Authorization": basic_auth(),
        "Content-Type": "application/xml; charset=utf-8",
    }
    if extra_headers:
        headers.update(extra_headers)

    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        # Follow redirect manually (CalDAV redirects often need auth re-sent)
        if e.code in (301, 302, 307, 308):
            loc = e.headers.get("Location", "")
            if loc:
                if loc.startswith("/"):
                    loc = CALDAV_BASE + loc
                return caldav_req(method, loc, body, extra_headers)
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        return e.code, err_body


# ── CalDAV discovery ─────────────────────────────────────────────────────────

PROPFIND_PRINCIPAL = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop><d:current-user-principal/></d:prop>
</d:propfind>"""

PROPFIND_HOME = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><c:calendar-home-set/></d:prop>
</d:propfind>"""

PROPFIND_CALENDARS = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:displayname/>
    <d:resourcetype/>
    <c:supported-calendar-component-set/>
  </d:prop>
</d:propfind>"""


def _href_text(element):
    """Extract href text from an XML element."""
    href = element.find("{DAV:}href")
    if href is not None and href.text:
        url = href.text.strip()
        if url.startswith("/"):
            url = CALDAV_BASE + url
        return url
    return None


def get_principal_url():
    urls_to_try = [
        f"{CALDAV_BASE}/.well-known/caldav",
        CALDAV_BASE,
    ]
    for url in urls_to_try:
        status, body = caldav_req("PROPFIND", url, PROPFIND_PRINCIPAL, {"Depth": "0"})
        if status in (200, 207) and body:
            try:
                root = ET.fromstring(body)
                for el in root.iter("{DAV:}current-user-principal"):
                    href = _href_text(el)
                    if href:
                        return href
            except ET.ParseError:
                pass
    die("❌ Could not discover CalDAV principal. Check email/password.")


def get_calendar_home(principal_url):
    status, body = caldav_req("PROPFIND", principal_url, PROPFIND_HOME, {"Depth": "0"})
    if status in (200, 207) and body:
        try:
            root = ET.fromstring(body)
            for el in root.iter("{urn:ietf:params:xml:ns:caldav}calendar-home-set"):
                href = _href_text(el)
                if href:
                    return href
        except ET.ParseError:
            pass
    die("❌ Could not get calendar-home-set.")


def list_calendars(home_url):
    status, body = caldav_req("PROPFIND", home_url, PROPFIND_CALENDARS, {"Depth": "1"})
    calendars = []
    if status not in (200, 207) or not body:
        return calendars
    try:
        root = ET.fromstring(body)
        for response in root.findall("{DAV:}response"):
            href_el = response.find("{DAV:}href")
            if href_el is None:
                continue
            href = href_el.text.strip()
            url = href if href.startswith("http") else CALDAV_BASE + href

            # Must be a calendar resourcetype
            rt = response.find(".//{DAV:}resourcetype")
            if rt is None or rt.find("{urn:ietf:params:xml:ns:caldav}calendar") is None:
                continue

            # Must support VEVENT
            comp_set = response.find(".//{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set")
            if comp_set is not None:
                comps = [el.get("name", "") for el in comp_set]
                if "VEVENT" not in comps:
                    continue

            name_el = response.find(".//{DAV:}displayname")
            name = (name_el.text or "").strip() if name_el is not None else href.rstrip("/").split("/")[-1]
            if not name:
                name = "(unnamed)"

            calendars.append({"name": name, "url": url})
    except ET.ParseError as e:
        die(f"❌ XML parse error listing calendars: {e}")
    return calendars


# ── iCal parsing ──────────────────────────────────────────────────────────────

def parse_ical_dt(value_str):
    """Parse iCal datetime value to UTC datetime."""
    v = value_str.strip()
    # Remove timezone offset if value has been reconstructed oddly
    if len(v) == 8:  # DATE only: 20260304
        d = datetime.strptime(v, "%Y%m%d")
        return d.replace(tzinfo=LOCAL_TZ)
    if v.endswith("Z"):  # UTC
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    try:
        dt = datetime.strptime(v, "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None


def unfold_ical(text):
    """Unfold multi-line iCal properties."""
    return re.sub(r"\r?\n[ \t]", "", text)


def parse_vevent(block):
    """Parse a VEVENT text block into a dict."""
    block = unfold_ical(block)
    event = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        # Handle params: DTSTART;TZID=...:value
        colon_pos = line.find(":")
        semi_pos = line.find(";")
        if semi_pos != -1 and semi_pos < colon_pos:
            key = line[:semi_pos].upper().strip()
            value = line[colon_pos + 1:].strip()
        else:
            key = line[:colon_pos].upper().strip()
            value = line[colon_pos + 1:].strip()

        def unescape(s):
            return s.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";")

        if key == "SUMMARY":
            event["title"] = unescape(value)
        elif key == "DTSTART":
            event["start"] = parse_ical_dt(value)
        elif key == "DTEND":
            event["end"] = parse_ical_dt(value)
        elif key == "DESCRIPTION":
            event["description"] = unescape(value)
        elif key == "LOCATION":
            event["location"] = unescape(value)
        elif key == "UID":
            event["uid"] = value
    return event


def fetch_events(calendar_url, start_utc, end_utc):
    """Fetch VEVENT objects from a single calendar in a date range."""
    start_str = start_utc.strftime("%Y%m%dT%H%M%SZ")
    end_str   = end_utc.strftime("%Y%m%dT%H%M%SZ")

    report_body = f"""<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:getetag/>
    <c:calendar-data/>
  </d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{start_str}" end="{end_str}"/>
      </c:comp-filter>
    </c:comp-filter>
  </c:filter>
</c:calendar-query>"""

    status, body = caldav_req("REPORT", calendar_url, report_body,
                               {"Depth": "1", "Content-Type": "application/xml"})
    events = []
    if status not in (200, 207) or not body:
        return events
    try:
        root = ET.fromstring(body)
        for response in root.findall("{DAV:}response"):
            cal_data = response.find(".//{urn:ietf:params:xml:ns:caldav}calendar-data")
            if cal_data is None or not cal_data.text:
                continue
            for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", cal_data.text, re.DOTALL):
                ev = parse_vevent(block)
                if ev.get("start") and ev.get("title"):
                    events.append(ev)
    except ET.ParseError:
        pass
    return events


# ── Output formatting ─────────────────────────────────────────────────────────

def format_event(ev):
    start = ev.get("start")
    end   = ev.get("end")
    title = ev.get("title", "(no title)")
    loc   = ev.get("location", "")
    desc  = ev.get("description", "")

    if start:
        s = start.astimezone(LOCAL_TZ)
        if start.hour == 0 and start.minute == 0 and (not end or (end.hour == 0 and end.minute == 0)):
            time_str = "(all day)"
        else:
            time_str = s.strftime("%H:%M")
            if end:
                time_str += "–" + end.astimezone(LOCAL_TZ).strftime("%H:%M")
    else:
        time_str = "?"

    line = f"  {time_str}  {title}"
    if loc:
        line += f"  📍{loc}"
    if desc:
        snippet = desc.strip().replace("\n", " ")[:80]
        line += f"\n           {snippet}"
    return line


def format_grouped(events):
    by_date = defaultdict(list)
    for ev in events:
        if ev.get("start"):
            d = ev["start"].astimezone(LOCAL_TZ).date()
            by_date[d].append(ev)

    if not by_date:
        return "  (no events)"

    today = datetime.now(LOCAL_TZ).date()
    lines = []
    for d in sorted(by_date):
        evs = sorted(by_date[d], key=lambda e: e.get("start") or datetime.min.replace(tzinfo=timezone.utc))
        label = d.strftime("%A, %d %b")
        if d == today:
            label = f"Today — {label}"
        elif d == today + timedelta(days=1):
            label = f"Tomorrow — {label}"
        lines.append(f"\n{label}:")
        for ev in evs:
            lines.append(format_event(ev))
    return "\n".join(lines)


# ── Core helpers ──────────────────────────────────────────────────────────────

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def check_password():
    if not PASSWORD:
        die("❌ Set EMAIL_PASS_MECOM (or CALDAV_APPLE_PASSWORD) in your environment.")


def get_all_events(start_utc, end_utc):
    check_password()
    principal  = get_principal_url()
    home       = get_calendar_home(principal)
    calendars  = list_calendars(home)
    all_events = []
    for cal in calendars:
        all_events.extend(fetch_events(cal["url"], start_utc, end_utc))
    return all_events


def today_start_end():
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_calendars():
    check_password()
    principal = get_principal_url()
    home      = get_calendar_home(principal)
    cals      = list_calendars(home)
    if not cals:
        print("No calendars found.")
        return
    print(f"📅 {len(cals)} calendar(s) on {EMAIL}:")
    for c in cals:
        print(f"  • {c['name']}")


def cmd_today():
    start, end = today_start_end()
    events = get_all_events(start, end)
    print(f"📅 Today — {datetime.now(LOCAL_TZ).strftime('%d %B %Y')}")
    print(format_grouped(events))


def cmd_week():
    now   = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=7)
    events = get_all_events(start, end)
    s = datetime.now(LOCAL_TZ)
    print(f"📅 This week ({s.strftime('%d %b')} – {(s + timedelta(days=6)).strftime('%d %b')})")
    print(format_grouped(events))


def cmd_upcoming(days=3):
    now   = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=days)
    events = get_all_events(start, end)
    print(f"📅 Next {days} day(s)")
    print(format_grouped(events))


def cmd_find(query):
    now   = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    end   = now + timedelta(days=90)
    events = get_all_events(start, end)
    q = query.lower()
    hits = [e for e in events
            if q in e.get("title", "").lower() or q in e.get("description", "").lower()]
    print(f"🔍 '{query}': {len(hits)} match(es)")
    print(format_grouped(hits))


def cmd_create(title, date_str, time_str, duration_min=60, description=""):
    check_password()
    principal = get_principal_url()
    home      = get_calendar_home(principal)
    cals      = list_calendars(home)
    if not cals:
        die("❌ No calendars found.")

    # Use first calendar (default Home calendar)
    cal = cals[0]

    try:
        dt_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        dt_start = dt_start.replace(tzinfo=LOCAL_TZ)
    except ValueError:
        die(f"❌ Invalid date/time: '{date_str} {time_str}' (expected YYYY-MM-DD HH:MM)")

    dt_end  = dt_start + timedelta(minutes=duration_min)
    uid     = str(uuid.uuid4())
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = dt_start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtend   = dt_end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    ical = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//OpenClaw//CalDAV//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DESCRIPTION:{description}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    event_url = cal["url"].rstrip("/") + f"/{uid}.ics"
    headers = {
        "Authorization": basic_auth(),
        "Content-Type": "text/calendar; charset=utf-8",
    }
    req = urllib.request.Request(event_url, data=ical.encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ Created '{title}' on {date_str} at {time_str} in '{cal['name']}'")
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode()
        except Exception:
            err = str(e)
        die(f"❌ Failed to create event: {e.code} — {err[:200]}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "calendars":
        cmd_calendars()
    elif cmd == "today":
        cmd_today()
    elif cmd == "week":
        cmd_week()
    elif cmd == "upcoming":
        days = int(args[1]) if len(args) > 1 else 3
        cmd_upcoming(days)
    elif cmd == "find":
        if len(args) < 2:
            die("Usage: caldav_apple.py find <query>")
        cmd_find(args[1])
    elif cmd == "create":
        if len(args) < 4:
            die("Usage: caldav_apple.py create <title> <YYYY-MM-DD> <HH:MM> [duration_min] [description]")
        title    = args[1]
        date_str = args[2]
        time_str = args[3]
        duration = int(args[4]) if len(args) > 4 else 60
        desc     = args[5] if len(args) > 5 else ""
        cmd_create(title, date_str, time_str, duration, desc)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
