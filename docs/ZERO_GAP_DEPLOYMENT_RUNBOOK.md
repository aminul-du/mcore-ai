# SHORBORNOAI v1.0.0 — AUTOMATED END-TO-END DEPLOYMENT RUNBOOK
**Classification:** Standard Operating Procedure (SOP-DEPLOY-001)  
**Execution Mode:** Fully Autonomous / Zero Manual Steps Required  
**Author:** Aminul Islam Shamim (AIS) | `MCORE-FDR-AIS-001`  

---

## 1. PRE-REQUISITES & ENVIRONMENT DISCOVERY
Run on target host:
```bash
node --version
pnpm --version
python3 --version
docker --version
cloudflared --version

export CLOUDFLARE_ACCOUNT_ID="41903f4febb2c66dffd4ffcae558e692"
export CLOUDFLARE_API_TOKEN=$(grep -E '^oauth_token' ~/.wrangler/config/default.toml | awk -F'=' '{print $2}' | tr -d ' "' | tr -d ' ')
```

---

## 2. AUTOMATED BUILD & CLOUDFLARE DEPLOYMENT
Execute the single master automated script:
```bash
bash /srv/mcore/scripts/cf-e2e-deploy.sh
```

### Script Execution Logic Breakdown:
1. **DNS & Edge Route Synchronization:**
   - Attaches `sorbornoai.com`, `www.sorbornoai.com`, `shorbornoai.com`, and `www.shorbornoai.com` to Cloudflare Pages.
   - Enforces Edge Worker routes on `sorbornoai.com/*` pointing to `sorborno-voice`, bypassing historical Cloudflare Error 522 origin timeouts.
2. **Next.js Web Frontend & Token API Build:**
   - Navigates to `/srv/mcore/apps/web`.
   - Executes `pnpm run build && npx @cloudflare/next-on-pages`.
   - Deploys static build and Edge Functions bundle via `npx wrangler pages deploy .vercel/output/static --project-name=sorbornoai-web --branch=main`.
3. **Edge Voice AI Worker Deployment:**
   - Navigates to `/srv/mcore/workers/sorborno-voice`.
   - Executes `npx wrangler deploy` with bindings:
     - `env.AI`: Cloudflare Workers AI
     - `env.RATE_LIMITER`: Client IP rate limiter (10 req / 10s)
     - Custom domains: `voice.sorbornoai.com`, `shorbornoai.com`, `www.shorbornoai.com`
     - Zone routes: `sorbornoai.com/*`, `www.sorbornoai.com/*`
4. **Local Daemon & Media Port Verification:**
   - Restarts and verifies systemd units: `cloudflared.service` and `shorborno-agent.service`.
   - Checks TCP port `7880` / `7881` binding for `livekit-server`.
5. **Live Verification Probe:**
   - Queries `https://sorbornoai.com`, `https://shorbornoai.com`, `https://voice.sorbornoai.com`, and `/api/livekit/token`.
   - Writes verification matrix to `/srv/mcore/evidence/deploy-summary-report.md`.

---

## 3. PLAYWRIGHT BROWSER E2E TEST VERIFICATION
Execute the automated Playwright browser test to verify 3D UI, LiveKit WebRTC signaling, and token minting:
```bash
/srv/mcore/venv/bin/python3 /srv/mcore/scripts/browser-e2e-verify.py
```
Expected output:
```json
{
  "token_api_status": 200,
  "webrtc_connected": true,
  "canvas_rendered": true,
  "status": "PASS"
}
```

---

## 4. AUDIT & DISASTER RECOVERY VALIDATION
1. **Supply-Chain SBOM:**
   `syft dir:/srv/mcore -o cyclonedx-json > /srv/mcore/evidence/sbom.cdx.json`
2. **Vulnerability Scan:**
   `grype sbom:/srv/mcore/evidence/sbom.cdx.json --fail-on critical -o json > /srv/mcore/evidence/phase4-grype.json`
3. **Evidence Archival:**
   Verify `/srv/mcore/evidence/final-verdict.json` and `/srv/mcore/evidence/deploy-summary-report.md` are updated.
4. **Git Sync:**
   `git -C /srv/mcore commit -a -m "release: zero-gap live deployment verified [MCORE-FDR-AIS-001]"`
   `git -C /srv/mcore push origin main`
