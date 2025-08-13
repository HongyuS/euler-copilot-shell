#!/usr/bin/env bash
# create_tarball.sh: create a tarball of current repo for RPM build.
set -euo pipefail

# Locate spec file relative to repo root
SPEC_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/distribution/linux/euler-copilot-shell.spec"

# Extract name and version from spec
NAME=$(grep -E '^Name:' "$SPEC_FILE" | awk '{print $2}')
VERSION=$(grep -E '^Version:' "$SPEC_FILE" | awk '{print $2}')

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
TARBALL="${NAME}-${VERSION}.tar.gz"

echo "Creating tarball ${TARBALL} in ${BUILD_DIR}"
# Archive the current HEAD into tarball with proper prefix
git archive --format=tar.gz --prefix="${NAME}-${VERSION}/" -o "${BUILD_DIR}/${TARBALL}" HEAD

# Export variables for reuse by build_rpm.sh
# Usage: eval "$(./create_tarball.sh)"
echo "export BUILD_DIR=${BUILD_DIR}"
echo "export TARBALL=${TARBALL}"
