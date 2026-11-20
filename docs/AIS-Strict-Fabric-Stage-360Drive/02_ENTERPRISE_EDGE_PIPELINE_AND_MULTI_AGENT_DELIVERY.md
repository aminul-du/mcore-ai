---
id: MCORE-SPEC-004
title: Enterprise Edge Pipeline & Multi-Agent Delivery
author_id: MCORE-FDR-AIS-001
status: verified
domain_scope: isolated-mcore
quantization_profile: L0-Lossless
last_reviewed: 2026-11-20
---

# 02. Enterprise Edge Pipeline & Multi-Agent Delivery
**Document Authority:** MCORE-AIS-PIPE-002  
**Owner:** Aminul Islam Shamim (AIS) | MCORE Architect Office  
**Classification:** Enterprise Multi-Agent Operating Standard  

---

## 1. Master Capabilities for the `/AIS` Developer Ecosystem

The `/AIS` architecture operates as a **Developer-First Multi-Agent Platform** providing sovereign execution across 6 primary control tiers:

1. **L0 Transport & Edge Ingress:** Cloudflare QUIC Argo Tunnel (`cloudflared`), DNSSEC, Origin Shielding, and TLS 1.3 zero-trust perimeter.
2. **L1 WebRTC Real-Time Media:** LiveKit protocol streaming 24kHz bidirectional audio with sub-100ms packet delivery.
3. **L2 Sovereign Memory & Context Mesh:** Hybrid local SQLite vector index + Qdrant memory trust engine (MTE) enforcing prompt-injection isolation.
4. **L3 Speech & Perception (SHORBORNO):** Dual-engine STT/TTS supporting Bengali Dari (`।`, `॥`) punctuation, Silero VAD, and real-time DOM highlighting.
5. **L4 Agentic Reasoning:** LLaMA 3.3 70B FP8 Edge / Gemini CLI local subprocess with structured tool-calling.
6. **L5 Autonomic Control Plane:** Monorepo CI/CD, systemd daemon supervisory loops, and automated rollback health checks.

---

## 2. Multi-Agent Unified Multi-Surface Delivery (SHORBORNO & MCORE/AIS)

```
[Student / Engineer Surface]
   │
   ├─► Surface A: Web / Chrome Reading Mode (AudioControlToolbar - library.mcoreai.cloud)
   ├─► Surface B: Developer Workspace (Next.js 14 / Zustand - research.mcoreai.com / Workspace 360)
   ├─► Surface C: Terminal AI (FastAPI / Gemini CLI - Port 8200)
   └─► Surface D: Sovereign Voice Room (LiveKit WebRTC + Three.js 3D Core Canvas)
          │
          ▼
   [Unified Multi-Agent Routing Broker]
          │
          ├─► Agent A: Curriculum & Reading Guide (Sentence Chunker + Audio Sync)
          ├─► Agent B: Memory Trust Engine (Context Poisoning Detection)
          ├─► Agent C: Infra Control Plane (SSH IAM / Health Telemetry)
          └─► Agent D: Sovereign Bengalee Voice Agent (Shorborno Daemon)
```

---

## 3. Strict Boundary Workflows for Multi-Surface Agents

To ensure mathematical stability, agents follow strict operational boundaries:
- **Zero-Hallucination Fallback:** If confidence in localized Bengali synthesis or document retrieval falls below 0.82, the engine explicitly signals fallback to standard client Web Speech and cites exact source segments.
- **Non-Interfering Background Daemons:** Agentic background workers (`shorborno-agent`, `mte.server`) execute under systemd cgroups with memory limits (Max: 1.8GB) to guarantee zero interference with edge serving.
- **Contract-First Communication:** All inter-agent data exchanges use strongly-typed protobuf or JSON schemas validated against the Master Index.
