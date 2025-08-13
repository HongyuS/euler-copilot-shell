#!/usr/bin/env bash
# build_rpm.sh: build RPM package using the tarball created by create_tarball.sh
set -euo pipefail

# Determine script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Create the tarball and set BUILD_DIR and TARBALL
eval "$("${SCRIPT_DIR}"/create_tarball.sh)"
set +u
if [[ -z "${BUILD_DIR:-}" || -z "${TARBALL:-}" ]]; then
    echo "Error: BUILD_DIR 或 TARBALL 变量未设置，create_tarball.sh 执行失败。" >&2
    exit 1
fi
set -u

# Spec file path
SPEC_FILE="${REPO_ROOT}/distribution/linux/euler-copilot-shell.spec"

# Prepare RPM build directories under BUILD_DIR
mkdir -p "${BUILD_DIR}/"{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}

# Copy source tarball and spec into RPM tree
cp "${BUILD_DIR}/${TARBALL}" "${BUILD_DIR}/SOURCES/"
cp "${SPEC_FILE}" "${BUILD_DIR}/SPECS/"

# Build the RPMs
echo "Building RPM using topdir ${BUILD_DIR}"
rpmbuild --define "_topdir ${BUILD_DIR}" -ba "${BUILD_DIR}/SPECS/$(basename "${SPEC_FILE}")"

# Output locations
echo "RPM build complete."
echo "SRPMs: ${BUILD_DIR}/SRPMS"
echo "Binary RPMs: ${BUILD_DIR}/RPMS"
