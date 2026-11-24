# mcore-ai

Production Multi-Model Perspective Arena & Zero-Trust AI Gateway (`FastAPI` + `React/Vite` + `Nginx` + `Redis` + `Cloudflare Tunnel`).

## Architecture & Port Mapping
- **Public Edge**: Cloudflare Zero-Trust Tunnel (`QUIC`) -> `https://arena.<domain>`
- **Reverse Proxy**: Nginx (`127.0.0.1:18088 -> 80/tcp`)
- **API Gateway**: FastAPI (`backend:8000` internal)
- **Cache & State**: Redis 7.4 (`redis:6379` internal, password-protected)
