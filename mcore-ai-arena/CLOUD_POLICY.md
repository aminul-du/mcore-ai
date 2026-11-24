# MCore AI Cloud & Zero-Trust Policy

1. **Zero Inbound Exposure**: Host firewall blocks all inbound public ports; ingress flows exclusively through outbound authenticated Cloudflare Tunnel (`ee70463d-b74c-4f11-b2ef-3280f04068b0`).
2. **Least-Privilege Runtime**: Backend executes as unprivileged `appuser` inside an isolated Docker bridge network (`mcore_internal`).
3. **Secret Hygiene**: All provider keys (`GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `CLOUDFLARE_TUNNEL_TOKEN`) are stored strictly in `chmod 600 .env` and excluded from VCS.
4. **Resilient Degradation**: Unconfigured upstream providers enter `[Standby]` state without impacting active inference routes or Redis cache hits.
