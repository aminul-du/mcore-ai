# MCORE AIS/BOX-1.0 & SHORBORNOAI v1.0.0 — COMPREHENSIVE PROJECT GAP AUDIT
**Date of Audit:** November 17, 2026  
**Auditor / Authority:** Aminul Islam Shamim (AIS) | `MCORE-FDR-AIS-001`  
**Host Target:** Debian 13 (Trixie) Bare-Metal Node (`113.11.1.161` / `MCORE-FDR-AIS-001`)  
**Repository:** `git@github.com:aminul-du/mcoreai.git` (`main`)  
**Classification:** Sovereign Autonomous Intelligence Infrastructure (SAII 2050 Baseline)

---

## 1. EXECUTIVE SUMMARY & VERDICT
An end-to-end architectural, security, operational, and supply-chain audit was conducted on the ShorbornoAI and MCORE ecosystem. 
The live deployment verification confirms:
- **Public Edge Endpoints:** `https://sorbornoai.com` (200), `https://shorbornoai.com` (200), `https://voice.sorbornoai.com` (200), and `/api/livekit/token` (200) are fully operational.
- **Sovereign Bare-Metal Compute:** Local LiveKit SFU (Docker host-mode on port 7880/7881, UDP 50000-60000), Cloudflared QUIC Tunnel (`ais001`), and Python 3.14 `shorborno-agent` are active.
- **Cost Efficiency:** Running at **$0.00/month** on Cloudflare Free Tier and bare-metal compute.
- **Identified Gaps:** A total of **18 Architectural Gaps across the 18 SAII Planes** and **4 Gate Gaps across the 9 Sovereign Gates (G0-G8)** were identified and cataloged below with remediation targets.

---

## 2. NINE SOVEREIGN GATES (G0 - G8) VALIDATION MATRIX

| Gate | Title | Target Scope | Current Status | Finding & Action Item |
| :--- | :--- | :--- | :--- | :--- |
| **G0** | Architecture Alignment | 18 SAII Planes & AIS/BOX-1.0 | **PASSED** | Formally documented in `ARCHITECTURE.md` and `GEMINI.md`. |
| **G1** | Security Review & CVEs | Zero Critical CVEs | **CONDITIONAL PASS** | 0 Critical CVEs confirmed. **GAP:** 8 High CVEs in `python-multipart`, `postcss`, and `sharp`. |
| **G2** | Static Code & Policy | Linting, Types, Policy Registry | **PASSED** | TypeScript verification clean (`tsc --noEmit` 0 errors on web & worker). |
| **G3** | Empirical Execution | LiveKit WebRTC & 3D Canvas | **PASSED** | Playwright E2E browser test verified WebRTC state `connecting -> connected` (15.49s) and canvas rendering. |
| **G4** | Trust & Provenance | Trust Scoring & Attestation | **GAP** | `trust-attestation.json` not dynamically generated per voice session. Target: Q1 2027. |
| **G5** | Verification & SBOM | CycloneDX SBOM & Signatures | **PARTIAL** | `sbom.cdx.json` generated. **GAP:** Cosign keyless cryptographic signing not integrated into CI. |
| **G6** | Disaster Recovery | Runbooks & Automated Backups | **GAP** | Recovery runbooks documented, but continuous Cloudflare R2 backup cron is pending implementation. |
| **G7** | Observability Plane | Metrics, OTel, Alerting | **PARTIAL** | Systemd and Playwright metrics active. **GAP:** Prometheus Alertmanager webhook alerting missing. |
| **G8** | Production Authorization | Human Authority Sign-Off | **APPROVED** | Explicit authorization by Founder AIS (`MCORE-FDR-AIS-001`). |

---

## 3. DETAILED 18 SAII ARCHITECTURAL PLANES GAP AUDIT

### Plane 1: Data Plane
- **Current Baseline:** Local PostgreSQL 16 container (`aaa-postgres`), Redis 7 container (`aaa-redis`), and Qdrant vector DB.
- **Identified Gap:** Lack of continuous automated streaming replication and off-site encrypted snapshot synchronization to Cloudflare R2 storage.
- **Risk Level:** Medium (Data loss in case of physical disk failure).
- **Remediation:** Implement automated systemd timer running encrypted `pg_dump` with SOPS + Cloudflare S3 API upload.

### Plane 2: Control Plane
- **Current Baseline:** NativeBox orchestration scripts (`cf-e2e-deploy.sh`, `setup_master_devops_deploy.sh`) and systemd services.
- **Identified Gap:** Control plane logic is imperative bash; lacks declarative OpenTofu reconciliation loop.
- **Risk Level:** Low.
- **Remediation:** Package infrastructure into declarative OpenTofu modules for drift detection.

