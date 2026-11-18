#!/usr/bin/env python3
"""MCORE AIS Local Voice Console v0.6 — Sovereign Bangla-First STT + Gemini CLI.
Secured for global Cloudflare Tunnel deployment (ais.mcorecare.com, ais.mcoreai.dev).
Enforces Unicode Bengali script anchoring, Devanagari drift protection, and Sovereign Key Auth."""

from __future__ import annotations

import hmac
import json
import os
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from faster_whisper import WhisperModel

HOST = "127.0.0.1"
PORT = int(os.environ.get("MCORE_PORT", "7860"))
WORKDIR = Path(os.environ.get("MCORE_WORKDIR", str(Path.home()))).expanduser().resolve()
GEMINI = os.environ.get("GEMINI_BIN") or shutil.which("gemini")
GEMINI_TIMEOUT = int(os.environ.get("MCORE_GEMINI_TIMEOUT", "240"))
WHISPER_MODEL_NAME = os.environ.get("MCORE_WHISPER_MODEL", "medium")
WHISPER_CACHE = os.environ.get("HF_HOME", "/srv/mcore/apps/voice-console/.cache")
MAX_AUDIO_BYTES = 15 * 1024 * 1024

# Bengali Unicode script anchor prompt (prevents Hindi/Devanagari token drift)
BANGLA_SCRIPT_PROMPT = "বাংলায় শুদ্ধ বানানে লিখুন: আমার সোনার বাংলা, আমি তোমায় ভালোবাসি। ঢাকা, বাংলাদেশ।"

# Sovereign Access Key Authentication
AUTH_KEY = os.environ.get("MCORE_VOICE_AUTH_KEY", "").strip()

# Allowed Origins & Hosts
ALLOWED_ORIGINS = {
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
    "https://ais.mcorecare.com",
    "http://ais.mcorecare.com",
    "https://ais.mcoreai.dev",
    "http://ais.mcoreai.dev",
    "https://voice.mcoreai.dev",
    "http://voice.mcoreai.dev",
}
_custom_origins = os.environ.get("MCORE_ALLOWED_ORIGINS", "")
if _custom_origins:
    for _o in _custom_origins.split(","):
        _o = _o.strip()
        if _o:
            ALLOWED_ORIGINS.add(_o)

_whisper_model: WhisperModel | None = None
_whisper_lock = threading.Lock()


def get_whisper() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            if _whisper_model is None:
                _whisper_model = WhisperModel(
                    WHISPER_MODEL_NAME,
                    device="cpu",
                    compute_type="int8",
                    download_root=WHISPER_CACHE,
                )
    return _whisper_model


