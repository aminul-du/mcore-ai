import asyncio, hashlib, json, os, time
from typing import List, Optional
import httpx, redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MCore AI Gateway", version="1.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
rdb = redis.Redis(host="redis", port=6379, password=os.getenv("REDIS_PASSWORD") or None, decode_responses=True)

class CompareRequest(BaseModel):
    prompt: str
    models: List[str] = ["gemini-4-neon", "gemini-4-hydrogen", "openai/gpt-oss-120b", "claude-sonnet-4-20250514", "deepseek-chat", "gpt-4o"]
    system_instruction: Optional[str] = "Provide a clear, high-signal, analytical response."
    bypass_cache: bool = False

class ModelResult(BaseModel):
    model: str
    provider: str
    response: str
    latency_ms: int
    cached: bool = False
    status: str

async def call_upstream(client: httpx.AsyncClient, model: str, prompt: str, sys_inst: str, bypass: bool) -> ModelResult:
    t0 = time.perf_counter()
    ck = "mcore:" + hashlib.sha256(f"{model}|{sys_inst}|{prompt}".encode()).hexdigest()
    if not bypass:
        try:
            if hit := await rdb.get(ck):
                d = json.loads(hit); d["cached"] = True; d["latency_ms"] = int((time.perf_counter() - t0) * 1000)
                return ModelResult(**d)
        except Exception:
            pass

    try:
        if model.startswith("gemini"):
            prov, key = "Google DeepMind", os.getenv("GEMINI_API_KEY", "")
            if not key or key.startswith(("replace_", "YOUR_")):
                return ModelResult(model=model, provider=prov, response=f"[{model} Standby] Add GEMINI_API_KEY", latency_ms=1, status="standby")
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={"system_instruction": {"parts": [{"text": sys_inst}]}, "contents": [{"parts": [{"text": prompt}]}]},
                timeout=45.0,
            )
            r.raise_for_status()
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif model.startswith("openai/") or model.startswith("llama-"):
            prov, key = "Groq LPU", os.getenv("GROQ_API_KEY", "")
            if not key or key.startswith(("replace_", "YOUR_")):
                return ModelResult(model=model, provider=prov, response=f"[{model} Standby] Add GROQ_API_KEY", latency_ms=1, status="standby")
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": [{"role": "system", "content": sys_inst}, {"role": "user", "content": prompt}]},
                timeout=45.0,
            )
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
        elif model.startswith("claude"):
            prov, key = "Anthropic", os.getenv("ANTHROPIC_API_KEY", "")
            if not key or key.startswith(("replace_", "YOUR_")):
                return ModelResult(model=model, provider=prov, response=f"[{model} Standby] Add ANTHROPIC_API_KEY", latency_ms=1, status="standby")
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 2048, "system": sys_inst, "messages": [{"role": "user", "content": prompt}]},
                timeout=45.0,
            )
            r.raise_for_status()
            txt = r.json()["content"][0]["text"]
        elif model.startswith("deepseek"):
            prov, key = "DeepSeek", os.getenv("DEEPSEEK_API_KEY", "")
            if not key or key.startswith(("replace_", "YOUR_")):
                return ModelResult(model=model, provider=prov, response=f"[{model} Standby] Add DEEPSEEK_API_KEY", latency_ms=1, status="standby")
            r = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": [{"role": "system", "content": sys_inst}, {"role": "user", "content": prompt}]},
                timeout=45.0,
            )
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
        else:
            prov, key = "OpenAI", os.getenv("OPENAI_API_KEY", "")
            if not key or key.startswith(("replace_", "YOUR_")):
                return ModelResult(model=model, provider=prov, response=f"[{model} Standby] Add OPENAI_API_KEY", latency_ms=1, status="standby")
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": [{"role": "system", "content": sys_inst}, {"role": "user", "content": prompt}]},
                timeout=45.0,
            )
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]

        res = ModelResult(model=model, provider=prov, response=txt, latency_ms=int((time.perf_counter() - t0) * 1000), status="ok")
        try:
            await rdb.setex(ck, int(os.getenv("CACHE_TTL_SECONDS", "3600")), res.model_dump_json())
        except Exception:
            pass
        return res
    except Exception as e:
        return ModelResult(model=model, provider="Upstream", response=f"Error: {e}", latency_ms=int((time.perf_counter() - t0) * 1000), status="error")

@app.get("/api/health")
async def health():
    try:
        r_ok = bool(await rdb.ping())
    except Exception:
        r_ok = False
    return {"status": "healthy", "service": "mcore-ai-gateway", "redis_cache": r_ok, "ts": int(time.time())}

@app.post("/api/compare", response_model=List[ModelResult])
async def compare(req: CompareRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "Empty prompt")
    async with httpx.AsyncClient() as c:
        return await asyncio.gather(*[call_upstream(c, m, req.prompt, req.system_instruction or "", req.bypass_cache) for m in req.models])
