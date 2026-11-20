---
id: MCORE-SPEC-000
title: AIS-PRO Strict Fabric Stage-360Drive Overview
author_id: MCORE-FDR-AIS-001
status: verified
domain_scope: isolated-mcore
quantization_profile: L0-Lossless
last_reviewed: 2026-11-20
---

# AIS-PRO: Strict Fabric Stage-360Drive
**Sovereign Multi-Surface AI Infrastructure, Dual-Distro WSL2 & Edge Ecosystem**  
**Lead Architect:** Aminul Islam Shamim (AIS) | `MCORE-FDR-AIS-001`  
**Ecosystem:** MCORE / ShorbornoAI / AIS  

---

## Repository Overview

This repository establishes the definitive control plane and multiplatform edge inference specification for the **MCORE / ShorbornoAI / AIS** ecosystem.

### Included Specifications

1. [`01_MULTI_SURFACE_EDGE_ARCHITECTURE_SPEC.md`](01_MULTI_SURFACE_EDGE_ARCHITECTURE_SPEC.md): Comprehensive evaluation of vendor-native engines (ExecuTorch, Kotlin Multiplatform, ONNX Runtime, Google AICore) vs. Cloudflare Workers.
2. [`02_ENTERPRISE_EDGE_PIPELINE_AND_MULTI_AGENT_DELIVERY.md`](02_ENTERPRISE_EDGE_PIPELINE_AND_MULTI_AGENT_DELIVERY.md): Master capabilities for developer-first AI, enterprise multi-agent pipelines, and strict boundary workflows.
3. [`03_STRATEGIC_ROADMAP_AGI_2026_2050.md`](03_STRATEGIC_ROADMAP_AGI_2026_2050.md): Roadmap spanning Foundation (2026–2030), Multi-Agent Networks (2029–2035), Neuromorphic Edge (2036–2042), and Distributed Sovereign AGI (2043–2050).
4. [`04_TOPOLOGY_AND_NETWORK_REACHABILITY_MATRIX.md`](04_TOPOLOGY_AND_NETWORK_REACHABILITY_MATRIX.md): Exact verified network topology connecting GCP Edge VM (`ais-pro-edge`, `35.201.189.39`), Cloudflare Argo Tunnel (`fd5bd793...`), and Sovereign Bare-Metal host (`mcorebd`).
5. [`05_QUANTIZED_MODEL_AND_ASSET_MANIFEST.yaml`](05_QUANTIZED_MODEL_AND_ASSET_MANIFEST.yaml): Concrete quantization recipes (INT4/INT8/CT2/PTE) for speech and LLMs.
6. [`06_WSL2_DUAL_DISTRO_DEDUPLICATION_MATRIX.md`](06_WSL2_DUAL_DISTRO_DEDUPLICATION_MATRIX.md): Detailed operational rules, network namespace boundaries, and automated validation for Debian 13 and Ubuntu Pro 24.04 under WSL2.

---

## Verified Infrastructure Topology

- **Edge Ingress:** Cloudflare Argo Tunnel (`ais-pro-tunnel` ID: `fd5bd793-6d5f-45a3-9f7d-200009b12f25`)
- **GCP Edge Node:** `ais-pro-edge` (`35.201.189.39`, Zone: `asia-east1-b`)
- **Host Architecture:** Windows 11 WSL2 Kernel 6.18 (Debian 13.7 Trixie + Ubuntu Pro 24.04 LTS Noble)
- **Live Library URL:** [https://library.mcoreai.cloud](https://library.mcoreai.cloud) (Port 8000)
- **Live Web Assistant:** [https://sorbornoai.com](https://sorbornoai.com) (Cloudflare Pages)
- **Local Workspace:** [http://localhost:3000](http://localhost:3000) (Next.js Workspace 360)
