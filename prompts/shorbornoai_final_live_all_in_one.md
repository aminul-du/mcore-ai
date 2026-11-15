# FINAL ZERO-GAP PRODUCTION UPGRADE & LIVE END-TO-END LAUNCH: SHORBORNOAI v1.0.0
**Date & Baseline:** November 16, 2026 | Debian 13 (Trixie) Host (`113.11.1.161`)
**Workspaces:** `/srv/mcore` (Edge Worker & Next.js Web) & `/srv/shorborno-agent` (Python 3.14 LiveKit Daemon + Docker SFU)
**Execution Mode:** FULLY AUTONOMOUS / NON-INTERACTIVE (`yolo` mode). Do NOT pause or ask for confirmation. Execute every upgrade, firewall/port binding, Cloudflare Worker & Pages deployment, systemd restart, and live verification step sequentially until `evidence/final-verdict.json` is updated.

---

## STEP 1: LOCAL DEBIAN 13 RUNTIME & PACKAGE UPGRADES
1. **Verify & Upgrade Local Toolchains:**
   - Ensure `pnpm --version` is `11.28.11` (or latest `11.x` / `12.x` via ` @.cache/pnpm/v12/metadata/https:+registry.npmjs.org/@pnpm/exe.jsonl`).
   - Ensure `wrangler` inside `/srv/mcore/workers/sorborno-voice` and `/srv/mcore/apps/web` is updated to the latest `4.x` release (`pnpm up wrangler @latest`).
   - Inside `/srv/shorborno-agent/venv`, upgrade `livekit-agents`, `livekit-plugins-silero`, `aiohttp`, and `python-dotenv` to their latest compatible releases (`pip install --upgrade livekit-agents livekit-plugins-silero aiohttp python-dotenv`).
   - Pull the latest `livekit/livekit-server:latest` Docker image if a newer digest is available.

---

## STEP 2: SOVEREIGN LIVEKIT MEDIA PORTS & HOST FIREWALL HARDENING
1. **Enforce Host Networking / Full UDP Media Range (`50000-60000/udp` & `7881/tcp`):**
   - Inspect the running `livekit-server` Docker container (`docker inspect livekit-server`).
   - Because publishing 10,000 individual `-p` flags in Docker causes iptables/proxy slowdowns, ensure `livekit-server` runs with `--network host` (using `/srv/shorborno-agent/livekit.yaml` where `port: 7880`, `rtc.tcp_port: 7881`, `rtc.port_range_start: 50000`, `rtc.port_range_end: 60000`, and `rtc.use_external_ip: true`). Recreate the container with `--network host --restart always` if it is currently using bridge port mappings.
2. **Configure Host Firewall (`ufw`):**
   - If `ufw` is active (`sudo ufw status | grep -q "Status: active"`), allow `7881/tcp` and `50000:60000/udp` (`sudo ufw allow 7881/tcp && sudo ufw allow 50000:60000/udp && sudo ufw reload`).
   - Verify with `ss -tulpn | grep -E '7880|7881'` that `livekit-server` is bound directly to host TCP ports `7880` and `7881`.

---

## STEP 3: CLOUDFLARE EDGE WORKER & PAGES PRODUCTION UPGRADE + DEPLOYMENT
1. **Load Cloudflare Credentials:**
   - Source `CLOUDFLARE_API_TOKEN` from `/srv/mcore/apps/web/.env.local`.
2. **Upgrade & Deploy Edge AI Worker (`workers/sorborno-voice`):**
   - Inside `/srv/mcore/workers/sorborno-voice`, update `"compatibility_date": "2026-11-16"` in `wrangler.jsonc`, upgrade dependencies (`pnpm up`), verify TypeScript (`pnpm tsc --noEmit`), and execute a live production deployment (`npx wrangler deploy`).
   - Record the new Worker Version ID in `/srv/mcore/evidence/phase1-worker.json`.
3. **Upgrade, Build & Deploy Next.js Frontend (`apps/web`):**
   - Inside `/srv/mcore/apps/web`, run `pnpm up` (keeping React `19.2.6` and Next.js `16.4.6+` aligned with ` @cloudflare/next-on-pages`), run `pnpm audit --fix`, build (`pnpm run build && npx @cloudflare/next-on-pages`), and deploy live to Cloudflare Pages:
     `npx wrangler pages deploy .vercel/output/static --project-name=sorbornoai-web --branch=main`
   - Ensure both custom domains (`sorbornoai.com` and `shorbornoai.com`) are active on `sorbornoai-web` via the Cloudflare Pages API and record the live deployment URL in `/srv/mcore/evidence/phase3-pages.json`.

---

## STEP 4: RESTART DAEMON & EXECUTE LIVE END-TO-END VERIFICATION TRACE
1. **Restart Python Agent Daemon:**
   - Run `sudo systemctl restart shorborno-agent` and verify `systemctl is-active shorborno-agent` outputs `active` and `journalctl -u shorborno-agent -n 15` confirms `registered worker` against `wss://livekit.mcoreai.dev` with `0` key-length warnings.
2. **Live HTTP/2 & Token Issuance Smoke Tests:**
   - Test `curl -sS -I https://voice.sorbornoai.com` -> must return `HTTP/2 200`.
   - Test `curl -sS -I https://livekit.mcoreai.dev` -> must return `HTTP/2 200`.
   - Test `curl -sS -I https://sorbornoai.com` and `curl -sS -I https://shorbornoai.com` -> verify live edge HTTP status.
   - Test `curl -sS https://sorbornoai.com/api/livekit/token` -> verify a valid 3-part HS256 JWT (`eyJ...`) is minted.
3. **Final Supply-Chain Gate & Verdict:**
   - Run `syft dir:/srv/mcore -o cyclonedx-json > /srv/mcore/evidence/sbom.cdx.json` and `grype sbom:/srv/mcore/evidence/sbom.cdx.json --fail-on critical -o json > /srv/mcore/evidence/phase4-grype.json`.
   - Write the final verified JSON payload to `/srv/mcore/evidence/final-verdict.json` (`"verdict": "LIVE-PRODUCTION-COMPLETE"`, `"timestamp": "2026-11-16"`, `"critical_cves": 0`, `"udp_media_verified": true`) and display a concise summary table of all live URLs and service statuses.
