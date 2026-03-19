---
name: cloudflare-dns
description: Manage Cloudflare DNS records for volamoks.store. Use when asked to add, remove, list, or update DNS records (CNAME, A, TXT, MX). Examples: "add CNAME for app.volamoks.store", "point sure.volamoks.store to tunnel", "list DNS records", "delete DNS record".
---

# Cloudflare DNS Manager

## Credentials

Always use env vars — never hardcode tokens:
- `CLOUDFLARE_API_TOKEN` — API token with DNS:Edit for volamoks.store
- Zone ID for volamoks.store: resolve at runtime via API (see below)

## Get Zone ID

```bash
curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=volamoks.store" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'][0]['id'])"
```

## List DNS records

```bash
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=volamoks.store" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['result'][0]['id'])")

curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | python3 -c "
import json,sys
records = json.load(sys.stdin)['result']
for r in records:
    print(f\"{r['type']:6} {r['name']:40} -> {r['content']}  (id: {r['id']})\")
"
```

## Add CNAME record (e.g. point to Cloudflare Tunnel)

```bash
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=volamoks.store" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['result'][0]['id'])")

curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "SUBDOMAIN.volamoks.store",
    "content": "TUNNEL_ID.cfargotunnel.com",
    "ttl": 1,
    "proxied": true
  }' | python3 -c "import json,sys; r=json.load(sys.stdin); print('OK:', r['result']['name']) if r['success'] else print('ERROR:', r['errors'])"
```

## Add A record

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "SUBDOMAIN.volamoks.store",
    "content": "IP_ADDRESS",
    "ttl": 1,
    "proxied": true
  }' | python3 -c "import json,sys; r=json.load(sys.stdin); print('OK:', r['result']['name']) if r['success'] else print('ERROR:', r['errors'])"
```

## Delete DNS record

```bash
# First find the record ID from the list command, then:
curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Deleted' if r['success'] else r['errors'])"
```

## Update (patch) existing record

```bash
curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"content": "NEW_VALUE"}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('OK:', r['result']['name']) if r['success'] else print('ERROR:', r['errors'])"
```

## Tunnel CNAME target

To point a subdomain to the existing Jarvis tunnel, get the tunnel ID first:

```bash
docker exec cloudflared cloudflared tunnel list 2>/dev/null || \
curl -s "https://api.cloudflare.com/client/v4/accounts?name=volamoks.store" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), indent=2))"
```

Then CNAME content = `<TUNNEL_ID>.cfargotunnel.com`

## Rules

- Always confirm record name and type before creating
- Check if record already exists before adding (avoid duplicates)
- `proxied: true` means traffic goes through Cloudflare CDN (recommended)
- `ttl: 1` = automatic TTL when proxied
- After creating, verify with: `dig SUBDOMAIN.volamoks.store`