### Plane 3: Security Plane
- **Current Baseline:** Grype vulnerability audit (`phase4-grype.json`), CycloneDX SBOM (`sbom.cdx.json`), UFW firewall rules.
- **Identified Gap:** 8 High-severity CVEs in project dependency trees:
  - `python-multipart@0.0.20`: GHSA-wp53-j4wj-2cfg, GHSA-pp6c-gr5w-3c5g, GHSA-5rvq-cxj2-64vf
  - `postcss@8.4.31`: GHSA-6g55-p6wh-862q, GHSA-r28c-9q8g-f849
  - `sharp@0.33.5`: GHSA-f88m-g3jw-g9cj, GHSA-rgj7-g3m4-5g8c, GHSA-wq5f-xc86-pv6w
- **Risk Level:** High (Supply chain attack surface).
- **Remediation:** Bump `python-multipart >= 0.0.21`, update `postcss` and `sharp` in `apps/web`.

### Plane 4: Identity Plane
- **Current Baseline:** LiveKit HS256 JWT minting (`/api/livekit/token`), Cloudflare Zero Trust Tunnel authentication.
- **Identified Gap:** SPIFFE/SPIRE workload attestation daemon not deployed on host. Internal microservices do not use cryptographic SPIFFE IDs (`spiffe://mcoreai.dev/agent/voice`).
- **Risk Level:** Medium.
- **Remediation:** Deploy SPIRE agent container on NativeBox bare-metal node (GAP-001).

### Plane 5: Intelligence Plane
- **Current Baseline:** Cloudflare Workers AI (`whisper-large-v3-turbo`, `llama-3.3-70b-instruct`, `melotts`) and host CTranslate2 BanglaASR.
- **Identified Gap:** No automatic edge-to-local fallback circuit breaker if Cloudflare Workers AI exceeds latency thresholds (>1500ms).
- **Risk Level:** Medium.
- **Remediation:** Add fallback route in `sorborno-voice` Worker to route audio to local host endpoint via Cloudflare Tunnel on timeout.

### Plane 6: Memory Plane (Core IP)
- **Current Baseline:** Qdrant vector engine deployed; basic session state storage.
- **Identified Gap:** The Predictive Memory Security Layer (Poisoning Detection Engine & Memory Trust Engine) is not yet inline with the live voice audio turn pipeline.
- **Risk Level:** High (Core research IP integration milestone).
- **Remediation:** Route recognized user transcript through `mcoresec-mte` (Memory Trust Engine port 8000) prior to LLM response generation.

### Plane 7: Knowledge Plane
- **Current Baseline:** Academic research files in `AIS-DU-PMICS-PROJECT-SBOX` and Markdown knowledge base.
- **Identified Gap:** Deterministic knowledge graph is static; no automated ingestion of Bengali voice conversation entities.
- **Risk Level:** Low.
- **Remediation:** Implement post-session entity extraction worker populating vector and graph stores.

### Plane 8: Observability Plane
- **Current Baseline:** Playwright E2E browser metric logging, systemd journal logs.
- **Identified Gap:** LiveKit WebRTC packet loss, audio frame jitter, and STT/TTS latency metrics are not scraped into a unified Prometheus/Grafana dashboard.
- **Risk Level:** Medium.
- **Remediation:** Expose LiveKit Prometheus telemetry endpoint (`:7880/metrics`) to local Prometheus instance.

### Plane 9: Governance Plane
- **Current Baseline:** 9-Gate policy model, authority model, and verifiable JSON outputs.
- **Identified Gap:** Deployments can be manually executed without CI/CD pipeline enforcing Gate G1-G7 checks automatically.
- **Risk Level:** Medium.
- **Remediation:** Create GitHub Actions workflow executing full gate check suite on every pull request.

### Plane 10: Verification Plane
- **Current Baseline:** Evidence files (`evidence.json`, `final-verdict.json`, `browser-e2e-verdict.json`, `deploy-summary-report.md`).
- **Identified Gap:** Verification JSON payloads and container artifacts are not cryptographically signed with Cosign keyless signatures.
- **Risk Level:** Medium.
- **Remediation:** Add `cosign sign-blob` step to `cf-e2e-deploy.sh`.

### Plane 11: Trust Plane
- **Current Baseline:** Attestation records locked to Founder ID `MCORE-FDR-AIS-001`.
- **Identified Gap:** Trust scoring engine (`trust-attestation.json`) not yet emitting real-time confidence scores per audio turn.
- **Risk Level:** Medium.
- **Remediation:** Connect `trust-engine/trust_scorer.py` into voice agent feedback loop.

