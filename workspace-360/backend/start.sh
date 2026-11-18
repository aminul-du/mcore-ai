#!/usr/bin/env bash
set -e
export MCORE_WHISPER_MODEL="/srv/mcore/apps/voice-console/models/bangla-asr-ct2"
export HF_HUB_OFFLINE="1"
export HF_HOME="/srv/mcore/apps/voice-console/.cache"
cd /srv/mcore/workspace-360/backend
source .venv-3.13/bin/activate
exec uvicorn app.main:app --host 127.0.0.1 --port 3001
