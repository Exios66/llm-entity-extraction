#!/usr/bin/env bash
set -euo pipefail

───────────────────────── USER‑CONFIG ─────────────────────────
REPO_DIR="/Users/luciusjmorningstar/Downloads/llm-entity-extraction"   # ← repo root
NODE_USER="jburleson"
NODE_HOST="rogers-gpu-1.discovery.wisc.edu"
SERVICE_NAME="phoenix-app"
IMAGE_TAG="phoenix-app:latest"
────────────────────────────────────────────────────────────────

───────────────────── Build Docker image on the node ─────────────
echo "Building Docker image on $NODE_HOST…"
ssh -n "${NODE_USER}@${NODE_HOST}" <<'EOS'
cd "${REPO_DIR}"
docker build -t "${IMAGE_TAG}" .
EOS
echo "✅ Docker image built."

────────────────── Install systemd unit on the node ─────────────
echo "Installing systemd unit on $NODE_HOST…"
ssh -n "${NODE_USER}@${NODE_HOST}" <<'EOS'
cat >~/phoenix-app.service <<'EOF2'
[Unit]
Description=Phoenix App running in Docker
After=network.target docker.service
Requires=docker.service

[Service]
Restart=always
User=${NODE_USER}
WorkingDirectory=${REPO_DIR}
ExecStartPre=/usr/bin/docker pull hexpm/elixir:1.13-alpine
ExecStart=/usr/bin/docker run --rm --name ${SERVICE_NAME} -p 4000:4000 ${IMAGE_TAG}
ExecStop=/usr/bin/docker stop ${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF2

sudo mv ~/phoenix-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ${SERVICE_NAME}
EOS
echo "✅ systemd unit installed and started."

────────────────── Start reverse tunnel (port 80) ───────────────
echo "Starting reverse SSH tunnel (public port 80 → 4000)…"
ssh -N -R 80:localhost:4000 "${NODE_USER}@${NODE_HOST}" &
TUNNEL_PID=$!
echo "✅ Reverse tunnel running (PID $TUNNEL_PID)."

────────────────── Verify everything is up ─────────────────────
echo "✔️  Phoenix app should now be reachable at:"
echo "    • http://localhost:4000   (local port‑forward)"
echo "    • http://<public‑IP-or‑domain> (reverse tunnel on port 80)"