### Plane 12: Safety Plane
- **Current Baseline:** Rate limiting (10 req/10s), 32KB payload guard, prompt injection regex sanitization.
- **Identified Gap:** No emergency WebRTC kill-switch endpoint accessible via secure management token.
- **Risk Level:** Medium.
- **Remediation:** Expose `/api/v1/safety/kill-switch` on `sorborno-voice` protected by Cloudflare Access service token.

### Plane 13: Ethics Plane
- **Current Baseline:** Bengali ethical alignment instructions embedded in system prompt.
- **Identified Gap:** Lacks dedicated lightweight classifier model for toxic/harmful Bengali language detection.
- **Risk Level:** Low.
- **Remediation:** Fine-tune or deploy quantized Bengali toxicity classifier in agent pipeline.

### Plane 14: Sovereignty Plane
- **Current Baseline:** 100% open-source bare-metal runtime, zero cloud lock-in, zero monthly vendor spend.
- **Identified Gap:** Hardcoded external IP (`113.11.1.161`) in `livekit.yaml` requires manual intervention if ISP DHCP reallocates IP.
- **Risk Level:** Medium.
- **Remediation:** Deploy DDNS / dynamic IP discovery hook that reconfigures `livekit.yaml` and signals `livekit-server` reload.

### Plane 15: Simulation Plane
- **Current Baseline:** Playwright browser test (`browser-e2e-verify.py`) running headless WebRTC simulation.
- **Identified Gap:** No automated adversarial audio injection suite testing model resistance to ultrasonic or adversarial noise.
- **Risk Level:** Low.
- **Remediation:** Build audio adversarial test harness in `tests/simulation/`.

### Plane 16: Evolution Plane
- **Current Baseline:** Pinning compatibility dates and model tags in `wrangler.jsonc`.
- **Identified Gap:** Lack of continuous automated evaluation dataset benchmarking Bengali WER (Word Error Rate) across versions.
- **Risk Level:** Low.
- **Remediation:** Build automated CommonVoice Bengali benchmark evaluation script.

### Plane 17: Deployment Plane
- **Current Baseline:** `cf-e2e-deploy.sh` script deploying Pages and Worker triggers with automatic credential resolution.
- **Identified Gap:** GitOps pull-based daemon absent; deployments require active operator invocation.
- **Risk Level:** Low.
- **Remediation:** Implement GitHub Webhook receiver or lightweight GitOps poller.

### Plane 18: Operations Plane
- **Current Baseline:** Runbooks 01-10 documented in `MCoreNativeEngine/runbooks/`, systemd unit auto-restart.
- **Identified Gap:** Disaster recovery drill (Runbook 10) not verified on standby secondary node.
- **Risk Level:** Low.
- **Remediation:** Conduct quarterly bare-metal recovery drill into isolated sandbox container.

---

## 4. PRIORITIZED REMEDIATION ROADMAP

| Priority | Plane / Gate | Gap Description | Action Plan | Target Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | Security Plane (G1) | 8 High-severity CVEs in dependencies | Upgrade `python-multipart`, `postcss`, and `sharp` | Immediate (Milestone 1.1) |
| **P0** | Memory Plane (G4) | Predictive Memory Security inline engine | Wire `mcoresec-mte` into voice agent pipeline | Immediate (Milestone 1.2) |
| **P1** | Identity Plane (G2) | SPIFFE/SPIRE Workload Attestation | Deploy SPIRE container on NativeBox host | Milestone 2.0 |
| **P1** | Sovereignty Plane | Dynamic IP binding for LiveKit | Implement automated DDNS external IP discovery | Milestone 2.1 |
| **P1** | Observability Plane (G7) | Prometheus metrics & Alertmanager | Scrape LiveKit `:7880/metrics` into Grafana | Milestone 2.2 |
| **P2** | Verification Plane (G5) | Cosign Cryptographic Artifact Signing | Embed Cosign sign-blob in release pipeline | Milestone 3.0 |
| **P2** | Operations Plane (G6) | Automated S3/R2 Backup Cron | Implement SOPS-encrypted database snapshot cron | Milestone 3.1 |

---

## 5. EVIDENCE METRICS & AUDIT ATTESTATION
- **Total Planes Audited:** 18 / 18
- **Total Gates Validated:** 9 / 9 (G0 to G8)
- **Active Operational Endpoints:** 4 / 4 (`sorbornoai.com`, `shorbornoai.com`, `voice.sorbornoai.com`, `/api/livekit/token`)
- **System Service Health:** 100% (`cloudflared`, `shorborno-agent`, `livekit-server` active)
- **Zero-Cost Compliance:** Confirmed ($0.00/month recurring cost)
- **Attestation Hash:** Generated and committed to repository evidence registry.
