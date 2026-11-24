#!/usr/bin/env python3
from __future__ import annotations
import json, os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterator, Literal, Optional, Sequence, Type, TypeVar, Union
import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel

SandboxMode = Literal["auto", "sandbox1", "sandbox2"]
ModelTier = Literal["argon", "hydrogen"]
SchemaT = TypeVar("SchemaT", bound=BaseModel)

def _clean_secret(raw: Optional[str]) -> str:
    if not raw:
        return ""
    val = raw.strip().strip("\"'")
    return "" if val.startswith("replace_") else val

@dataclass(frozen=True)
class SandboxProfile:
    name: str
    use_vertexai: bool
    project: Optional[str]
    location: Optional[str]
    api_version: str
    argon_model: str
    hydrogen_model: str

class MCoreGeminiRouter:
    def __init__(self, mode: SandboxMode = "auto", argon_model: Optional[str] = None, hydrogen_model: Optional[str] = None, default_temperature: float = 0.4, default_max_tokens: int = 2048) -> None:
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.profile = self._detect_sandbox(mode=mode, argon_override=argon_model, hydrogen_override=hydrogen_model)
        self.client = self._build_client(self.profile)

    @classmethod
    def _detect_sandbox(cls, mode: SandboxMode, argon_override: Optional[str], hydrogen_override: Optional[str]) -> SandboxProfile:
        argon_id = argon_override or os.getenv("GEMINI_CODING_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-4-argon"
        hydrogen_id = hydrogen_override or os.getenv("GEMINI_FAST_MODEL") or "gemini-4-hydrogen"
        vertex_flag = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower()
        api_key = _clean_secret(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip() or None
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "").strip() or "global"
        adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        gcloud_dir = os.getenv("CLOUDSDK_CONFIG", "").strip()
        has_adc = bool((adc_path and Path(adc_path).is_file()) or "mcore-vertex" in gcloud_dir)

        if mode == "sandbox2" or vertex_flag in {"true", "1", "yes"} or (has_adc and project and not api_key):
            if not project:
                raise RuntimeError("Sandbox 2 (Vertex AI) selected, but GOOGLE_CLOUD_PROJECT is unset.")
            return SandboxProfile("sandbox2:vertex-keyless", True, project, location, os.getenv("GOOGLE_GENAI_API_VERSION", "v1beta1"), argon_id, hydrogen_id)
        if not api_key:
            raise RuntimeError("Sandbox 1 (AI Studio) selected, but GEMINI_API_KEY is missing.")
        return SandboxProfile("sandbox1:aistudio-key", False, None, None, os.getenv("GOOGLE_GENAI_API_VERSION", "v1beta"), argon_id, hydrogen_id)

    @classmethod
    def _build_client(cls, profile: SandboxProfile) -> genai.Client:
        http_opts = types.HttpOptions(api_version=profile.api_version)
        if profile.use_vertexai:
            return genai.Client(vertexai=True, project=profile.project, location=profile.location, http_options=http_opts)
        return genai.Client(vertexai=False, api_key=_clean_secret(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")), http_options=http_opts)

    def resolve_model(self, tier: ModelTier = "argon", model: Optional[str] = None) -> str:
        return model if model else (self.profile.hydrogen_model if tier == "hydrogen" else self.profile.argon_model)

    def _build_config(self, system_instruction: Optional[str] = None, temperature: Optional[float] = None, max_output_tokens: Optional[int] = None, response_mime_type: Optional[str] = None, response_schema: Any = None, tools: Optional[Sequence[Any]] = None, automatic_function_calling: bool = True) -> types.GenerateContentConfig:
        afc = types.AutomaticFunctionCallingConfig(disable=not automatic_function_calling) if tools else None
        return types.GenerateContentConfig(system_instruction=system_instruction, temperature=self.default_temperature if temperature is None else temperature, max_output_tokens=self.default_max_tokens if max_output_tokens is None else max_output_tokens, response_mime_type=response_mime_type, response_schema=response_schema, tools=list(tools) if tools else None, automatic_function_calling=afc)

    def generate(self, prompt: str, *, tier: ModelTier = "argon", model: Optional[str] = None, system_instruction: Optional[str] = None, temperature: Optional[float] = None, max_output_tokens: Optional[int] = None) -> str:
        resp = self.client.models.generate_content(model=self.resolve_model(tier=tier, model=model), contents=prompt, config=self._build_config(system_instruction, temperature, max_output_tokens))
        return resp.text or ""

    async def agenerate(self, prompt: str, *, tier: ModelTier = "argon", model: Optional[str] = None, system_instruction: Optional[str] = None, temperature: Optional[float] = None, max_output_tokens: Optional[int] = None) -> str:
        resp = await self.client.aio.models.generate_content(model=self.resolve_model(tier=tier, model=model), contents=prompt, config=self._build_config(system_instruction, temperature, max_output_tokens))
        return resp.text or ""

    async def astream(self, prompt: str, *, tier: ModelTier = "argon", model: Optional[str] = None, system_instruction: Optional[str] = None, temperature: Optional[float] = None, max_output_tokens: Optional[int] = None) -> AsyncIterator[str]:
        async for chunk in await self.client.aio.models.generate_content_stream(model=self.resolve_model(tier=tier, model=model), contents=prompt, config=self._build_config(system_instruction, temperature, max_output_tokens)):
            if chunk.text:
                yield chunk.text

    async def agenerate_structured(self, prompt: str, schema: Union[Type[SchemaT], dict[str, Any]], *, tier: ModelTier = "argon", model: Optional[str] = None, system_instruction: Optional[str] = None, temperature: float = 0.1, max_output_tokens: Optional[int] = None) -> Union[SchemaT, dict[str, Any]]:
        cfg = self._build_config(system_instruction, temperature, max_output_tokens, response_mime_type="application/json", response_schema=schema)
        resp = await self.client.aio.models.generate_content(model=self.resolve_model(tier=tier, model=model), contents=prompt, config=cfg)
        raw = resp.text or "{}"
        return schema.model_validate_json(raw) if isinstance(schema, type) and issubclass(schema, BaseModel) else json.loads(raw)

    async def agenerate_with_tools(self, prompt: str, tools: Sequence[Union[Callable[..., Any], types.Tool]], *, tier: ModelTier = "argon", model: Optional[str] = None, system_instruction: Optional[str] = None, automatic_function_calling: bool = True, temperature: Optional[float] = None, max_output_tokens: Optional[int] = None) -> str:
        cfg = self._build_config(system_instruction, temperature, max_output_tokens, tools=tools, automatic_function_calling=automatic_function_calling)
        resp = await self.client.aio.models.generate_content(model=self.resolve_model(tier=tier, model=model), contents=prompt, config=cfg)
        return resp.text or ""

    def close(self) -> None:
        self.client.close()

    async def aclose(self) -> None:
        await self.client.aio.aclose()

def query_openai_compat(base_url: str, api_key: str, model: str, prompt: str, system_instruction: str = "Be concise and technical.") -> str:
    r = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]},
        timeout=45.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    r = MCoreGeminiRouter()
    print(f"[ACTIVE SANDBOX] {r.profile.name} (vertexai={r.client.vertexai})")
    print(f"[ARGON]    {r.resolve_model('argon')} -> {r.generate('Reply with exact word: ARGON_OK', tier='argon', max_output_tokens=32).strip()}")
    r.close()
