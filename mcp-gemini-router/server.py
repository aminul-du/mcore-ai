#!/usr/bin/env python3
"""
MCore AI FastMCP Tool Server (v2.0)
- Exposes Google Gemini 4 (Argon/Hydrogen + Pydantic Structured JSON + AFC Diagnostics),
  Groq LPU Inference, and Cloudflare Workers AI over MCP stdio & Streamable-HTTP (:18089).
- Strict stdout cleanliness for JSON-RPC stdio transport (all diagnostics log to stderr).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import logging
import os
import sys
from typing import Any, Dict, List, Literal, Optional, Type

sys.path.insert(0, "/srv/mcore/shared")

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from mcore_gemini_router import MCoreGeminiRouter

logging.basicConfig(
    level=logging.INFO,
    format="[mcore-gemini-mcp] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcore-gemini-mcp")


def _clean_secret(raw: Optional[str]) -> str:
    if not raw:
        return ""
    val = raw.strip().strip("\"'")
    return "" if val.startswith("replace_") else val


# --- Built-In Pydantic Schemas for Structured Extraction ---
class ArchitectureDecision(BaseModel):
    title: str = Field(description="Concise architectural decision title")
    recommended_stack: List[str] = Field(description="Ordered list of recommended technologies")
    risk_level: Literal["low", "medium", "high"]
    estimated_latency_ms: int = Field(description="Expected end-to-end latency in milliseconds")
    rationale: str = Field(description="Technical justification")


class SecurityAuditReport(BaseModel):
    target: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    vulnerabilities: List[str]
    mitigations: List[str]
    compliant: bool


class IncidentRCA(BaseModel):
    incident_summary: str
    root_cause: str
    affected_components: List[str]
    remediation_steps: List[str]
    preventive_action: str


class EntityExtraction(BaseModel):
    entities: List[Dict[str, str]] = Field(description="List of extracted items with name, type, and value keys")
    summary: str = Field(description="One-sentence summary of extracted entities")
    confidence: Literal["low", "medium", "high"]


SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "architecture_decision": ArchitectureDecision,
    "security_audit": SecurityAuditReport,
    "incident_rca": IncidentRCA,
    "entity_extraction": EntityExtraction,
}


# --- Deterministic #MCORE-NET-001 Diagnostic Tools ---
def lookup_mcore_service_port(service_name: str) -> Dict[str, Any]:
    """Looks up reserved loopback TCP ports in the #MCORE-NET-001 port registry."""
    ports = {
        "axum_mcp_bus": 8080,
        "arena_gateway": 18088,
        "gemini_mcp_http": 18089,
        "academy_web": 3000,
        "ais_profile": 3001,
        "eduverse": 3002,
        "fastapi_internal": 8000,
        "redis_internal": 6379,
    }
    key = service_name.strip().lower().replace("-", "_")
    if key in ports:
        return {"service": key, "bind": "127.0.0.1", "port": ports[key], "status": "reserved"}
    return {"service": key, "available_services": list(ports.keys()), "status": "unknown_service"}


def inspect_subnet_cidr(cidr: str) -> Dict[str, Any]:
    """Calculates network address, prefix length, and usable hosts for an IPv4 or IPv6 CIDR."""
    net = ipaddress.ip_network(cidr.strip(), strict=False)
    total = net.num_addresses
    usable = total if net.version == 6 or net.prefixlen >= 31 else max(0, total - 2)
    return {
        "cidr": str(net),
        "ip_version": f"IPv{net.version}",
        "network_address": str(net.network_address),
        "prefix_length": net.prefixlen,
        "usable_hosts": usable,
    }


def get_system_utc_clock() -> Dict[str, Any]:
    """Returns the current authoritative UTC ISO-8601 timestamp and Unix epoch seconds."""
    now = datetime.now(timezone.utc)
    return {"utc_iso": now.isoformat(), "unix_epoch": int(now.timestamp())}


DIAGNOSTIC_TOOLS = [lookup_mcore_service_port, inspect_subnet_cidr, get_system_utc_clock]

_router_instance: Optional[MCoreGeminiRouter] = None


def get_router() -> MCoreGeminiRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = MCoreGeminiRouter()
        logger.info(
            "Initialized MCoreGeminiRouter sandbox=%s argon=%s hydrogen=%s",
            _router_instance.profile.name,
            _router_instance.profile.argon_model,
            _router_instance.profile.hydrogen_model,
        )
    return _router_instance


async def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    system_instruction: str,
    temperature: float,
    max_tokens: int,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return json.dumps(data, indent=2)
        content = choices[0].get("message", {}).get("content")
        return content if content is not None else ""


