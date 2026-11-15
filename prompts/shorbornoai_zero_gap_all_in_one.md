# AUTONOMOUS ZERO-GAP EXECUTION DIRECTIVE: SHORBORNOAI v1.0.0 END-TO-END
**Target Date & Baseline:** November 15, 2026 | Debian 13 (Trixie) Host
**GCP / Vertex AI Context:** Project `project-12884862-2ba9-4048-b03`
**Workspaces:** `/srv/mcore` (Monorepo: Cloudflare Workers + Next.js Web) & `/srv/shorborno-agent` (Python 3.14 LiveKit/VAD Service)
**Execution Mode:** FULLY AUTONOMOUS / HEADLESS / ZERO-PROMPT. Do NOT pause for confirmation. Execute all shell commands, file writes, builds, systemd registrations, Cloudflare deployments, and health verifications sequentially until `evidence/final-verdict.json` is written.

---

## PHASE 0: NOVEMBER 15, 2026 ZERO-GAP TOOLCHAIN & PRE-FLIGHT GATES
Inspect the local Debian 13 host and enforce these exact baselines. Automatically install or upgrade any missing component before proceeding:
1. **Python Runtime:** `Python 3.14.9+` (or `3.14.10+`) with free-threaded / low-GIL support verified for `/srv/shorborno-agent/venv`.
2. **Node.js & Package Manager:** `Node.js v26.13.0+` (Active LTS "Lithium") and `pnpm 11.x` (Node 20/24 or npm/yarn are strictly blocked).
3. **Systems Telemetry Runtime:** `Rust 1.98.1+` stable (`rustc` & `cargo` for Quickview Engine integration).
4. **Database & Vector Store:** `PostgreSQL 17` with `pgvector 0.8.6+` extension active.
5. **Supply-Chain & Attestation Binaries:**
   - `cosign >= v3.1.4`
   - `syft >= v1.51.0`
   - `grype >= v0.88.0` (Schema v6 mandatory; schema v5 is EOL)
   - `trivy == v0.69.3` (Verify SHA256 binary digest strictly; block unverified tags >= v0.69.4)
6. **Gate Output:** Write verified versions, binary paths, and SHA digests to `/srv/mcore/evidence/phase0-toolchain.json`.

---

## PHASE 1: CLOUDFLARE EDGE AI WORKER (`workers/sorborno-voice`)
1. Create/update `/srv/mcore/workers/sorborno-voice/wrangler.jsonc`:
   - Set `"compatibility_date": "2026-11-15"` and `"compatibility_flags": ["nodejs_compat"]`.
   - Bind custom domain route: `voice.sorbornoai.com`.
   - Bind Workers AI (`"binding": "AI"`), Analytics Engine (`"dataset": "sorborno_ai_telemetry"`), and IP rate-limiting (`10 requests / 10s`).
2. Implement `/srv/mcore/workers/sorborno-voice/src/index.ts` (Hono + TypeScript):
   - **Security Guard:** Enforce a 32KB max audio payload limit and strip prompt-injection control sequences before inference.
   - **Stage 1 (STT):** `@cf/openai/whisper-large-v3-turbo` tuned for Bengali (`bn`) audio frames.
   - **Stage 2 (NLP):** `@cf/meta/llama-3.3-70b-instruct-fp8-fast` with a strict system prompt enforcing natural, concise Bengali responses.
   - **Stage 3 (TTS):** `@cf/myshell-ai/melotts` returning 24kHz mono WAV audio encoded as Base64 alongside `userText`, `aiText`, and stage latency metrics (`sttMs`, `nlpMs`, `ttsMs`).
3. Run typecheck (`pnpm tsc --noEmit`) and deploy live via `npx wrangler deploy`. Record deployment URL and Worker version ID in `/srv/mcore/evidence/phase1-worker.json`.

---

## PHASE 2: PYTHON 3.14 LIVEKIT & SILERO VAD DAEMON (`/srv/shorborno-agent`)
1. Provision an isolated Python 3.14 virtual environment:
   ```bash
   mkdir -p /srv/shorborno-agent
   python3.14 -m venv /srv/shorborno-agent/venv
   /srv/shorborno-agent/venv/bin/pip install --upgrade pip livekit-agents livekit-plugins-silero aiohttp python-dotenv
   ```