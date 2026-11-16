import json
import os
import sys
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ.get("TARGET_URL", "https://sorbornoai-web.pages.dev")
SCREENSHOT_PATH = "/srv/mcore/evidence/browser-e2e-screenshot.png"
EVIDENCE_PATH = "/srv/mcore/evidence/browser-e2e-verdict.json"

def run_browser_e2e():
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "signature": "MCORE-FDR-AIS-001",
        "target_url": TARGET_URL,
        "token_api_status": None,
        "token_mint_latency_ms": None,
        "webrtc_connected": False,
        "webrtc_connection_time_ms": None,
        "canvas_rendered": False,
        "canvas_dimensions": None,
        "assistant_state": None,
        "screenshot_saved": False,
        "screenshot_path": SCREENSHOT_PATH,
        "console_events": [],
        "metrics_ms": {},
        "status": "FAILED"
    }

    t0_total = time.perf_counter()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--allow-file-access"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["microphone"]
        )
        page = context.new_page()

        t_token_start = 0.0
        t_webrtc_start = 0.0

        def handle_console(msg):
            text = msg.text
            report["console_events"].append({"type": msg.type, "text": text})
            if "connection state changed: connecting -> connected" in text:
                report["webrtc_connected"] = True
                if t_webrtc_start > 0:
                    report["webrtc_connection_time_ms"] = round((time.perf_counter() - t_webrtc_start) * 1000, 2)
                    report["metrics_ms"]["webrtc_connect"] = report["webrtc_connection_time_ms"]

        page.on("console", handle_console)

        def handle_response(response):
            nonlocal t_token_start
            if "/api/livekit/token" in response.url:
                report["token_api_status"] = response.status
                if t_token_start > 0:
                    latency = round((time.perf_counter() - t_token_start) * 1000, 2)
                    report["token_mint_latency_ms"] = latency
                    report["metrics_ms"]["token_mint"] = latency

        page.on("response", handle_response)

        # 1. Navigate to target frontend
        t_nav_start = time.perf_counter()
        t_token_start = time.perf_counter()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        report["metrics_ms"]["dom_load"] = round((time.perf_counter() - t_nav_start) * 1000, 2)
        t_webrtc_start = time.perf_counter()

        # 2. Wait for 3D Canvas element to mount
        try:
            canvas = page.wait_for_selector("canvas", state="visible", timeout=20000)
            if canvas:
                box = canvas.bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    report["canvas_rendered"] = True
                    report["canvas_dimensions"] = {"width": round(box["width"]), "height": round(box["height"])}
                    report["metrics_ms"]["canvas_mount"] = round((time.perf_counter() - t_nav_start) * 1000, 2)
        except Exception as e:
            report["error_canvas"] = str(e)

        # 3. Wait for WebRTC connection status
        max_wait = 15.0
        poll_start = time.perf_counter()
        while time.perf_counter() - poll_start < max_wait:
            if report["webrtc_connected"]:
                break
            time.sleep(0.5)

        # 4. Extract assistant UI state text if available
        try:
            state_el = page.query_selector("div.text-xl")
            if state_el:
                report["assistant_state"] = state_el.inner_text().strip()
        except Exception:
            pass

        # 5. Capture Screenshot for evidence
        os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
        page.screenshot(path=SCREENSHOT_PATH, full_page=True)
        report["screenshot_saved"] = os.path.exists(SCREENSHOT_PATH)

        browser.close()

    report["metrics_ms"]["total_duration"] = round((time.perf_counter() - t0_total) * 1000, 2)

    # 6. Evaluate verdict
    if report["token_api_status"] == 200 and report["webrtc_connected"] and report["canvas_rendered"]:
        report["status"] = "PASS"
    elif report["token_api_status"] == 200 and report["canvas_rendered"]:
        report["status"] = "PARTIAL_CANVAS_RENDERED"
    else:
        report["status"] = "FAILED"

    os.makedirs(os.path.dirname(EVIDENCE_PATH), exist_ok=True)
    with open(EVIDENCE_PATH, "w") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    res = run_browser_e2e()
    # Print clean summary and JSON
    print(json.dumps(res, indent=2))
    if res.get("status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)