def create_mcp_server(host: str = "127.0.0.1", port: int = 18089) -> FastMCP:
    mcp = FastMCP("mcore-gemini-router", host=host, port=port)

    @mcp.tool()
    def mcore_router_status() -> str:
        """Inspect active MCore Gemini sandbox credentials, Groq/Cloudflare readiness, and available schemas."""
        groq_ok = bool(_clean_secret(os.getenv("GROQ_API_KEY")))
        cf_ok = bool(_clean_secret(os.getenv("CLOUDFLARE_ACCOUNT_ID")) and _clean_secret(os.getenv("CLOUDFLARE_API_TOKEN")))
        try:
            r = get_router()
            info: Dict[str, Any] = {
                "status": "ready",
                "gemini_sandbox": r.profile.name,
                "vertexai": r.profile.use_vertexai,
                "project": r.profile.project,
                "location": r.profile.location,
                "api_version": r.profile.api_version,
                "argon_model": r.profile.argon_model,
                "hydrogen_model": r.profile.hydrogen_model,
                "groq_configured": groq_ok,
                "cloudflare_ai_configured": cf_ok,
                "available_schemas": list(SCHEMA_REGISTRY.keys()),
            }
        except Exception as exc:
            info = {
                "status": "gemini_unconfigured",
                "gemini_error": str(exc),
                "groq_configured": groq_ok,
                "cloudflare_ai_configured": cf_ok,
                "available_schemas": list(SCHEMA_REGISTRY.keys()),
            }
        return json.dumps(info, indent=2)

    @mcp.tool()
    async def ask_gemini_argon(
        prompt: str,
        system_instruction: str = "You are Gemini 4 Argon inside MCore AI. Provide precise, production-grade engineering analysis.",
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> str:
        """Query Gemini 4 Argon (gemini-4-argon) for deep architectural reasoning, code generation, and security analysis."""
        r = get_router()
        return await r.agenerate(
            prompt,
            tier="argon",
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    @mcp.tool()
    async def ask_gemini_hydrogen(
        prompt: str,
        system_instruction: str = "You are Gemini 4 Hydrogen inside MCore AI. Provide concise, high-speed, accurate responses.",
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> str:
        """Query Gemini 4 Hydrogen (gemini-4-hydrogen) for fast triage, classification, and low-latency summarization."""
        r = get_router()
        return await r.agenerate(
            prompt,
            tier="hydrogen",
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    @mcp.tool()
    async def ask_groq_lpu(
        prompt: str,
        model: str = "openai/gpt-oss-120b",
        system_instruction: str = "You are a high-speed engineering assistant running on Groq LPU. Provide concise, accurate, production-grade responses.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Query Groq LPU ultra-fast inference (e.g. openai/gpt-oss-120b, llama-3.1-8b-instant, qwen/qwen3-32b)."""
        api_key = _clean_secret(os.getenv("GROQ_API_KEY"))
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured. Run /home/mcoreai/configure-cf-groq-keys.sh first.")
        norm_model = model.split("/", 1)[1] if model.startswith("groq/") else model.strip()
        return await _call_openai_compatible(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=norm_model,
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @mcp.tool()
    async def ask_cloudflare_workers_ai(
        prompt: str,
        model: str = "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        system_instruction: str = "You are a concise, technical assistant running on Cloudflare Workers AI.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Query Cloudflare Workers AI serverless models (e.g. @cf/meta/llama-3.3-70b-instruct-fp8-fast, @cf/google/gemma-4-26b-a4b-it, @cf/openai/gpt-oss-120b)."""
        account_id = _clean_secret(os.getenv("CLOUDFLARE_ACCOUNT_ID"))
        api_token = _clean_secret(os.getenv("CLOUDFLARE_API_TOKEN"))
        if not account_id or not api_token:
            raise RuntimeError("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN is not configured. Run /home/mcoreai/configure-cf-groq-keys.sh first.")
        norm_model = f"@{model.strip()}" if model.strip().startswith("cf/") else model.strip()
        return await _call_openai_compatible(
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
            api_key=api_token,
            model=norm_model,
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @mcp.tool()
    async def extract_structured_json(
        prompt: str,
        schema_name: str = "architecture_decision",
        custom_json_schema: str = "",
        tier: Literal["argon", "hydrogen"] = "hydrogen",
        system_instruction: str = "Extract or synthesize data strictly conforming to the target JSON schema.",
    ) -> str:
        """Generate schema-validated JSON via Gemini 4. Use schema_name ('architecture_decision', 'security_audit', 'incident_rca', 'entity_extraction') or supply custom_json_schema."""
        r = get_router()
        if custom_json_schema.strip():
            schema_obj: Any = json.loads(custom_json_schema)
            result = await r.agenerate_structured(
                prompt,
                schema_obj,
                tier=tier,
                system_instruction=system_instruction,
            )
            return json.dumps(result, indent=2)

        schema_cls = SCHEMA_REGISTRY.get(schema_name.strip())
        if schema_cls is None:
            raise ValueError(f"Unknown schema_name '{schema_name}'. Valid options: {list(SCHEMA_REGISTRY.keys())}")
        parsed = await r.agenerate_structured(
            prompt,
            schema_cls,
            tier=tier,
            system_instruction=system_instruction,
        )
        return parsed.model_dump_json(indent=2)

    @mcp.tool()
    async def route_with_diagnostics(
        prompt: str,
        tier: Literal["argon", "hydrogen"] = "argon",
        enable_builtin_tools: bool = True,
    ) -> str:
        """Run Gemini 4 with automatic function calling over #MCORE-NET-001 port registry, CIDR calculator, and UTC clock tools."""
        r = get_router()
        if enable_builtin_tools:
            return await r.agenerate_with_tools(
                prompt,
                DIAGNOSTIC_TOOLS,
                tier=tier,
                automatic_function_calling=True,
            )
        return await r.agenerate(prompt, tier=tier)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="MCore Multi-Provider FastMCP Server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18089)
    args = parser.parse_args()

    server = create_mcp_server(host=args.host, port=args.port)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
