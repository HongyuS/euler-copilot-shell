#!/usr/bin/env bash
# create_tarball.sh: create a tarball of current repo for RPM build.
set -euo pipefail

# Locate spec file relative to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SPEC_FILE="${REPO_ROOT}/distribution/linux/euler-copilot-shell.spec"

# Extract name and version from spec
NAME=$(grep -E '^Name:' "$SPEC_FILE" | awk '{print $2}')
VERSION=$(grep -E '^Version:' "$SPEC_FILE" | awk '{print $2}')

# Create build directory in repo
BUILD_DIR="${REPO_ROOT}/build"
mkdir -p "${BUILD_DIR}"
TARBALL="${NAME}-${VERSION}.tar.gz"

echo "Creating tarball ${TARBALL} in ${BUILD_DIR}" >&2
# Archive the current HEAD into tarball with proper prefix
git archive --format=tar.gz --prefix="${NAME}-${VERSION}/" -o "${BUILD_DIR}/${TARBALL}" HEAD

# 输出变量用于 build_rpm.sh 的 eval
echo "BUILD_DIR=${BUILD_DIR}"
echo "TARBALL=${TARBALL}"
