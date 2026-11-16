import asyncio
import json
import math
import os
import struct
import time
import urllib.request
from datetime import datetime, timezone
from livekit import rtc

TOKEN_URL = os.environ.get("TOKEN_URL", "https://sorbornoai.com/api/livekit/token")
FALLBACK_TOKEN_URL = "https://sorbornoai-web.pages.dev/api/livekit/token"
LIVEKIT_URL = "wss://livekit.mcoreai.dev"
ROOM_NAME = f"shorborno-e2e-probe-{int(time.time())}"
IDENTITY = "mcore-e2e-verifier"
EVIDENCE_PATH = "/srv/mcore/evidence/webrtc-e2e-verdict.json"

def mint_token() -> tuple[str, float, str]:
    t0 = time.perf_counter()
    payload = json.dumps({"roomName": ROOM_NAME, "participantName": IDENTITY}).encode("utf-8")
    
    endpoints = [TOKEN_URL]
    if FALLBACK_TOKEN_URL not in endpoints:
        endpoints.append(FALLBACK_TOKEN_URL)
        
    last_err = None
    for ep in endpoints:
        try:
            req = urllib.request.Request(
                ep,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "MCore-E2E-Probe/1.0 (MCORE-FDR-AIS-001)"
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            token = data.get("token") or data.get("accessToken")
            if token:
                return token, latency_ms, ep
        except Exception as e:
            last_err = e
            continue
            
    raise RuntimeError(f"Token minting failed across all endpoints: {last_err}")

async def run_probe():
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "signature": "MCORE-FDR-AIS-001",
        "room": ROOM_NAME,
        "endpoints": {"token_api": TOKEN_URL, "signaling": LIVEKIT_URL},
        "metrics_ms": {},
        "agent_dispatched": False,
        "agent_identity": None,
        "remote_audio_received": False,
        "status": "FAILED"
    }

    # 1. Mint JWT from Cloudflare Pages Edge Function
    token, token_ms, active_ep = mint_token()
    report["endpoints"]["token_api"] = active_ep
    report["metrics_ms"]["token_mint"] = token_ms

    room = rtc.Room()
    agent_joined_evt = asyncio.Event()
    remote_audio_evt = asyncio.Event()
    t_connect_start = time.perf_counter()
    t_audio_pub = 0.0

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        report["agent_dispatched"] = True
        report["agent_identity"] = participant.identity
        report["metrics_ms"]["agent_dispatch"] = round((time.perf_counter() - t_connect_start) * 1000, 2)
        agent_joined_evt.set()

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            report["remote_audio_received"] = True
            if t_audio_pub > 0:
                report["metrics_ms"]["ttfa_roundtrip"] = round((time.perf_counter() - t_audio_pub) * 1000, 2)
            remote_audio_evt.set()

    # 2. Connect WebRTC PeerConnection over Cloudflare QUIC -> LiveKit SFU
    await room.connect(LIVEKIT_URL, token)
    report["metrics_ms"]["webrtc_ice_dtls_connect"] = round((time.perf_counter() - t_connect_start) * 1000, 2)

    # 3. Wait for shorborno-agent.service worker dispatch
    try:
        await asyncio.wait_for(agent_joined_evt.wait(), timeout=12.0)
    except asyncio.TimeoutError:
        report["error"] = "Timed out waiting for shorborno-agent dispatch"
        await room.disconnect()
        return report

    # 4. Publish 2.0s of 48kHz mono PCM audio frames to trigger Silero VAD + Bengali pipeline
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("bengali-probe-mic", source)
    await room.local_participant.publish_track(track)
    t_audio_pub = time.perf_counter()

    samples_per_frame = 480  # 10ms frame
    for frame_idx in range(200):  # 2.0 seconds
        pcm = bytearray(samples_per_frame * 2)
        for i in range(samples_per_frame):
            t = (frame_idx * samples_per_frame + i) / 48000.0
            # Modulated speech-band envelope (320Hz + 640Hz) to trigger Silero VAD speech probability
            sample = int(12000 * math.sin(2 * math.pi * 320 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)))
            struct.pack_into("<h", pcm, i * 2, sample)
        frame = rtc.AudioFrame(data=bytes(pcm), sample_rate=48000, num_channels=1, samples_per_channel=samples_per_frame)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)

    # 5. Await Agent Greeting / TTS Audio Track Response
    try:
        await asyncio.wait_for(remote_audio_evt.wait(), timeout=15.0)
        report["status"] = "PASS"
    except asyncio.TimeoutError:
        report["status"] = "PARTIAL_AGENT_JOINED_NO_TTS_TRACK"

    await room.disconnect()
    os.makedirs(os.path.dirname(EVIDENCE_PATH), exist_ok=True)
    with open(EVIDENCE_PATH, "w") as f:
        json.dump(report, f, indent=2)
    return report

if __name__ == "__main__":
    res = asyncio.run(run_probe())
    print(json.dumps(res, indent=2))
