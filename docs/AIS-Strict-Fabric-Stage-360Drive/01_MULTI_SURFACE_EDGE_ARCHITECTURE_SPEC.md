---
id: MCORE-SPEC-003
title: Multi-Surface Edge Architecture & Engine Evaluation
author_id: MCORE-FDR-AIS-001
status: verified
domain_scope: isolated-mcore
quantization_profile: L0-Lossless
last_reviewed: 2026-11-20
---

# 01. Multi-Surface Edge Architecture & Engine Evaluation
**Document Authority:** MCORE-AIS-ARCH-001  
**Owner:** Aminul Islam Shamim (AIS) | MCORE Architect Office  
**Classification:** Sovereign Enterprise Blueprint  

---

## 1. Executive Thesis: Why Vendor-Native Edge Engines Are Mandatory

While Cloudflare Workers and serverless CDNs provide zero-cost ingress, global caching, and DDoS defense, relying **exclusively** on serverless runtimes introduces critical limitations for enterprise AI and sovereign autonomy:
1. **CPU/Memory Constraints:** Cloudflare Workers enforce hard limits on execution time (50ms on Free, 30s on Paid) and memory (128MB), making local weights loading or high-batch on-device inference impossible.
2. **Cold Starts and Network Egress:** Offloading every speech token or semantic vector lookup to cloud APIs re-introduces network latency (100ms–400ms) and creates external availability dependencies.
3. **Hardware Acceleration Gap:** Cloudflare Workers AI runs in centralized Cloudflare data centers, not on the user's local NPU (Apple Neural Engine, Qualcomm Hexagon, Intel NPU, NVIDIA TensorRT).
4. **Data Sovereignty:** Enterprise workloads require zero-egress data processing where embeddings and speech never leave the private enclave or on-premises appliance.

By combining Cloudflare edge routing (QUIC, WAF, Tunnel) with **vendor-native multiplatform engines** (ExecuTorch, Kotlin Multiplatform, ONNX Runtime, Google AICore, Microsoft DirectML), the `/AIS` ecosystem achieves true **Multi-Surface Portability**: code and quantized models run identically across iOS, Android, macOS, Linux, Windows, Bare-Metal servers, and WebAssembly.

---

## 2. Side-by-Side Comparison: AI & Edge Deployment Engines

| Dimension | Cloudflare Workers AI | PyTorch ExecuTorch | ONNX Runtime (Mobile/Web) | Google AICore / MediaPipe | Kotlin Multiplatform (KMP) | Sovereign Bare-Metal (MCORE L1) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Execution Surface** | Cloudflare Edge PoP | On-Device (iOS/Android/Embedded) | Browser (WASM/WebGPU) & OS | Android System Service / Web | Native Desktop/Mobile Shared | Debian 13 Bare-Metal / WSL2 |
| **Typical Latency** | 120ms - 350ms | 5ms - 25ms | 10ms - 40ms | 8ms - 30ms | Near-Zero (JNI/Native C) | < 5ms (Local IPC/UDS) |
| **Zero-Cost Feasibility** | 10k neurons/day free tier | 100% Free (Device Compute) | 100% Free (Client GPU/CPU) | 100% Free (On-Device Gemini Nano) | 100% Free (Native Binary) | $0 Cloud Bill (Owned Compute) |
| **Quantization Support** | FP8, INT8 (Cloud Hosted) | INT4, INT8, FP16 (Custom delegate) | INT4, INT8, FP16, TensorRT | Gemini Nano INT4, MediaPipe Tasks | Wraps C++ Quantized Runtimes | AWQ, GPTQ, GGUF, CT2, INT8 |
| **Offline Autonomy** | No (Requires Internet) | Yes (100% Offline) | Yes (Browser Cached Model) | Yes (Local OS Daemon) | Yes (Bundled Binary) | Yes (Local LAN / Air-Gapped) |
| **Bengali Phonetics (TTS/STT)** | MeloTTS / Whisper-Turbo | FastSpeech2 / Whisper-Tiny INT4 | Web Speech API / Sherpa-ONNX | Gemini Nano Text / MediaPipe ASR | Native C++ Piper/VITS bindings | faster-whisper + Silero + VITS |
| **Portability Rating** | Web / HTTP API only | Mobile, Embedded, Microcontrollers | Cross-Platform (WASM, Windows, Linux) | Android & Chromium ecosystem | Unified Business Logic & Bindings | Linux Server / Container / POSIX |

---

## 3. High-Performance Vector Caching & Semantic Retrieval

To avoid repetitive model invocations, `/AIS` implements a two-tier vector caching architecture:
- **L1 In-Memory Semantic Cache:** Employs cosine-similarity thresholds (e.g., threshold > 0.94) using a lightweight embedded vector index (`sqlite-vec` or memory-mapped HNSW). Frequent user inquiries resolve in < 2ms without hitting LLM inference.
- **L2 Sovereign Distributed Vector Store:** Backed by local Qdrant instance (`127.0.0.1:6333`) with INT8 scalar quantization, reducing RAM footprint by 75% while maintaining 98.7% recall.
- **Multi-Surface Synchronization:** Vector embeddings computed on edge devices synchronize asynchronously with the primary MCORE knowledge plane over end-to-end encrypted QUIC tunnels.

---

## 4. Kotlin Multiplatform (KMP) + Monorepo ExecuTorch Design Pattern

```
                       +-----------------------------------+
                       |    /AIS Monorepo Unified Core     |
                       |    (Kotlin Multiplatform + C++)   |
                       +-----------------+-----------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
+--------v--------+             +--------v--------+             +--------v--------+
|   iOS / macOS   |             |     Android     |             |   Web / Linux   |
| Swift / Cocoa   |             |   Jetpack / NDK |             | Next.js / POSIX |
| ExecuTorch Core |             | Google AICore   |             | ONNX WebGPU / C |
+-----------------+             +-----------------+             +-----------------+
```

- **Shared State & Contract Engine:** All state machines, reading mode sentence chunkers, audio stream orchestrators, and network retry loops reside in a single shared KMP module.
- **Pluggable Audio Delegates:**
  - On Web: Falls back seamlessly to Web Speech API / Cloudflare Workers AI.
  - On Android: Binds to Google AICore Gemini Nano + On-Device Speech Recognizer.
  - On iOS / macOS: Binds to Apple CoreML / ExecuTorch Metal delegate.
  - On Linux / Debian L1: Binds to Silero VAD + Faster-Whisper CT2.
