#!/bin/sh
set -e

# Fix ownership of bind-mounted directories so appuser (UID 1000) can write to them.
# This is needed because Docker creates bind-mount dirs as root on the host.
chown -R appuser:appuser /app/logs /app/sessions /app/downloads 2>/dev/null || true

# Drop privileges and exec the CMD as appuser
exec gosu appuser "$@"
