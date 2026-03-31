# Docker Compose OpenSSL Error Fix

## Problem

When running `docker compose`, you encounter this error:

```
AttributeError: module 'lib' has no attribute 'X509_V_FLAG_NOTIFY_POLICY'
```

This occurs due to incompatibility between old system-installed `pyOpenSSL` and newer `cryptography` packages.

## Root Cause

- Your system has `docker compose` 1.25.0 (old version from Ubuntu repos)
- It depends on system Python packages (`python3-openssl`, `python3-cryptography`)
- Recent updates created version conflicts between these packages

## Solutions

### Solution 1: Upgrade to Docker Compose V2 (Recommended)

Docker Compose V2 is a standalone binary that doesn't depend on Python packages.

```bash
# Remove old docker compose
sudo apt remove docker compose

# Install Docker Compose V2 plugin
sudo apt update
sudo apt install docker compose-plugin

# Verify installation
docker compose version
```

**Important:** The command changes from `docker compose` to `docker compose` (space instead of hyphen).

Update your scripts:
- `docker compose up -d` → `docker compose up -d`
- `docker compose down` → `docker compose down`
- `docker compose logs` → `docker compose logs`

### Solution 2: Fix Python Package Versions

If you must keep the old docker compose:

```bash
# Option A: Upgrade pyOpenSSL (recommended)
sudo apt remove python3-openssl
sudo pip3 install pyOpenSSL==22.1.0

# Option B: Downgrade cryptography (if Option A doesn't work)
sudo pip3 install cryptography==36.0.2 --force-reinstall
```

### Solution 3: Install docker compose via pip

```bash
# Remove system docker compose
sudo apt remove docker compose

# Install latest via pip
sudo pip3 install docker compose

# Verify
docker compose --version
```

## Verification

After applying any solution, test with:

```bash
# For Docker Compose V2
docker compose version
docker compose ps

# For old docker compose
docker compose --version
docker compose ps
```

## Updating Project Scripts

If you choose Solution 1 (Docker Compose V2), update these files:

### manage.py
Replace `docker compose` with `docker compose` in subprocess calls.

### Shell scripts
- `docker-authorize.sh`
- `docker-dev-access.sh`
- `fix-permissions.sh`

Replace all instances of `docker compose` with `docker compose`.

### Batch files (Windows)
- `docker-authorize.bat`
- `docker-dev-access.bat`
- `fix-permissions.bat`

Replace all instances of `docker compose` with `docker compose`.

## Recommended Approach

We strongly recommend Solution 1 (Docker Compose V2) because:
- It's the modern, officially supported version
- No Python dependency conflicts
- Better performance and features
- Active development and security updates
- Docker Compose V1 reached end-of-life in June 2023

## References

- [Docker Compose V2 Documentation](https://docs.docker.com/compose/cli-command/)
- [pyOpenSSL Issue #1143](https://github.com/pyca/pyopenssl/issues/1143)
- [Migration Guide](https://docs.docker.com/compose/migrate/)
