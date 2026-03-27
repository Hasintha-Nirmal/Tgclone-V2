#!/bin/bash
# Fix Docker volume permissions for logs, sessions, data, and downloads

echo "Fixing directory permissions for Docker..."

# Create directories if they don't exist
mkdir -p logs sessions data downloads

# Set ownership to match Docker user (UID 1000)
echo "Setting ownership to UID 1000..."
sudo chown -R 1000:1000 logs sessions data downloads

# Set proper permissions
echo "Setting permissions..."
chmod -R 755 logs sessions data downloads

echo "Permissions fixed successfully!"
echo ""
echo "Directory permissions:"
ls -la logs sessions data downloads
