---
id: MCORE-SPEC-007
title: WSL2 Dual-Distro & Multi-Host Deduplication Matrix
author_id: MCORE-FDR-AIS-001
status: verified
domain_scope: isolated-mcore
quantization_profile: L0-Lossless
last_reviewed: 2026-11-20
---

# 06. WSL2 Dual-Distro & Multi-Host Deduplication Matrix
**Document Authority:** MCORE-AIS-DEDUP-006  
**Owner:** Aminul Islam Shamim (AIS) | MCORE Architect Office  
**Verified Platform:** Windows 11 WSL2 (Kernel 6.18.58.1-microsoft-standard-WSL2)  
**Distro Pair:** Debian 13.7 Trixie (`MCORE-FDR-AIS-001`) + Ubuntu Pro 24.04.5 LTS Noble (`UbuntuPro`)  
**GCP Edge Node:** `ais-pro-edge` (Zone: `asia-east1-b` | IP: `35.201.189.39`)  

---

## 1. Verified Multi-Host Execution Matrix

| Boundary Dimension | Debian 13 (Trixie) — Sovereign Host | Ubuntu Pro (24.04) — NetOps & DevSec | GCP Edge VM (`ais-pro-edge`) |
| :--- | :--- | :--- | :--- |
| **Primary Role** | Core Sovereign Intelligence & Workspace | Network Namespaces & Isolated Sandbox | High-Availability Public Ingress Gateway |
| **Network Context** | Root Namespace (Port space `0.0.0.0`) | `mcore-ns` Virtual Ethernet (`veth-mcore`) | Dedicated GCP VPC / Public IPv4 (`35.201.189.39`) |
| **Active Ingress Tunnel** | Tunnel `ais001` (`78d7fa3b-...`) | None (Internal routing / NAT forward) | Argo Tunnel `ais-pro-tunnel` (`fd5bd793-...`) |
| **Ports Managed** | `3000` (Workspace 360), `7860` (Voice Console), `7880` (LiveKit), `8000` (FastAPI), `8100` (MTE), `8200` (Terminal AI), `8899` (Jupyter) | Isolated Ephemeral Container Ports | `8000` (`library.mcoreai.cloud`), `3000` (`research.mcoreai.com`) |
| **Runtime & Node** | Node v20/v22 / Python 3.14 (systemd) | Node v24.22.3 (NVM) / Python 3.12 | Docker Engine / `cloudflared` Daemon |
| **Model Storage** | `/srv/mcore/apps/voice-console/models` (Single Source of Truth) | Read-only Bind Mount / Zero Duplicate Weights | Ephemeral Cache / Cloudflare Workers AI offload |

---

## 2. Enforced Deduplication Rules

1. **Port Binding Invariant:**
   - Because WSL2 shares virtual adapter bindings when not inside an isolated network namespace, `UbuntuPro` must **never** run background services binding to ports `3000`, `7860`, `7880`, `8000`, `8100`, or `8200` in its root namespace.
   - Any experimental services in `UbuntuPro` must execute strictly within the `mcore-ns` namespace using `ip netns exec mcore-ns <command>`.

2. **Model Weights & Cache Deduplication:**
   - Hugging Face cache (`~/.cache/huggingface`) and CTranslate2 models (`models/bangla-asr-ct2`) are centralized on `Debian13`.
   - `UbuntuPro` and containerized runtimes access these assets via `/mnt/wsl/` shared volume or bind mounts. Duplicate downloads are blocked.

3. **Cloudflare Argo Tunnel Deduplication:**
   - Tunnel `ais001` (ID: `78d7fa3b-c30b-44eb-a474-d3d0aa2d963d`) is owned exclusively by `Debian13`.
   - Tunnel `ais-pro-tunnel` (ID: `fd5bd793-6d5f-45a3-9f7d-200009b12f25`) is owned exclusively by GCP Edge VM `ais-pro-edge`.
   - Both tunnels use distinct ingress credential files to prevent connection hijacking or edge flappiness.

4. **Task Ledger Single Source of Truth:**
   - All active agentic and human tasks must be registered in `/srv/mcore/evidence/task-ledger.yaml` before execution.
   - Interactive Gemini CLI sessions on `UbuntuPro` must consult `task-ledger.yaml` prior to initiating code modifications.

---

## 3. Automated Deduplication Validation Script (`validate_deduplication.sh`)

```bash
#!/usr/bin/env bash
# MCORE Deduplication Validator
set -euo pipefail

echo "=== [1/3] Checking Port Conflicts on Shared WSL2 Host ==="
CONFLICTING_PORTS=(3000 7860 7880 8000 8100 8200)
for port in "${CONFLICTING_PORTS[@]}"; do
  COUNT=$(ss -tulpn | grep -c ":${port} " || true)
  if [[ "$COUNT" -gt 1 ]]; then
    echo "⚠️ WARNING: Multiple listeners detected on port ${port}!"
  else
    echo "✅ Port ${port}: Clean (Single owner)"
  fi
done

echo "=== [2/3] Checking Cloudflared Tunnel Isolation ==="
RUNNING_TUNNELS=$(ps aux | grep -c "[c]loudflared tunnel" || true)
echo "Active local cloudflared tunnels on Debian 13: ${RUNNING_TUNNELS}"

echo "=== [3/3] Checking Shared Model Weights Footprint ==="
if [[ -d "/srv/mcore/apps/voice-console/models" ]]; then
  echo "✅ Canonical models directory verified at /srv/mcore/apps/voice-console/models"
fi
```
