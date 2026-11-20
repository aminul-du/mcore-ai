# ShorbornoAI - Cloudflare Workers AI Local Development

## Preferred architecture

Use Wrangler local development with a remote Workers AI binding.

Existing Worker binding:
AI

Recommended development configuration:

{
  "ai": {
    "binding": "AI",
    "remote": true
  }
}

Keep the existing production configuration unchanged until
AIS approves the configuration change.

## Local execution

From the existing Worker directory:

pnpm exec wrangler dev

The Worker executes locally while the AI binding accesses
Cloudflare's remote Workers AI service.

## Important

- Remote AI inference can incur usage charges.
- Do not put Cloudflare tokens in frontend code.
- Do not commit credentials.
- Do not expose secrets through logs.
- Do not change production routes during local testing.
- Do not perform inference automatically during infrastructure audit.

## Alternative

A backend-only application can use the Workers AI REST API
with Account ID and a dedicated Workers AI API token.

This is an external API workflow and should be separately
approved for usage and cost.
