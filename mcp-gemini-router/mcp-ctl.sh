#!/usr/bin/env bash
set -Eeuo pipefail

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
SERVICE="mcore-gemini-mcp.service"
ENDPOINT="http://127.0.0.1:18089/mcp"

run_http_probe() {
  /home/mcoreai/mcore-isolated/venv/bin/python - "${ENDPOINT}" <<'PY'
import json, sys, urllib.request

url = sys.argv[1]

def post_mcp(payload, session_id=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        sid = resp.headers.get("mcp-session-id") or session_id
        raw = resp.read().decode("utf-8")
        ctype = resp.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            msgs = []
            for line in raw.splitlines():
                if line.startswith("data:"):
                    part = line[5:].strip()
                    if part:
                        msgs.append(json.loads(part))
            return msgs[-1] if msgs else {}, sid
        return (json.loads(raw) if raw.strip() else {}), sid

init_res, sid = post_mcp({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "mcore-axum-probe", "version": "1.0.0"},
    },
})
assert "result" in init_res, f"Initialize failed: {init_res}"

post_mcp({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
tools_res, _ = post_mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, sid)
tool_names = [t["name"] for t in tools_res["result"]["tools"]]

status_res, _ = post_mcp({
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {"name": "mcore_router_status", "arguments": {}},
}, sid)
status_text = status_res["result"]["content"][0]["text"]

print(f"  [PASS] Endpoint   : {url} (session={sid})")
print(f"  [PASS] ServerInfo : {init_res['result']['serverInfo']}")
print(f"  [PASS] Tools ({len(tool_names)})  : {tool_names}")
print(f"  [PASS] RouterState:\n{status_text}")
PY
}

case "${1:-status}" in
  start|stop|restart)
    systemctl --user "$1" "${SERVICE}"
    systemctl --user --no-pager -l status "${SERVICE}"
    ;;
  status)
    systemctl --user --no-pager -l status "${SERVICE}"
    ;;
  logs)
    journalctl --user -u "${SERVICE}" -n "${2:-50}" --no-pager
    ;;
  test)
    run_http_probe
    ;;
  *)
    echo "Usage: $0 {status|start|stop|restart|logs [N]|test}"
    exit 1
    ;;
esac
