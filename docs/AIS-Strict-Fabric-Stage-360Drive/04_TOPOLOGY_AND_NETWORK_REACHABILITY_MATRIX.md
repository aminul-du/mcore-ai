---
id: MCORE-SPEC-006
title: Topology and Network Reachability Matrix
author_id: MCORE-FDR-AIS-001
status: verified
domain_scope: isolated-mcore
quantization_profile: L0-Lossless
last_reviewed: 2026-11-20
---

# 04. Topology and Network Reachability Matrix
**Document Authority:** MCORE-AIS-NET-004 (v1.1.0 Upgrade)  
**Owner:** Aminul Islam Shamim (AIS) | MCORE Architect Office  
**Verified Timestamp:** 2026-11-20T02:40:00Z  

---

## 1. Physical & Virtual Node Topology

```
+----------------------------------------------------------------------------------------------------+
|                                    CLOUDFLARE GLOBAL EDGE                                          |
|                                                                                                    |
|    library.mcoreai.cloud     research.mcoreai.com        sorbornoai.com     voice.sorbornoai.com   |
|         (DNS Proxied)            (Awaiting CNAME)         (CF Pages)            (Workers AI)       |
+--------------+------------------------+------------------------+---------------------+-------------+
               │                        │                        │                     │
      QUIC Tunnel (ais-pro)    QUIC Tunnel (ais-pro)             │                     │
               │                        │                        │                     │
+--------------v------------------------v---------------+        │                     │
|         GCP EDGE VM: ais-pro-edge                     |        │                     │
|         Zone: asia-east1-b | IP: 35.201.189.39        |        │                     │
|         Tunnel ID: fd5bd793-6d5f-45a3-9f7d-200009b12f25       │                     │
|                                                       |        │                     │
|    • Port 8000: library.mcoreai.cloud                 |        │                     │
|    • Port 3000: research.mcoreai.com                  |        │                     │
+-------------------------------------------------------+        │                     │
                                                                 │                     │
+-------------------------------------------------------+        │                     │
|      WINDOWS 11 WSL2 SOVEREIGN DUAL-DISTRO HOST       |◄───────┘                     │
|      Kernel: 6.18.58.1-microsoft-standard-WSL2        |                              │
|                                                       |                              │
|  +-------------------------------------------------+  |                              │
|  | Distro 1: Debian 13.7 (MCORE-FDR-AIS-001)       |  |                              │
|  | Root Namespace | Tunnel: ais001 (78d7fa3b-...)  |  |                              │
|  | • Port 3000: Workspace 360 Frontend             |◄─┼──────────────────────────────┘
|  | • Port 7860: MCORE Voice Console v0.6           |  |  (MeloTTS / LiveKit WebRTC)
|  | • Port 7880: LiveKit Signaling Server          |  |
|  | • Port 8000: API Policy Core                    |  |
|  | • Port 8100: Memory Trust Engine (MTE)          |  |
|  | • Port 8200: Terminal AI Server                 |  |
|  | • Port 8899: Jupyter Sovereign Lab              |  |
|  +-------------------------------------------------+  |
|                          │                            |
|             veth-mcore (Dynamic Routing)              |
|                          │                            |
|  +-----------------------v-------------------------+  |
|  | Distro 2: Ubuntu Pro 24.04 LTS (UbuntuPro)      |  |
|  | Network Namespace: mcore-ns                     |  |
|  | • WSL-devNet Automated Sandboxing               |  |
|  | • Isolated Port Spaces & IP Forwarding NAT      |  |
|  +-------------------------------------------------+  |
+-------------------------------------------------------+
```

---

## 2. Ingress & Routing Contracts

| Domain | Ingress Type | Target Service | Status | Action / Note |
| :--- | :--- | :--- | :--- | :--- |
| `library.mcoreai.cloud` | Argo Tunnel `ais-pro-tunnel` | `http://localhost:8000` | **ONLINE (HTTP 200)** | Injected with MCORE Audio Reading Toolbar |
| `research.mcoreai.com` | Argo Tunnel `ais-pro-tunnel` | `http://localhost:3000` | **AWAITING DNS** | Add CNAME in Cloudflare zone to `fd5bd793...cfargotunnel.com` |
| `sorbornoai.com` | Cloudflare Pages Custom Domain | `sorbornoai-web.pages.dev` | **ONLINE (HTTP 200)** | Next.js 16 WebRTC Voice Assistant |
| `voice.sorbornoai.com` | Cloudflare Workers AI Route | `sorborno-voice` worker | **ONLINE (HTTP 200)** | Sub-200ms STT + NLP + Bengali TTS |
| `livekit.mcoreai.dev` | Cloudflare Tunnel `ais001` | `http://localhost:7880` | **ONLINE (HTTP 200)** | Sovereign WebRTC Audio Transport |
| `ais.mcorecare.com` | Cloudflare Tunnel `ais001` | `http://localhost:7860` | **ONLINE (HTTP 200)** | Secured Voice Console Interface |

---

## 3. Work History Reconciliation Protocol

- **Debian 13:** Authoritative for sovereign code, git monorepo (`/srv/mcore`), model storage, and systemd services.
- **Ubuntu Pro 24.04:** Authoritative for network namespace operations (`WSL-devNet`), testing isolated subnets, and safe sandbox execution.
- **GCP Edge (`ais-pro-edge`):** Authoritative for public Cloudflare Argo termination and WAN ingress load-balancing.