def devanagari_to_bengali_fallback(text: str) -> str:
    """Converts any stray Devanagari codepoints (U+0900..U+097F) to Bengali (U+0980..U+09FF)."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x0901 <= cp <= 0x0970:
            mapped = cp + 0x80
            # Map Devanagari 'va/wa' (0x0935 -> 0x09B5 unassigned) to Bengali 'ba' (0x09AC)
            if mapped == 0x09B5:
                mapped = 0x09AC
            out.append(chr(mapped))
        else:
            out.append(ch)
    return "".join(out)


SAFE_COMMANDS: dict[tuple[str, ...], str] = {
    ("pwd",): "pwd",
    ("whoami",): "whoami",
    ("id",): "id",
    ("hostname",): "hostname",
    ("uname", "-a"): "uname -a",
    ("uptime",): "uptime",
    ("date",): "date",
    ("df", "-h"): "df -h",
    ("free", "-h"): "free -h",
    ("ls", "-la"): "ls -la",
    ("git", "status", "--short", "--branch"): "git status --short --branch",
    ("ss", "-lntp"): "ss -lntp",
    ("systemctl", "status", "mcore-voice-console.service", "--no-pager"): "systemctl status mcore-voice-console.service --no-pager",
}

HTML = r"""<!doctype html>
<html lang="bn">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCORE AIS — Sovereign Bangla Voice Console v0.6</title>
<style>
:root{color-scheme:dark;--bg:#10141c;--panel:#191f2b;--line:#303a4c;--blue:#4285f4;--green:#006a4e;--red:#f42a41;--gold:#fbc02d;--muted:#aab5c6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:#edf2fa;font:15px/1.55 system-ui,"Noto Sans Bengali",sans-serif}
header{padding:18px 22px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center}
h1{font-size:18px;margin:0}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;text-transform:uppercase}
.badge-gold{background:rgba(251,192,45,.15);color:var(--gold);border:1px solid rgba(251,192,45,.3)}
.badge-green{background:rgba(0,106,78,.2);color:#34a853;border:1px solid rgba(0,106,78,.4)}
main{max-width:1160px;margin:22px auto;padding:0 16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}
h2{font-size:16px;margin:0 0 12px}
textarea,input,select{width:100%;background:#0d121a;color:#edf2fa;border:1px solid var(--line);border-radius:9px;padding:12px;font:15px "Noto Sans Bengali",ui-monospace,monospace}
textarea{min-height:150px;resize:vertical}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
select{width:auto;padding:9px 12px;font-family:"Noto Sans Bengali",system-ui,sans-serif}
button{background:var(--blue);color:white;border:0;border-radius:9px;padding:10px 14px;font-weight:650;cursor:pointer}
button.secondary{background:#006a4e}
button.recording{background:#f42a41}
button.chip{background:#232c3d;border:1px solid var(--line);padding:5px 9px;font-size:12px;font-weight:500;font-family:ui-monospace,monospace}
button.chip:hover{border-color:var(--blue)}
button.auth-btn{background:#303a4c;font-size:12px;padding:6px 12px}
button:disabled{opacity:.5;cursor:not-allowed}
.meter-wrap{flex:1;min-width:120px;height:10px;background:#0d121a;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.meter-bar{height:100%;width:0%;background:#34a853;transition:width 60ms linear}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b1017;border:1px solid var(--line);padding:12px;border-radius:9px;min-height:110px;max-height:360px;overflow:auto;font-family:"Noto Sans Bengali",ui-monospace,monospace}
small,.muted,.note{color:var(--muted)}
.note{font-size:12px;margin-top:9px}
.wide{grid-column:1/-1}
#authBanner{background:#161c27;border:1px solid var(--gold);padding:12px 16px;border-radius:10px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media(max-width:760px){main{grid-template-columns:1fr}.wide{grid-column:auto}}
</style>
</head>
<body>
<header>
  <div>
    <h1>MCORE AIS — Sovereign Bangla Voice &amp; Prompt Console <span class="badge badge-gold">v0.6 Global</span></h1>
    <small>Bangla-First Whisper STT · Gemini CLI · Cloudflare Zero-Trust · Protected Origin</small>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <button class="auth-btn" id="keyBtn" title="Set or manage Sovereign Access Key">🔐 Key: Local</button>
    <small id="status">Connecting…</small>
  </div>
</header>
<main>
  <div class="wide" id="authBanner" style="display:none;">
    <div>
      <strong style="color:var(--gold)">🔐 Sovereign Security Shield Active</strong>
      <div style="font-size:12px;color:var(--muted)">This console is exposed globally. Enter your Sovereign Access Key to unlock STT and Gemini executions.</div>
    </div>
    <div style="display:flex;gap:8px;">
      <input type="password" id="authKeyInput" placeholder="Enter Sovereign Access Key" style="width:240px;padding:8px 12px;">
      <button id="saveKeyBtn" style="padding:8px 14px;">Unlock</button>
    </div>
  </div>

  <section>
    <h2>বাংলা ভয়েস / প্রম্পট → Gemini CLI</h2>
    <textarea id="prompt" placeholder="বাংলায় বলুন বা লিখুন (যেমন: আমার সোনার বাংলা)..."></textarea>
    <div class="row">
      <select id="lang" title="Primary Speech Language">
        <option value="bn" selected>বাংলা — Bangladesh (bn-BD Primary)</option>
        <option value="en">English (en)</option>
      </select>
      <button class="secondary" id="mic">🎙 বাংলায় বলুন (Record)</button>
      <button id="send">Send prompt to Gemini</button>
    </div>
    <div class="row">
      <small>Mic level:</small>
      <div class="meter-wrap"><div class="meter-bar" id="meter"></div></div>
    </div>
    <p class="note" id="micNote">Bangla-first local transcription active (Unicode U+0980–U+09FF enforced).</p>
    <h2 style="margin-top:18px">Gemini response</h2>
    <pre id="gemini">No prompt submitted.</pre>
  </section>

  <section>
    <h2>Local web terminal — restricted commands</h2>
    <input id="cmd" placeholder="Click a command chip below or type an allowlisted command (e.g. whoami)">
    <div class="row" id="chips"></div>
    <div class="row">
      <button id="run">Review &amp; run</button>
    </div>
    <p class="note">Only exact read-only commands from the server allowlist are accepted.</p>
    <h2 style="margin-top:18px">Terminal output</h2>
    <pre id="terminal">No command run.</pre>
  </section>

  <section class="wide">
    <h2>Security &amp; Language Sovereignty</h2>
    <p class="muted">Primary ASR prioritizes Bengali script (U+0980–U+09FF) with Devanagari drift protection. Protected by Sovereign Access Authentication, Cloudflare QUIC Tunnel edge encryption, and least-privilege systemd isolation.</p>
  </section>
</main>
<script>
const $=id=>document.getElementById(id);
["whoami","pwd","hostname","uptime","df -h","free -h","ss -lntp","ls -la","date"].forEach(c=>{
  const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=c;
  b.onclick=()=>{$('cmd').value=c;$('cmd').focus();};$('chips').appendChild(b);
});

// Auto-capture ?key= from URL if present
const urlParams = new URLSearchParams(window.location.search);
if(urlParams.has('key')){
  const qk = urlParams.get('key').trim();
  if(qk){
    sessionStorage.setItem('mcore_voice_key', qk);
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

function getKey(){
  return sessionStorage.getItem('mcore_voice_key') || '';
}

function updateKeyUI(hasAuthRequired){
  const k = getKey();
  const btn = $('keyBtn');
  if(!hasAuthRequired){
    btn.textContent = '🔓 Loopback Access';
    btn.className = 'auth-btn';
    $('authBanner').style.display = 'none';
    return;
  }
  if(k){
    btn.textContent = '🔐 Sovereign: Authenticated';
    btn.style.borderColor = '#34a853';
    btn.style.color = '#34a853';
    $('authBanner').style.display = 'none';
  } else {
    btn.textContent = '🔒 Key Required';
    btn.style.borderColor = 'var(--gold)';
    btn.style.color = 'var(--gold)';
    $('authBanner').style.display = 'flex';
  }
}

$('keyBtn').onclick = () => {
  const current = getKey();
  const res = prompt('Enter MCORE Sovereign Access Key:', current);
  if(res !== null){
    if(res.trim()){
      sessionStorage.setItem('mcore_voice_key', res.trim());
    } else {
      sessionStorage.removeItem('mcore_voice_key');
    }
    location.reload();
  }
};

$('saveKeyBtn').onclick = () => {
  const val = $('authKeyInput').value.trim();
  if(val){
    sessionStorage.setItem('mcore_voice_key', val);
    $('authKeyInput').value = '';
    updateKeyUI(true);
  }
};

async function postJson(p, d){
  const headers = {'Content-Type': 'application/json'};
  const k = getKey();
  if(k) headers['X-MCORE-KEY'] = k;
  const r = await fetch(p, {method: 'POST', headers, body: JSON.stringify(d)});
  let j = {};
  try { j = await r.json(); } catch {}
  if(r.status === 401){
    updateKeyUI(true);
    throw Error('401 Unauthorized: Valid Sovereign Access Key required.');
  }
  if(!r.ok) throw Error(j.error || r.statusText);
  return j;
}

(async()=>{
  try{
    const headers = {};
    const k = getKey();
    if(k) headers['X-MCORE-KEY'] = k;
    let s = await fetch('/api/status', {headers}).then(r=>r.json());
    $('status').textContent = `${s.state} · ${s.bind} · Whisper: ${s.whisper} · Primary: ${s.primary_language}`;
    updateKeyUI(s.auth_required);
  }catch(e){
    $('status').textContent = 'Status unavailable';
  }
})();

$('send').onclick=async()=>{
  let prompt=$('prompt').value.trim();
  if(!prompt){$('gemini').textContent='অনুগ্রহ করে বাংলা বা ইংরেজিতে প্রম্পট দিন।';return;}
  $('gemini').textContent='Waiting for Gemini CLI…';$('send').disabled=true;
  try{
    let r=await postJson('/api/prompt',{prompt});
    $('gemini').textContent=`Exit code: ${r.returncode}\n\n${r.stdout}\n${r.stderr}`.trim();
  }catch(e){$('gemini').textContent='ERROR: '+e.message;}
  finally{$('send').disabled=false;}
};

$('run').onclick=async()=>{
  let command=$('cmd').value.trim();
  if(!command){$('terminal').textContent='Select a command chip first.';return;}
  if(!confirm(`Run locally?\n\n${command}`))return;
  $('terminal').textContent='Running…';$('run').disabled=true;
  try{
    let r=await postJson('/api/terminal',{command});
    $('terminal').textContent=`Exit code: ${r.returncode}\n\n${r.stdout}\n${r.stderr}`.trim();
  }catch(e){$('terminal').textContent='ERROR: '+e.message;}
  finally{$('run').disabled=false;}
};

let mr=null,chunks=[],stream=null,mt=null,actx=null;
function stopM(){if(mt){clearInterval(mt);mt=null;}if(actx){actx.close().catch(()=>{});actx=null;}$('meter').style.width='0%';}

$('mic').onclick=async()=>{
  if(mr&&mr.state==='recording'){mr.stop();return;}
  try{
    stream=await navigator.mediaDevices.getUserMedia({audio:true});
    actx=new(window.AudioContext||window.webkitAudioContext)();
    const src=actx.createMediaStreamSource(stream),an=actx.createAnalyser();an.fftSize=256;src.connect(an);
    const buf=new Uint8Array(an.frequencyBinCount);
    mt=setInterval(()=>{an.getByteFrequencyData(buf);let s=0;for(let i=0;i<buf.length;i++)s+=buf[i];$('meter').style.width=Math.min(100,Math.round((s/buf.length)*1.8))+'%';},60);
    chunks=[];
    const mime=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm';
    mr=new MediaRecorder(stream,{mimeType:mime});
    mr.ondataavailable=e=>{if(e.data&&e.data.size>0)chunks.push(e.data);};
    mr.onstop=async()=>{
      stopM();stream.getTracks().forEach(t=>t.stop());
      $('mic').classList.remove('recording');$('mic').textContent='🎙 বাংলায় বলুন (Record)';$('mic').disabled=true;
      $('micNote').textContent='বাংলায় রূপান্তর হচ্ছে (Transcribing Bangla locally)…';
      try{
        const blob=new Blob(chunks,{type:mime}),lang=$('lang').value;
        const headers={'Content-Type':mime};
        const k=getKey();
        if(k) headers['X-MCORE-KEY']=k;
        const resp=await fetch('/api/transcribe?lang='+encodeURIComponent(lang),{method:'POST',headers,body:blob});
        const j=await resp.json();
        if(resp.status === 401){
          updateKeyUI(true);
          throw Error('401 Unauthorized: Valid Sovereign Access Key required.');
        }
        if(!resp.ok)throw Error(j.error||resp.statusText);
        if(j.text){
          const cur=$('prompt').value.trim();
          $('prompt').value=(cur?(cur+' '+j.text):j.text).trim();
          $('micNote').textContent=`সফলভাবে রূপান্তরিত (${j.language}, ${j.duration_s}s).`;
        }else{$('micNote').textContent='কোনো কথা শনাক্ত হয়নি (Mic level বার লক্ষ্য করুন)।';}
      }catch(err){$('micNote').textContent='Error: '+err.message;}
      finally{$('mic').disabled=false;}
    };
    mr.start();
    $('mic').classList.add('recording');$('mic').textContent='⏹ থামুন ও রূপান্তর করুন (Stop)';
    $('micNote').textContent='রেকর্ডিং চলছে… বাংলায় বলুন, তারপর Stop চাপুন।';
  }catch(err){stopM();$('micNote').textContent='Mic error: '+err.message;}
};
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "MCOREVoiceConsole/0.6-GlobalSecure"

    def log_message(self, fmt: str, *args: object) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def _send_security_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-MCORE-KEY")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "microphone=(self)")
        self.send_header("Cache-Control", "no-store")

    def _is_authorized(self) -> bool:
        if not AUTH_KEY:
            return True

        # Check client IP: allow local loopback callers without Origin
        client_ip = self.client_address[0]
        origin = self.headers.get("Origin", "")
        if client_ip in {"127.0.0.1", "::1"} and (not origin or origin in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}):
            return True

        # Check X-MCORE-KEY header
        header_key = self.headers.get("X-MCORE-KEY", "").strip()
        if header_key and hmac.compare_digest(header_key, AUTH_KEY):
            return True

        # Check Authorization: Bearer <key>
        auth = self.headers.get("Authorization", "").strip()
        if auth.lower().startswith("bearer "):
            bearer_key = auth[7:].strip()
            if hmac.compare_digest(bearer_key, AUTH_KEY):
                return True

        # Check query parameters (?key=...)
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "key" in params and params["key"]:
            if hmac.compare_digest(params["key"][0].strip(), AUTH_KEY):
                return True

        # Check Cookie
        cookie = self.headers.get("Cookie", "")
        for c in cookie.split(";"):
            parts = c.strip().split("=", 1)
            if len(parts) == 2 and parts[0].strip() == "mcore_voice_key":
                if hmac.compare_digest(parts[1].strip(), AUTH_KEY):
                    return True

        return False

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 20000:
            raise ValueError("Invalid request size.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("JSON object required.")
        return data

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_security_headers()
        self.end_headers()

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._send_security_headers()
            self.end_headers()
        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_security_headers()
            self.end_headers()
        else:
            self.send_response(404)
            self._send_security_headers()
            self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            self._json(200, {
                "state": "ready",
                "version": "0.6-GlobalSecure",
                "primary_language": "bn-BD",
                "bind": f"{HOST}:{PORT}",
                "working_directory": str(WORKDIR),
                "whisper": f"faster-whisper ({WHISPER_MODEL_NAME})",
                "gemini": GEMINI or "NOT FOUND",
                "python": os.sys.version.split()[0],
                "auth_required": bool(AUTH_KEY),
                "domains": ["ais.mcorecare.com", "ais.mcoreai.dev", "voice.mcoreai.dev"],
            })
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            self._json(403, {"error": f"Origin not allowed: {origin}"})
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if not self._is_authorized():
            self._json(401, {"error": "Unauthorized: Valid Sovereign Access Key required"})
            return

        if path == "/api/transcribe":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 100 or length > MAX_AUDIO_BYTES:
                    self._json(400, {"error": "Invalid audio size."})
                    return
                audio_bytes = self.rfile.read(length)
                # Default strictly to Bangla ('bn') unless explicitly overridden to 'en'
                params = parse_qs(parsed.query)
                lang = params.get("lang", ["bn"])[0].lower()
                target_lang = "en" if lang == "en" else "bn"
                init_prompt = None if target_lang == "en" else BANGLA_SCRIPT_PROMPT

                ctype = self.headers.get("Content-Type", "").lower()
                suffix = ".wav" if "wav" in ctype or audio_bytes[:4] == b"RIFF" else ".webm"

                with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
                    tmp.write(audio_bytes)
                    tmp.flush()
                    segs, info = get_whisper().transcribe(
                        tmp.name,
                        language=target_lang,
                        initial_prompt=init_prompt,
                        beam_size=5,
                        vad_filter=False,
                    )
                    raw_text = " ".join(s.text.strip() for s in segs if s.text.strip()).strip()
                    clean_text = devanagari_to_bengali_fallback(raw_text) if target_lang == "bn" else raw_text
                    self._json(200, {
                        "text": clean_text,
                        "language": target_lang,
                        "script": "Bengali (U+0980-U+09FF)" if target_lang == "bn" else "Latin",
                        "duration_s": round(getattr(info, "duration", 0.0), 2),
                    })
            except Exception as exc:
                self._json(500, {"error": f"Whisper failed: {exc}"})
            return

        try:
            data = self._body()
        except Exception as exc:
            self._json(400, {"error": str(exc)})
            return

        if path == "/api/prompt":
            prompt = data.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
                self._json(400, {"error": "Invalid prompt."})
                return
            if not GEMINI:
                self._json(503, {"error": "Gemini CLI not found."})
                return
            r = subprocess.run(
                [GEMINI, "-p", prompt.strip()],
                cwd=str(WORKDIR),
                capture_output=True,
                text=True,
                timeout=GEMINI_TIMEOUT,
                check=False,
            )
            self._json(200, {"returncode": r.returncode, "stdout": r.stdout[-30000:], "stderr": r.stderr[-12000:]})
            return

        if path == "/api/terminal":
            cmd = data.get("command")
            if not isinstance(cmd, str) or len(cmd) > 300:
                self._json(400, {"error": "Invalid command."})
                return
            allowed = SAFE_COMMANDS.get(tuple(cmd.strip().split()))
            if not allowed:
                self._json(403, {"error": "Command not allowlisted."})
                return
            exe = shutil.which(allowed.split()[0])
            r = subprocess.run(
                [exe, *allowed.split()[1:]],
                cwd=str(WORKDIR),
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self._json(200, {"returncode": r.returncode, "stdout": r.stdout[-16000:], "stderr": r.stderr[-8000:]})
            return

        self._json(404, {"error": "Not found"})


if __name__ == "__main__":
    get_whisper()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
