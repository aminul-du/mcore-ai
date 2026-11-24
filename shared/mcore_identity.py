#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ID_DIR = Path("/home/mcoreai/.config/mcore-identity")
PRIV_PATH = ID_DIR / "node_ed25519.pem"
PUB_PATH = ID_DIR / "node_ed25519.pub"
META_PATH = ID_DIR / "identity.json"
NODE_ID = "MCORE-FDR-AIS-001"

def ensure_identity() -> dict:
    ID_DIR.mkdir(parents=True, exist_ok=True)
    if not PRIV_PATH.exists():
        priv = Ed25519PrivateKey.generate()
        PRIV_PATH.write_bytes(
            priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        PRIV_PATH.chmod(0o600)
        pub_raw = priv.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        PUB_PATH.write_text(base64.b64encode(pub_raw).decode("ascii") + "\n", encoding="utf-8")
    pub_b64 = PUB_PATH.read_text(encoding="utf-8").strip()
    fp = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest()[:16].upper()
    meta = {
        "node_id": NODE_ID,
        "organization": "Meticulous Core Ltd. (MCore)",
        "algorithm": "Ed25519",
        "fingerprint": f"SHA256:{fp}",
        "public_key_b64": pub_b64,
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta

def sign_service_headers(service_name: str) -> dict:
    meta = ensure_identity()
    priv = serialization.load_pem_private_key(PRIV_PATH.read_bytes(), password=None)
    ts = str(int(time.time()))
    msg = f"{NODE_ID}:{service_name}:{ts}".encode("utf-8")
    sig = base64.b64encode(priv.sign(msg)).decode("ascii")
    return {
        "X-MCore-Node-ID": NODE_ID,
        "X-MCore-Service": service_name,
        "X-MCore-Fingerprint": meta["fingerprint"],
        "X-MCore-Timestamp": ts,
        "X-MCore-Signature": sig,
    }

if __name__ == "__main__":
    print(json.dumps(ensure_identity(), indent=2))
