#!/usr/bin/env bash
set -Eeuo pipefail

load_env_if_unset() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    line="${line#export }"
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local k="${BASH_REMATCH[1]}"
      local v="${BASH_REMATCH[2]}"
      v="${v#"${v%%[![:space:]]*}"}"
      v="${v%"${v##*[![:space:]]}"}"
      if [[ ( "$v" == \"*\" && "$v" == *\" ) || ( "$v" == \'*\' && "$v" == *\' ) ]]; then
        v="${v:1:${#v}-2}"
      fi
      if [[ -z "${!k:-}" && -n "$v" && "$v" != replace_* ]]; then
        export "${k}=${v}"
      fi
    fi
  done < "$f"
}

# 1. Always backfill unset GROQ_API_KEY / CLOUDFLARE_* from Arena .env & Sandbox 1 env
load_env_if_unset "/srv/mcore/mcore-ai-arena/.env"
load_env_if_unset "/home/mcoreai/.config/mcore-aistudio/profiles/org-v4-argon/org-aistudio.env"

# 2. If Gemini auth mode wasn't explicitly forced by caller, prefer Sandbox 2 Vertex ADC when present
if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_GENAI_USE_VERTEXAI:-}" ]]; then
  load_env_if_unset "/home/mcoreai/.config/mcore-vertex-master/vertex-master.env"
fi

export PYTHONPATH="/srv/mcore/shared:${PYTHONPATH:-}"
exec /home/mcoreai/mcore-isolated/venv/bin/python /srv/mcore/mcp-gemini-router/server.py "$@"
