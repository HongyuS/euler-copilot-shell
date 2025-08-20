#!/usr/bin/env bash

# Uninstaller for openEuler Intelligence
# Run as root or with sudo on openEuler

# Check openEuler environment
if [ ! -f /etc/openEuler-release ]; then
    echo "Error: This script must be run on openEuler environment." >&2
    exit 1
fi

set -e

echo "Stopping services..."
systemctl stop framework || true
systemctl stop rag || true

echo "Removing packages..."
dnf remove -y openeuler-intelligence-* || true
dnf remove -y euler-copilot-framework euler-copilot-rag || true

echo "Cleaning deployment files..."
rm -rf /opt/copilot
rm -rf /usr/lib/euler-copilot-framework
rm -rf /etc/euler-copilot-framework

echo "Clearing user configs & cache logs..."
for home in /root /home/*; do
    cache_dir="$home/.cache/openEuler Intelligence/logs"
    if [ -d "$cache_dir" ]; then
        echo "Removing $cache_dir"
        rm -rf "$cache_dir"
    fi
    config_dir="$home/.config/eulerintelli"
    if [ -d "$config_dir" ]; then
        echo "Removing $config_dir"
        rm -rf "$config_dir"
    fi
done

echo "Removing configuration template..."
rm -f /etc/openEuler-Intelligence/smart-shell-template.json

echo "Uninstallation complete."
