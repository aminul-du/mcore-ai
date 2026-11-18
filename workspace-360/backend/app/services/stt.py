from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import tempfile
import threading
import os
from faster_whisper import WhisperModel

router = APIRouter()

WHISPER_MODEL_NAME = os.environ.get("MCORE_WHISPER_MODEL", "medium")
WHISPER_CACHE = os.environ.get("HF_HOME", "/srv/mcore/apps/voice-console/.cache")
BANGLA_SCRIPT_PROMPT = "বাংলায় শুদ্ধ বানানে লিখুন: আমার সোনার বাংলা, আমি তোমায় ভালোবাসি। ঢাকা, বাংলাদেশ।"

_whisper_model = None
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
            if mapped == 0x09B5: mapped = 0x09AC
            out.append(chr(mapped))
        else: out.append(ch)
    return "".join(out)

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), lang: str = Form("bn")):
    try:
        audio_bytes = await file.read()
        target_lang = "en" if lang == "en" else "bn"
        init_prompt = None if target_lang == "en" else BANGLA_SCRIPT_PROMPT

        suffix = ".wav" if file.filename.endswith(".wav") else ".webm"
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
            
            return {
                "text": clean_text,
                "language": target_lang,
                "duration_s": round(getattr(info, "duration", 0.0), 2)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
