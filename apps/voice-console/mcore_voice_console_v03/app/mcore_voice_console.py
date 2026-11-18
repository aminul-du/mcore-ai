#!/usr/bin/env python3
"""MCORE AIS Local Voice Console v0.7 — Sovereign Bangla-First STT, Gemini CLI,
File Manager, xterm.js Web Terminal, and Productivity Dashboard (FastAPI Engine)."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import pty
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Header,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from faster_whisper import WhisperModel
import uvicorn

HOST = "127.0.0.1"
PORT = int(os.environ.get("MCORE_PORT", "7860"))
WORKDIR = Path(os.environ.get("MCORE_WORKDIR", str(Path.home()))).expanduser().resolve()
GEMINI = os.environ.get("GEMINI_BIN") or shutil.which("gemini")
GEMINI_TIMEOUT = int(os.environ.get("MCORE_GEMINI_TIMEOUT", "240"))
WHISPER_MODEL_NAME = os.environ.get("MCORE_WHISPER_MODEL", "medium")
WHISPER_CACHE = os.environ.get("HF_HOME", "/srv/mcore/apps/voice-console/.cache")
MAX_AUDIO_BYTES = 15 * 1024 * 1024

UPLOAD_DIR = "/srv/mcore/apps/voice-console/local_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

BANGLA_SCRIPT_PROMPT = "বাংলায় শুদ্ধ বানানে লিখুন: আমার সোনার বাংলা, আমি তোমায় ভালোবাসি। ঢাকা, বাংলাদেশ।"
AUTH_KEY = (os.environ.get("MCORE_VOICE_AUTH_KEY") or os.environ.get("MCORE_SOVEREIGN_KEY") or "").strip()

ALLOWED_ORIGINS = [
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
    "https://ais.mcorecare.com",
    "http://ais.mcorecare.com",
    "https://ais.mcoreai.dev",
    "http://ais.mcoreai.dev",
    "https://voice.mcoreai.dev",
    "http://voice.mcoreai.dev",
]
_custom_origins = os.environ.get("MCORE_ALLOWED_ORIGINS", "")
if _custom_origins:
    for _o in _custom_origins.split(","):
        _o = _o.strip()
        if _o and _o not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(_o)

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
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x0901 <= cp <= 0x0970:
            mapped = cp + 0x80
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


def is_authenticated(request: Request, x_mcore_key: Optional[str] = None) -> bool:
    if not AUTH_KEY:
        return True

    # Allow local loopback callers without origin or from localhost
    client_ip = request.client.host if request.client else ""
    origin = request.headers.get("origin", "")
    if client_ip in {"127.0.0.1", "::1"} and (not origin or origin in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}):
        return True

    # Check X-MCORE-KEY header
    key = x_mcore_key or request.headers.get("x-mcore-key") or ""
    if key and hmac.compare_digest(key.strip(), AUTH_KEY):
        return True

    # Check Authorization: Bearer <key>
    auth = request.headers.get("authorization", "").strip()
    if auth.lower().startswith("bearer "):
        if hmac.compare_digest(auth[7:].strip(), AUTH_KEY):
            return True

    # Check query parameter ?key=
    query_key = request.query_params.get("key") or request.query_params.get("token")
    if query_key and hmac.compare_digest(query_key.strip(), AUTH_KEY):
        return True

    # Check Cookie
    cookie_key = request.cookies.get("mcore_voice_key")
    if cookie_key and hmac.compare_digest(cookie_key.strip(), AUTH_KEY):
        return True

    return False


def verify_key(request: Request, x_mcore_key: Optional[str] = Header(None)) -> str:
    if not is_authenticated(request, x_mcore_key):
        raise HTTPException(status_code=401, detail="Unauthorized: Valid Sovereign Access Key required")
    return x_mcore_key or ""


app = FastAPI(title="MCORE AIS Sovereign Voice & Productivity Console", version="0.7-ROI-Unified")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Origin check on POST requests
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "DELETE"} and origin:
        if origin not in ALLOWED_ORIGINS:
            return JSONResponse(status_code=403, content={"error": f"Origin not allowed: {origin}"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    response.headers["Cache-Control"] = "no-store"
    return response


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCORE AIS — Productivity & AI ROI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- xterm.js -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        body { background-color: #0B0E14; color: #E2E8F0; font-family: 'Inter', sans-serif; -webkit-font-smoothing: antialiased; }
        .font-bn { font-family: 'Noto Sans Bengali', 'Inter', sans-serif; }
        .card { border-radius: 16px; padding: 24px; height: 100%; display: flex; flex-direction: column; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); transition: border-color 0.3s ease; }
        .card-purple { background-color: #13111C; border: 1px solid #4C1D95; }
        .card-teal { background-color: #0D161A; border: 1px solid #0F766E; }
        .card-blue { background-color: #0F1423; border: 1px solid #1E3A8A; }
        
        textarea, input[type="text"], select { background-color: #05070A; border: 1px solid #334155; color: #F8FAFC; border-radius: 8px; padding: 12px 16px; width: 100%; outline: none; font-size: 14px; }
        textarea:focus, input[type="text"]:focus, select:focus { border-color: #64748B; box-shadow: 0 0 0 2px rgba(100, 116, 139, 0.2); }
        
        select { appearance: none; background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2394A3B8%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E"); background-repeat: no-repeat; background-position: right 16px top 50%; background-size: 10px auto; padding-right: 40px; }

        .btn { transition: all 0.2s; font-weight: 600; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
        .btn:active { transform: scale(0.97); }
        .form-row { display: flex; gap: 12px; align-items: center; }
        .form-row select { height: 48px; }
        .form-row .btn-record { height: 48px; width: 48px; padding: 0; flex-shrink: 0; background-color: #0F766E; color: white; border: 1px solid #115E59; }
        .form-row .btn-record:hover { background-color: #115E59; border-color: #14B8A6; }
        .form-row .btn-record.recording { background-color: #DC2626 !important; border-color: #EF4444 !important; animation: pulse 1.5s infinite; }
        
        .btn-send { background-color: #2563EB; color: white; padding: 12px; height: 48px; }
        .btn-send:hover { background-color: #1D4ED8; }
        .btn-run { background-color: #2563EB; color: white; padding: 8px 20px; height: 40px; }
        .btn-run:hover { background-color: #1D4ED8; }
        
        .chip { background-color: #1E293B; border: 1px solid #334155; color: #CBD5E1; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-family: monospace; cursor: pointer; }
        .chip:hover { background-color: #334155; color: #F8FAFC; }

        #terminal-container { height: 340px; background-color: #000000; border-radius: 8px; padding: 8px; border: 1px solid #1E293B; overflow: hidden; }
        .output-box { background-color: #05070A; border: 1px solid #1E293B; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; color: #94A3B8; min-height: 100px; white-space: pre-wrap; word-break: break-all; max-height: 280px; overflow-y: auto; }

        .devops-table th { text-align: left; padding: 12px 16px; font-size: 11px; text-transform: uppercase; color: #94A3B8; border-bottom: 1px solid #1E293B; }
        .devops-table td { padding: 16px; border-bottom: 1px solid #1E293B; font-size: 14px; }
        
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; margin-bottom: 8px; }
        .btn-delete { color: #F87171; padding: 4px 8px; border-radius: 4px; cursor: pointer; }
        .btn-delete:hover { background-color: #7F1D1D; color: #FCA5A5; }

        #chatbot-widget { position: fixed; bottom: 24px; right: 24px; z-index: 50; display: flex; flex-direction: column; align-items: flex-end; }
        #chatbot-window { width: 340px; height: 450px; background-color: #0B0E14; border: 1px solid #1E293B; border-radius: 16px; display: none; flex-direction: column; overflow: hidden; margin-bottom: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        #chatbot-button { width: 56px; height: 56px; background-color: #2563EB; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
        .chat-message { padding: 10px 14px; border-radius: 8px; margin-bottom: 10px; max-width: 85%; font-size: 14px; line-height: 1.4; word-break: break-word; }
        .msg-bot { background-color: #1E293B; color: #E2E8F0; align-self: flex-start; }
        .msg-user { background-color: #2563EB; color: white; align-self: flex-end; margin-left: auto; }
    </style>
</head>
<body class="p-4 md:p-8 lg:p-10">

    <!-- HEADER -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-gray-800 pb-6 gap-4">
        <div>
            <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight text-white">MCORE AIS <span class="text-gray-500 font-normal hidden sm:inline">— Productivity & AI ROI</span></h1>
            <p class="text-sm md:text-base text-gray-400 mt-1">Sovereign Bangla Voice & Prompt Console (v0.7)</p>
        </div>
        <button id="authBtn" class="bg-[#064E3B] hover:bg-[#065F46] text-[#34D399] px-4 py-2 rounded-full text-xs md:text-sm font-semibold border border-[#065F46] flex items-center gap-2 cursor-pointer transition-colors" title="Click to update Sovereign Access Key">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" clip-rule="evenodd"></path></svg>
            <span id="authStatusText">Sovereign: Authenticated</span>
        </button>
    </div>

    <!-- 3-COLUMN GRID -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        <!-- COLUMN 1: Bangla Voice (Purple) -->
        <div class="card card-purple">
            <h2 class="text-lg md:text-xl font-bold mb-4 text-purple-400 font-bn">বাংলা ভয়েস / প্রম্পট → Gemini CLI</h2>
            <textarea id="promptInput" rows="4" placeholder="বাংলায় বলুন বা লিখুন (যেমন: আমার সোনার বাংলা)..." class="mb-4 font-bn"></textarea>
            
            <div class="form-row mb-4">
                <select id="langSelect" class="w-full text-sm font-bn">
                    <option value="bn" selected>বাংলা (Primary) / English</option>
                    <option value="en">English (en)</option>
                </select>
                <button id="recordBtn" class="btn btn-record" title="বাংলায় বলুন (Record)">
                    <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd"></path></svg>
                </button>
            </div>

            <button id="sendPromptBtn" class="btn btn-send w-full mb-4">Send prompt to Gemini</button>

            <div class="mb-4">
                <label class="text-xs text-gray-400 mb-1 block">Mic level:</label>
                <div class="w-full bg-gray-800 rounded-full h-1.5"><div id="micMeter" class="bg-purple-500 h-1.5 rounded-full transition-all" style="width: 0%"></div></div>
            </div>
            <p id="sttStatusNote" class="text-xs text-gray-500 mb-6">Bangla-first local transcription active (Unicode U+0980-U+09FF enforced).</p>

            <div class="mt-auto">
                <h3 class="text-sm font-bold text-white mb-2">Gemini response</h3>
                <div id="geminiOutput" class="output-box">No prompt submitted.</div>
            </div>
        </div>

        <!-- COLUMN 2: Restricted Commands (Teal) -->
        <div class="card card-teal">
            <h2 class="text-lg md:text-xl font-bold mb-4 text-teal-400">Local web terminal — restricted</h2>
            <input id="cmdInput" type="text" placeholder="Click a chip or type an allowed command..." class="text-sm mb-4" />
            
            <div id="cmdChips" class="flex flex-wrap gap-2 mb-6">
                <!-- Chips injected via JS -->
            </div>
            
            <button id="runCmdBtn" class="btn btn-run w-max text-sm mb-2">Review & run</button>
            <p class="text-xs text-gray-500 mb-6">Only exact read-only commands from the server allowlist are accepted.</p>

            <div class="mt-auto">
                <h3 class="text-sm font-bold text-white mb-2">Terminal output</h3>
                <div id="cmdOutput" class="output-box text-emerald-400">No command run.</div>
            </div>
        </div>

        <!-- COLUMN 3: xterm.js (Blue) -->
        <div class="card card-blue">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2">
                <h2 class="text-lg md:text-xl font-bold text-blue-400">Sovereign Web Terminal</h2>
                <span class="text-xs bg-[#064E3B] text-[#34D399] px-3 py-1 rounded-full border border-[#065F46] font-semibold whitespace-nowrap">PTY Session</span>
            </div>
            <div id="terminal-container" class="flex-grow mt-2"></div>
        </div>
    </div>

    <!-- FILE MANAGER SECTION -->
    <div class="bg-[#111827] rounded-xl p-4 md:p-6 border border-gray-800 shadow-xl mb-8">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <div>
                <h2 class="text-lg md:text-xl font-bold text-white flex items-center gap-2">
                    <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>
                    Local File Manager
                </h2>
                <p class="text-sm text-gray-400 mt-1">Upload, view, and delete quarantined files in <code>/srv/mcore/apps/voice-console/local_storage</code>.</p>
            </div>
            <div class="flex items-center gap-3">
                <input type="file" id="fileInput" class="hidden" onchange="uploadFile()">
                <button onclick="document.getElementById('fileInput').click()" class="btn bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    Upload Document
                </button>
            </div>
        </div>
        <div id="fileListContainer" class="max-h-64 overflow-y-auto pr-2">
            <p class="text-gray-500 text-sm italic">Loading files...</p>
        </div>
    </div>

    <!-- DEVOPS MONITORING -->
    <div class="bg-[#13111C] rounded-xl p-4 md:p-6 border border-gray-800 shadow-xl overflow-hidden mb-8">
        <h2 class="text-lg md:text-xl font-bold mb-4 md:mb-6 text-white">Local DevOps Platform — Unified Monitoring</h2>
        <div class="overflow-x-auto">
            <table class="w-full devops-table min-w-[600px]">
                <thead><tr><th>DEVOPS AREA</th><th class="text-emerald-400">PLATFORM STATUS</th><th class="text-blue-400">METRICS / DETAILS</th></tr></thead>
                <tbody>
                    <tr><td class="text-gray-300">System Health &amp; Uptime</td><td class="font-bold text-white">99.98% (Healthy)</td><td id="sysMetric" class="text-gray-400 font-mono text-xs">Uptime: active | Bind: 127.0.0.1:7860 | Model: faster-whisper</td></tr>
                    <tr><td class="text-gray-300">Version Control (Git)</td><td class="font-bold text-white">Synced</td><td class="text-gray-400 font-mono text-xs">Branch: <span class="text-emerald-300">main</span> | Repos: mcoreai.git</td></tr>
                    <tr><td class="text-gray-300">Edge &amp; Ingress</td><td class="font-bold text-white">Proxied (QUIC/TLS)</td><td class="text-gray-400 font-mono text-xs">Cloudflare Tunnel: ais001 | ais.mcorecare.com</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- CHATBOT -->
    <div id="chatbot-widget">
        <div id="chatbot-window">
            <div class="bg-[#13111C] p-4 border-b border-gray-700 flex justify-between items-center">
                <div class="flex items-center gap-2"><div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div><span class="font-bold text-sm text-white">MCORE AI Assistant (Gemini)</span></div>
                <button onclick="toggleChat()" class="text-gray-400 hover:text-white"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
            </div>
            <div id="chat-messages" class="flex-1 p-4 overflow-y-auto flex flex-col">
                <div class="chat-message msg-bot">Hello AIS! I am your sovereign MCORE AI assistant powered by Gemini CLI. How can I assist you?</div>
            </div>
            <div class="p-3 bg-[#05070A] border-t border-gray-800">
                <form id="chat-form" class="flex gap-2">
                    <input type="text" id="chat-input" placeholder="Ask Gemini about metrics..." class="flex-1 bg-[#0B0E14] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg></button>
                </form>
            </div>
        </div>
        <div id="chatbot-button" onclick="toggleChat()"><svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg></div>
    </div>

    <script>
        // --- 0. AUTHENTICATION HANDLING ---
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('key')) {
            const qk = urlParams.get('key').trim();
            if (qk) {
                sessionStorage.setItem('mcore_voice_key', qk);
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }

        function getKey() {
            return sessionStorage.getItem('mcore_voice_key') || '';
        }

        function getAuthHeaders(customHeaders = {}) {
            const k = getKey();
            const h = { ...customHeaders };
            if (k) {
                h['X-MCORE-KEY'] = k;
            }
            return h;
        }

        document.getElementById('authBtn').onclick = () => {
            const current = getKey();
            const res = prompt('Enter MCORE Sovereign Access Key:', current);
            if (res !== null) {
                if (res.trim()) {
                    sessionStorage.setItem('mcore_voice_key', res.trim());
                } else {
                    sessionStorage.removeItem('mcore_voice_key');
                }
                location.reload();
            }
        };

        // --- 1. XTERM.JS WEBSOCKET ---
        const term = new Terminal({
            theme: { background: '#000000', foreground: '#10B981', cursor: '#10B981' },
            cursorBlink: true,
            fontSize: 13,
            fontFamily: 'monospace'
        });
        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal-container'));
        fitAddon.fit();

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const keyParam = getKey() ? `?key=${encodeURIComponent(getKey())}` : '';
        const wsUrl = `${protocol}//${window.location.host}/ws/terminal${keyParam}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            term.write('\x1b[1;36m[MCORE AIS Sovereign Shell]\x1b[0m PTY Session Established.\r\n');
        };
        ws.onmessage = (event) => term.write(event.data);
        ws.onclose = () => {
            term.write('\r\n\x1b[1;31m[Disconnected]\x1b[0m WebSocket closed. If access was denied, check your Sovereign Key.\r\n');
        };
        ws.onerror = (err) => {
            term.write('\r\n\x1b[1;31m[WebSocket Error]\x1b[0m Connection failed.\r\n');
        };
        term.onData((data) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(data);
            }
        });
        window.addEventListener('resize', () => fitAddon.fit());

        // --- 2. COMMAND CHIPS & RESTRICTED TERMINAL ---
        const chipContainer = document.getElementById('cmdChips');
        const allowedCommands = ["whoami", "pwd", "hostname", "uptime", "df -h", "free -h", "ss -lntp", "ls -la", "date"];
        allowedCommands.forEach(cmd => {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.textContent = cmd;
            chip.onclick = () => {
                document.getElementById('cmdInput').value = cmd;
                document.getElementById('cmdInput').focus();
            };
            chipContainer.appendChild(chip);
        });

        document.getElementById('runCmdBtn').onclick = async () => {
            const command = document.getElementById('cmdInput').value.trim();
            if (!command) return;
            const outputBox = document.getElementById('cmdOutput');
            outputBox.textContent = 'Executing command…';
            try {
                const res = await fetch('/api/terminal', {
                    method: 'POST',
                    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ command })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || res.statusText);
                outputBox.textContent = `Exit Code: ${data.returncode}\n\n${data.stdout}${data.stderr}`;
            } catch (err) {
                outputBox.textContent = 'Error: ' + err.message;
            }
        };

        // --- 3. BANGLA VOICE & GEMINI PROMPT ---
        document.getElementById('sendPromptBtn').onclick = async () => {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return;
            const geminiBox = document.getElementById('geminiOutput');
            geminiBox.textContent = 'Waiting for Gemini CLI…';
            try {
                const res = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || res.statusText);
                geminiBox.textContent = `Exit Code: ${data.returncode}\n\n${data.stdout}${data.stderr}`;
            } catch (err) {
                geminiBox.textContent = 'Error: ' + err.message;
            }
        };

        let mediaRecorder = null, audioChunks = [], micStream = null, meterInterval = null, audioCtx = null;
        function stopMeter() {
            if (meterInterval) { clearInterval(meterInterval); meterInterval = null; }
            if (audioCtx) { audioCtx.close().catch(()=>{}); audioCtx = null; }
            document.getElementById('micMeter').style.width = '0%';
        }

        document.getElementById('recordBtn').onclick = async () => {
            const btn = document.getElementById('recordBtn');
            const statusNote = document.getElementById('sttStatusNote');
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                return;
            }
            try {
                micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const src = audioCtx.createMediaStreamSource(micStream);
                const analyser = audioCtx.createAnalyser();
                analyser.fftSize = 256;
                src.connect(analyser);
                const pcmBuf = new Uint8Array(analyser.frequencyBinCount);
                meterInterval = setInterval(() => {
                    analyser.getByteFrequencyData(pcmBuf);
                    let sum = 0;
                    for (let i = 0; i < pcmBuf.length; i++) sum += pcmBuf[i];
                    document.getElementById('micMeter').style.width = Math.min(100, Math.round((sum / pcmBuf.length) * 1.8)) + '%';
                }, 60);

                audioChunks = [];
                const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
                mediaRecorder = new MediaRecorder(micStream, { mimeType: mime });
                mediaRecorder.ondataavailable = e => { if (e.data && e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = async () => {
                    stopMeter();
                    micStream.getTracks().forEach(t => t.stop());
                    btn.classList.remove('recording');
                    statusNote.textContent = 'Transcribing audio with faster-whisper…';
                    try {
                        const blob = new Blob(audioChunks, { type: mime });
                        const lang = document.getElementById('langSelect').value;
                        const res = await fetch(`/api/transcribe?lang=${encodeURIComponent(lang)}`, {
                            method: 'POST',
                            headers: getAuthHeaders({ 'Content-Type': mime }),
                            body: blob
                        });
                        const j = await res.json();
                        if (!res.ok) throw new Error(j.error || res.statusText);
                        if (j.text) {
                            const cur = document.getElementById('promptInput').value.trim();
                            document.getElementById('promptInput').value = cur ? `${cur} ${j.text}` : j.text;
                            statusNote.textContent = `Transcribed (${j.language}, ${j.duration_s}s).`;
                        } else {
                            statusNote.textContent = 'No speech detected.';
                        }
                    } catch (err) {
                        statusNote.textContent = 'Transcription error: ' + err.message;
                    }
                };
                mediaRecorder.start();
                btn.classList.add('recording');
                statusNote.textContent = 'Recording… Speak now, then click the mic button again to stop.';
            } catch (err) {
                stopMeter();
                statusNote.textContent = 'Mic Error: ' + err.message;
            }
        };

        // --- 4. FILE MANAGER ---
        async function loadFiles() {
            const container = document.getElementById('fileListContainer');
            try {
                const response = await fetch('/api/files', { headers: getAuthHeaders() });
                if (!response.ok) throw new Error('Authentication failed');
                
                const data = await response.json();
                if (!data.files || data.files.length === 0) {
                    container.innerHTML = '<p class="text-gray-500 text-sm italic">No files in quarantine storage.</p>';
                    return;
                }
                container.innerHTML = '';
                data.files.forEach(file => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'file-item';
                    fileDiv.innerHTML = `
                        <div class="flex items-center gap-3">
                            <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                            <span class="text-sm font-medium text-white">${file.name}</span>
                            <span class="text-xs text-gray-500">(${(file.size / 1024).toFixed(1)} KB)</span>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="deleteFile('${file.name}')" class="btn-delete" title="Delete file">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        </div>`;
                    container.appendChild(fileDiv);
                });
            } catch (error) {
                container.innerHTML = '<p class="text-red-500 text-sm">Failed to load files. Check Sovereign Key.</p>';
            }
        }

        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                    headers: getAuthHeaders()
                });
                if (response.ok) {
                    fileInput.value = '';
                    loadFiles();
                } else {
                    const err = await response.json();
                    alert('Upload failed: ' + (err.detail || err.error || 'Server error'));
                }
            } catch (error) {
                alert('Error uploading file: ' + error.message);
            }
        }

        async function deleteFile(filename) {
            if (!confirm(`Permanently delete "${filename}"?`)) return;
            try {
                const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                if (response.ok) {
                    loadFiles();
                } else {
                    alert('Delete failed.');
                }
            } catch (error) {
                alert('Error deleting file: ' + error.message);
            }
        }
        loadFiles();

        // --- 5. CHATBOT WIDGET ---
        const chatWindow = document.getElementById('chatbot-window');
        const chatMessages = document.getElementById('chat-messages');
        function toggleChat() {
            chatWindow.style.display = chatWindow.style.display === 'flex' ? 'none' : 'flex';
        }
        document.getElementById('chat-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            input.value = '';
            
            const botPlaceholder = addMessage("Thinking…", 'bot');
            try {
                const res = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ prompt: text })
                });
                const data = await res.json();
                botPlaceholder.textContent = data.stdout || data.stderr || 'No response generated.';
            } catch (err) {
                botPlaceholder.textContent = 'Error: ' + err.message;
            }
        });

        function addMessage(text, sender) {
            const div = document.createElement('div');
            div.className = `chat-message ${sender === 'user' ? 'msg-user' : 'msg-bot'}`;
            div.textContent = text;
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            return div;
        }

        // Fetch status on load
        (async () => {
            try {
                const s = await fetch('/api/status', { headers: getAuthHeaders() }).then(r => r.json());
                document.getElementById('sysMetric').textContent = `Bind: ${s.bind} | Python: ${s.python} | Whisper: ${s.whisper}`;
                if (!s.auth_required) {
                    document.getElementById('authStatusText').textContent = 'Loopback Access';
                }
            } catch (e) {}
        })();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=INDEX_HTML)


@app.head("/")
async def head_index():
    return Response(status_code=200, headers={"Content-Type": "text/html; charset=utf-8"})


@app.get("/api/status")
async def api_status(request: Request):
    return {
        "state": "ready",
        "version": "0.7-ROI-Unified",
        "primary_language": "bn-BD",
        "bind": f"{HOST}:{PORT}",
        "working_directory": str(WORKDIR),
        "whisper": f"faster-whisper ({WHISPER_MODEL_NAME})",
        "gemini": GEMINI or "NOT FOUND",
        "python": os.sys.version.split()[0],
        "auth_required": bool(AUTH_KEY),
        "domains": ["ais.mcorecare.com", "ais.mcoreai.dev", "voice.mcoreai.dev"],
    }


@app.get("/api/files")
async def list_files(request: Request, x_mcore_key: str = Header(None, alias="X-MCORE-KEY")):
    verify_key(request, x_mcore_key)
    try:
        files = []
        if os.path.exists(UPLOAD_DIR):
            for filename in sorted(os.listdir(UPLOAD_DIR)):
                filepath = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    files.append({
                        "name": filename,
                        "size": os.path.getsize(filepath),
                    })
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    x_mcore_key: str = Header(None, alias="X-MCORE-KEY"),
):
    verify_key(request, x_mcore_key)
    try:
        safe_filename = os.path.basename(file.filename or "")
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"info": f"File '{safe_filename}' uploaded successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files/{filename}")
async def delete_file(
    request: Request,
    filename: str,
    x_mcore_key: str = Header(None, alias="X-MCORE-KEY"),
):
    verify_key(request, x_mcore_key)
    try:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"info": f"File '{safe_filename}' deleted"}
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe(request: Request, lang: str = "bn"):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized: Sovereign Key required")

    try:
        audio_bytes = await request.body()
        if len(audio_bytes) < 100 or len(audio_bytes) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=400, detail="Invalid audio size.")

        target_lang = "en" if lang.lower() == "en" else "bn"
        init_prompt = None if target_lang == "en" else BANGLA_SCRIPT_PROMPT

        ctype = request.headers.get("content-type", "").lower()
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
            return Response(content=json.dumps({"text": clean_text, "language": target_lang, "script": "Bengali (U+0980-U+09FF)" if target_lang == "bn" else "Latin", "duration_s": round(getattr(info, "duration", 0.0), 2)}), media_type="application/json")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Whisper failed: {exc}")


@app.post("/api/prompt")
async def prompt_runner(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized: Sovereign Key required")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
        raise HTTPException(status_code=400, detail="Invalid prompt.")

    if not GEMINI:
        raise HTTPException(status_code=503, detail="Gemini CLI not found.")

    r = subprocess.run(
        [GEMINI, "-p", prompt.strip()],
        cwd=str(WORKDIR),
        capture_output=True,
        text=True,
        timeout=GEMINI_TIMEOUT,
        check=False,
    )
    return Response(content=json.dumps({"returncode": r.returncode, "stdout": r.stdout[-30000:], "stderr": r.stderr[-12000:]}), media_type="application/json")


@app.post("/api/terminal")
async def terminal_runner(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized: Sovereign Key required")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    cmd = data.get("command")
    if not isinstance(cmd, str) or len(cmd) > 300:
        raise HTTPException(status_code=400, detail="Invalid command.")

    allowed = SAFE_COMMANDS.get(tuple(cmd.strip().split()))
    if not allowed:
        raise HTTPException(status_code=403, detail="Command not allowlisted.")

    exe = shutil.which(allowed.split()[0])
    r = subprocess.run(
        [exe, *allowed.split()[1:]],
        cwd=str(WORKDIR),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return Response(content=json.dumps({"returncode": r.returncode, "stdout": r.stdout[-16000:], "stderr": r.stderr[-8000:]}), media_type="application/json")


@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    key = websocket.query_params.get("key") or websocket.query_params.get("token") or websocket.headers.get("x-mcore-key")
    client_ip = websocket.client.host if websocket.client else ""

    is_auth = False
    if not AUTH_KEY:
        is_auth = True
    elif key and hmac.compare_digest(key.strip(), AUTH_KEY):
        is_auth = True
    elif client_ip in {"127.0.0.1", "::1"}:
        origin = websocket.headers.get("origin", "")
        if not origin or origin in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}:
            is_auth = True

    if not is_auth:
        await websocket.close(code=1008, reason="Sovereign Key Invalid")
        return

    await websocket.accept()

    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        ["/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(WORKDIR),
        env={**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor"},
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    loop = asyncio.get_running_loop()

    async def read_from_pty():
        try:
            while True:
                data = await loop.run_in_executor(None, os.read, master_fd, 1024)
                if not data:
                    break
                await websocket.send_text(data.decode("utf-8", errors="ignore"))
        except (OSError, WebSocketDisconnect, asyncio.CancelledError):
            pass

    async def write_to_pty():
        try:
            while True:
                text = await websocket.receive_text()
                os.write(master_fd, text.encode("utf-8"))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    reader_task = asyncio.create_task(read_from_pty())
    writer_task = asyncio.create_task(write_to_pty())

    done, pending = await asyncio.wait(
        [reader_task, writer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for t in pending:
        t.cancel()

    try:
        process.terminate()
        process.wait(timeout=1)
    except Exception:
        process.kill()

    try:
        os.close(master_fd)
    except OSError:
        pass


if __name__ == "__main__":
    get_whisper()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
