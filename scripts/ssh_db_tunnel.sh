#!/usr/bin/env bash
# Simple helper to open an SSH tunnel to a remote PostgreSQL instance.
# Keeps the tunnel attached to this terminal; press Ctrl+C to close.

set -euo pipefail

SSH_USER=${DB_SSH_USER:-${DB_SSH_BASTION_USER:-}}
SSH_HOST=${DB_SSH_HOST:-${DB_SSH_BASTION_HOST:-}}
SSH_PORT=${DB_SSH_PORT:-22}
REMOTE_HOST=${DB_REMOTE_HOST:-127.0.0.1}
REMOTE_PORT=${DB_REMOTE_PORT:-5432}
LOCAL_PORT=${DB_LOCAL_PORT:-5442}
KEY_PATH=${DB_SSH_KEY_PATH:-}

if [ -z "$SSH_USER" ] || [ -z "$SSH_HOST" ]; then
  echo "Set DB_SSH_USER (or DB_SSH_BASTION_USER) and DB_SSH_HOST (or DB_SSH_BASTION_HOST) in your environment." >&2
  exit 1
fi

if [ -n "$KEY_PATH" ]; then
  # Expand leading tilde manually so ssh receives an absolute path.
  KEY_PATH="${KEY_PATH/#\~/$HOME}"
fi

SSH_CMD=(ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=3)

if [ -n "$KEY_PATH" ]; then
  SSH_CMD+=(-i "$KEY_PATH")
fi

SSH_CMD+=(-p "$SSH_PORT" -N -L "${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}" "${SSH_USER}@${SSH_HOST}")

echo "Opening SSH tunnel: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT} via ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
if [ -n "$KEY_PATH" ]; then
  echo "Using key: $KEY_PATH"
fi
echo "Keep this terminal open; press Ctrl+C to close the tunnel."

"${SSH_CMD[@]}"
