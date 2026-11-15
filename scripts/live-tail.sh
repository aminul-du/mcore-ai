#!/usr/bin/env bash
set -e

# Trap Ctrl+C and kill all child background jobs cleanly
trap 'kill 0' SIGINT SIGTERM EXIT

# Load environment
if [ -f /srv/mcore/apps/web/.env.local ]; then
  set -a
  source /srv/mcore/apps/web/.env.local
  set +a
fi

echo -e "\x1b[1;35m>>> Starting Unified Telemetry Stream (Cloudflare Edge + LiveKit SFU + Agent Daemon)...\x1b[0m"

# 1. Cloudflare Edge Tail
(
  cd /srv/mcore/workers/sorborno-voice
  npx wrangler tail sorborno-voice --format=pretty 2>&1 | sed -u $'s/^/\x1b[36m[CF-EDGE]\x1b[0m /'
) &

# 2. LiveKit Docker SFU Logs
(
  docker logs -f --tail 10 livekit-server 2>&1 | sed -u $'s/^/\x1b[33m[LIVEKIT]\x1b[0m /'
) &

# 3. Shorborno Agent Journalctl Trace
(
  journalctl -u shorborno-agent -f -n 10 --no-pager 2>&1 | sed -u $'s/^/\x1b[32m[AGENT]\x1b[0m /'
) &

wait
