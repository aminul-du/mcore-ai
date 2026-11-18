from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import shutil

router = APIRouter()

SAFE_COMMANDS = {
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
    ("ss", "-lntp"): "ss -lntp"
}

class CommandRequest(BaseModel):
    command: str
    target_env: str = "local"

@router.post("/run")
async def run_command(req: CommandRequest):
    if req.target_env != "local":
        raise HTTPException(status_code=501, detail="Only 'local' execution adapter is implemented.")
    
    cmd_tuple = tuple(req.command.strip().split())
    if cmd_tuple not in SAFE_COMMANDS:
        raise HTTPException(status_code=403, detail="Command not allowlisted.")
    
    allowed = SAFE_COMMANDS[cmd_tuple]
    exe = shutil.which(allowed.split()[0])
    
    try:
        r = subprocess.run(
            [exe, *allowed.split()[1:]],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return {
            "returncode": r.returncode,
            "stdout": r.stdout[-16000:],
            "stderr": r.stderr[-8000:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
