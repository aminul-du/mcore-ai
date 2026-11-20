#!/usr/bin/env bash
set -euo pipefail

ZONE_NAME="sorbornoai.com"
SUBDOMAINS=("voice" "api" "ai" "studio" "admin" "docs")
DEFAULT_CNAME_TARGET="sorbornoai-web.pages.dev"
EVIDENCE_FILE="/srv/mcore/evidence/sorborno-subdomains-audit.json"

: "${CLOUDFLARE_API_TOKEN:?ERROR: CLOUDFLARE_API_TOKEN is not set}"

cf_api() {
  local method="$1" path="$2" data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"       -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"       -H "Content-Type: application/json"       --data "$data"
  else
    curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"       -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"       -H "Content-Type: application/json"
  fi
}

ZONE_ID=$(cf_api GET "/zones?name=${ZONE_NAME}" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(r[0]['id'] if r else '')")
if [[ -z "$ZONE_ID" ]]; then
  echo "ERROR: Could not resolve Zone ID for ${ZONE_NAME}" >&2
  exit 1
fi

echo "Zone ${ZONE_NAME} resolved (${ZONE_ID}). Auditing & provisioning subdomains..."
EXISTING_JSON=$(cf_api GET "/zones/${ZONE_ID}/dns_records?per_page=100")

for sub in "${SUBDOMAINS[@]}"; do
  fqdn="${sub}.${ZONE_NAME}"
  rec_info=$(python3 -c "
import sys, json
recs = json.loads(sys.argv[1])['result']
matches = [r for r in recs if r['name'] == sys.argv[2] and r['type'] in ('CNAME', 'A', 'AAAA')]
if matches:
    r = matches[0]
    print(f"{r['type']}|{r['content']}|{r['proxied']}")
" "$EXISTING_JSON" "$fqdn")

  if [[ -n "$rec_info" ]]; then
    echo "  [EXISTS]   ${fqdn} -> ${rec_info}"
  else
    # Note: voice.sorbornoai.com is normally managed by Wrangler Custom Domains;
    # provisioning a proxied CNAME placeholder ensures edge resolution until worker route/domain binds.
    create_resp=$(cf_api POST "/zones/${ZONE_ID}/dns_records"       "{\"type\":\"CNAME\",\"name\":\"${sub}\",\"content\":\"${DEFAULT_CNAME_TARGET}\",\"ttl\":1,\"proxied\":true,\"comment\":\"Provisioned by MCORE-FDR-AIS-001\"}")
    ok=$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('success', False))" "$create_resp")
    if [[ "$ok" == "True" ]]; then
      echo "  [CREATED]  ${fqdn} -> CNAME ${DEFAULT_CNAME_TARGET} (proxied=true)"
    else
      echo "  [ERROR]    Failed creating ${fqdn}: ${create_resp}" >&2
      exit 1
    fi
  fi
done

echo ""
echo "Running post-provision Cloudflare API & Public Edge DNS verification..."
FINAL_JSON=$(cf_api GET "/zones/${ZONE_ID}/dns_records?per_page=100")
echo "$FINAL_JSON" > "$EVIDENCE_FILE"

printf "
| Subdomain | Record Type | Target | Proxied | Edge DNS Check |
| :--- | :--- | :--- | :--- | :--- |
"
for sub in "${SUBDOMAINS[@]}"; do
  fqdn="${sub}.${ZONE_NAME}"
  row=$(python3 -c "
import sys, json
recs = json.loads(sys.argv[1])['result']
m = [r for r in recs if r['name'] == sys.argv[2] and r['type'] in ('CNAME', 'A', 'AAAA')]
if m:
    r = m[0]
    print(f"{r['type']}|{r['content']}|{r['proxied']}")
else:
    print("MISSING|none|false")
" "$FINAL_JSON" "$fqdn")
  IFS="|" read -r rtype rtarget rprox <<< "$row"
  edge_ip=$(dig +short A "$fqdn" @1.1.1.1 | head -n 1)
  [[ -z "$edge_ip" ]] && edge_ip="propagating"
  printf "| \`%s\` | %s | \`%s\` | %s | %s |
" "$fqdn" "$rtype" "$rtarget" "$rprox" "$edge_ip"
done
