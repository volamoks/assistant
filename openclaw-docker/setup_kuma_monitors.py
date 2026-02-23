#!/usr/bin/env python3
"""
Setup Uptime Kuma monitors for all Docker services.
Usage: python3 setup_kuma_monitors.py [--username admin] [--password yourpass]
"""
import argparse
import sys
from uptime_kuma_api import UptimeKumaApi, MonitorType

KUMA_URL = "http://localhost:3003"

# All monitors to create: (name, url_or_host, port, type)
HTTP_MONITORS = [
    ("🏠 Homepage",         "http://host.docker.internal:3012", None),
    ("💬 Open WebUI",       "http://host.docker.internal:3005", None),
    ("🤖 Jarvis / OpenClaw","http://host.docker.internal:18789",None),
    ("🌊 TorrServer",       "http://host.docker.internal:8090", None),
    ("📋 Planka",           "http://host.docker.internal:3010", None),
    ("🔗 Shlink",           "http://host.docker.internal:3011", None),
    ("📄 Stirling PDF",     "http://host.docker.internal:3013", None),
    ("📊 Ryot",             "http://host.docker.internal:3014", None),
    ("⚙️  n8n",              "http://host.docker.internal:3016", None),
    ("🔍 SearXNG",          "http://host.docker.internal:3017", None),
    ("📈 Beszel",           "http://host.docker.internal:8096", None),
    ("🧠 LiteLLM proxy",   "http://host.docker.internal:18788",None),
    ("🦙 Ollama",           "http://host.docker.internal:11434",None),
    ("🔮 ChromaDB",         "http://host.docker.internal:8002", None),
    ("🏡 Home Assistant",   "http://192.168.147.16:8123",       None),
]

TCP_MONITORS = [
    ("🗄️  Redis",           "host.docker.internal", 6379),
    ("🐘 PostgreSQL",       "host.docker.internal", 5432),
]

DNS_MONITOR = [
    ("🛡️  AdGuard DNS",    "host.docker.internal", 53, "dns"),
]

def main():
    parser = argparse.ArgumentParser(description="Setup Uptime Kuma monitors")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--setup", action="store_true",
                        help="Create admin account (first run only)")
    parser.add_argument("--setup-password", help="Password for new admin account (with --setup)")
    args = parser.parse_args()

    print(f"Connecting to Uptime Kuma at {KUMA_URL}...")
    api = UptimeKumaApi(KUMA_URL)

    try:
        if args.setup:
            pwd = args.setup_password or args.password
            print("Creating admin account...")
            api.setup(args.username, pwd)
            print(f"✅ Admin account created: {args.username}")

        print(f"Logging in as {args.username}...")
        api.login(args.username, args.password)
        print("✅ Logged in")

        # Get existing monitors to avoid duplicates
        existing = api.get_monitors()
        existing_names = {m["name"] for m in existing}
        print(f"Found {len(existing_names)} existing monitors: {existing_names or 'none'}")

        created = 0
        skipped = 0

        # HTTP monitors
        for name, url, _ in HTTP_MONITORS:
            if name in existing_names:
                print(f"  ⏭️  Skip (exists): {name}")
                skipped += 1
                continue
            try:
                api.add_monitor(
                    type=MonitorType.HTTP,
                    name=name,
                    url=url,
                    interval=60,
                    retryInterval=60,
                    maxretries=3,
                    ignoreTls=True,
                )
                print(f"  ✅ Created HTTP: {name} → {url}")
                created += 1
            except Exception as e:
                print(f"  ❌ Failed {name}: {e}")

        # TCP monitors
        for name, host, port in TCP_MONITORS:
            if name in existing_names:
                print(f"  ⏭️  Skip (exists): {name}")
                skipped += 1
                continue
            try:
                api.add_monitor(
                    type=MonitorType.TCP_PING,
                    name=name,
                    hostname=host,
                    port=port,
                    interval=60,
                    retryInterval=60,
                    maxretries=3,
                )
                print(f"  ✅ Created TCP: {name} → {host}:{port}")
                created += 1
            except Exception as e:
                print(f"  ❌ Failed {name}: {e}")

        # DNS monitor for AdGuard
        dns_name = "🛡️  AdGuard DNS"
        if dns_name not in existing_names:
            try:
                api.add_monitor(
                    type=MonitorType.DNS,
                    name=dns_name,
                    hostname="host.docker.internal",
                    port=53,
                    dns_resolve_server="host.docker.internal",
                    dns_resolve_type="A",
                    interval=120,
                    retryInterval=60,
                    maxretries=3,
                )
                print(f"  ✅ Created DNS: {dns_name}")
                created += 1
            except Exception as e:
                print(f"  ❌ Failed {dns_name}: {e}")
        else:
            print(f"  ⏭️  Skip (exists): {dns_name}")
            skipped += 1

        print(f"\n🎉 Done! Created: {created}, Skipped: {skipped}")

    finally:
        api.disconnect()

if __name__ == "__main__":
    main()
