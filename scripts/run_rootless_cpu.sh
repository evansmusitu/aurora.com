#!/usr/bin/env bash
# Manually run ONLY on approved, provisioned, rootless Podman host.
# This script NEVER creates cloud resources, provisions GPUs or contacts a paid API.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 APPROVED_JOB_JSON EXPECTED_JOB_SHA256 EXISTING_OUTPUT_DIR" >&2
  exit 2
fi
command -v podman >/dev/null || { echo 'Podman missing' >&2; exit 2; }
job="$(realpath -- "$1")"
expected="$2"
output="$(realpath -- "$3")"
if [ -L "$1" ] || [ ! -f "$job" ] || [ ! -d "$output" ] || [ -L "$3" ]; then
  echo 'Job and output must be existing non-symlink files/directories' >&2
  exit 2
fi
[[ "$expected" =~ ^[a-f0-9]{64}$ ]] || { echo 'Invalid hash' >&2; exit 2; }
actual="$(sha256sum "$job" | awk '{print $1}')"
[ "$actual" = "$expected" ] || { echo 'Job digest mismatch' >&2; exit 2; }
# Must be prepared from trusted source and verified beforehand; no implicit pull.
image='localhost/musitu-blender-cpu-worker:4.5.14-prototype'
podman image exists "$image" || { echo 'Approved local image missing' >&2; exit 2; }
# Do not expose NVIDIA devices or Kubernetes/service identity tokens.
exec podman run --rm --pull=never --network=none --read-only \
  --userns=keep-id --user "$(id -u):$(id -g)" \
  --memory=4g --cpus=2 --pids-limit=128 \
  --cap-drop=all --security-opt=no-new-privileges \
  --tmpfs /tmp:rw,nodev,nosuid,size=64m \
  --mount "type=bind,src=${job},dst=/input/job.json,ro=true" \
  --mount "type=bind,src=${output},dst=/results,rw=true" \
  "$image" --job /input/job.json --expected-sha256 "$expected" \
  --output-root /results --blender /opt/blender/blender \
  --device CPU --cpu-threads 2 --timeout-seconds 180
