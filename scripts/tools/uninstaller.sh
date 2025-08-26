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
# For each expected service, first check if the unit file exists, then stop if running and disable it.
for svc in framework rag; do
    unit="${svc}.service"
    # Check if the service unit exists on the system
    if systemctl list-unit-files --type=service | awk '{print $1}' | grep -Fxq "$unit"; then
        # If the service is active/running, stop it; otherwise just report
        if systemctl is-active --quiet "$unit"; then
            echo "Stopping $unit ..."
            systemctl stop "$unit" || true
        else
            echo "$unit is not running."
        fi
        # Attempt to disable the unit (may already be disabled)
        echo "Disabling $unit ..."
        systemctl disable "$unit" || true
    else
        echo "$unit not found; skipping."
    fi
done

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

echo "Uninstalling built-in MCP servers ..."
# Check for running systrace-mcpserver services and stop/disable them if present.
services=$(systemctl list-units --type=service --state=running | awk '{print $1}' | grep -E '^systrace-mcpserver' || true)
if [ -n "$services" ]; then
    for service in $services; do
        echo "Stopping $service ..."
        systemctl stop "$service" || true
        echo "Disabling $service ..."
        systemctl disable "$service" || true
    done
else
    echo "No running systrace-mcpserver services found."
fi

dnf remove -y sysTrace-* || true
dnf remove -y mcp-servers-perf mcp-servers-remote-shell || true

echo "Uninstallation complete."
