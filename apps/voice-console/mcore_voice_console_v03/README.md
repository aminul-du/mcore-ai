# MCORE AIS Voice Console v0.3 — Standard Library Edition

**No `pip install` required.** Uses only Python standard-library modules. It invokes your already-installed Gemini CLI; it does not install Gemini CLI or copy credentials.

## Install on Debian 13

Run as your normal Linux user, not root. Assumes the ZIP is in `~/Downloads`.

```bash
sudo install -d -o "$USER" -g "$(id -gn)" -m 0750 /srv/mcore/apps/voice-console
cp ~/Downloads/mcore_voice_console_v03.zip /srv/mcore/apps/voice-console/
cd /srv/mcore/apps/voice-console
unzip -q mcore_voice_console_v03.zip
cd mcore_voice_console_v03
```

## Verify existing Gemini CLI (read-only)

```bash
whoami
command -v gemini
gemini --version
```

If `command -v gemini` prints a path, launch the app from the same user/session:

```bash
export MCORE_WORKDIR="$HOME"
python3 app/mcore_voice_console.py
```

Open `http://127.0.0.1:7860` in your browser. Stop with `Ctrl+C`.

## What is included

- Single-page localhost web UI
- Typed prompt submission to existing Gemini CLI using `gemini -p`
- Browser voice input where supported
- Separate restricted local command panel

## Important limitations

- The terminal panel is **not** a full interactive terminal/PTY. It runs one exact allowlisted command at a time: `pwd`, `whoami`, `id`, `hostname`, `uname -a`, `git status --short --branch`, `df -h`, `free -h`, `ls -la`, `date`.
- No arbitrary shell, pipes, redirects, file writes, `sudo`, or persistent terminal session.
- Browser speech recognition may use a browser vendor's remote service; local/offline speech recognition is not guaranteed.
- Python standard library means no third-party Python packages need installing. This does not mean OS packages or Gemini CLI are installed by this ZIP.
- The app inherits the environment of the Linux user who launches it. Existing Gemini/Vertex authentication remains outside this project.
- Gemini CLI may have its own tools and permissions. Configure them conservatively; this web UI does not bypass Gemini's own approval controls.
- Localhost binding only. Do not expose port 7860 to LAN, tunnel, or public internet.
- No systemd service, firewall rule, or existing configuration is changed.

Starter module; validate in a non-production workspace before relying on it.
