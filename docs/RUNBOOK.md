# MUSITU Studio v0.1 — deployment and recovery runbook

## Preflight acceptance requirements

1. Identify a specific legal company-owned or company-authorized Linux x64 workstation/server. Record host identity, owner, OS, patching, disk/RAM, operator, and commercial usage rights.
2. Confirm that software installation and access are permitted and that no new billable cloud resources are being created. The source code does NOT provide such a host.
3. Set up a private network (enterprise VPN), TLS reverse proxy and appropriate host firewall so that **port 8755 is never reachable from public internet**. Bind only to 127.0.0.1 at the host by default.
4. Require a nonroot host operator with access to the Docker/Podman engine and an isolated application data directory. Remember that access to the Docker socket is effectively root-equivalent on a rootful engine.
5. Review and independently verify container image signatures/base image digests, OS security policy, volume quotas and persistent storage.

## Startup

Generate token offline with `python -c 'import secrets;print(secrets.token_urlsafe(48))'`. Write it into `.env` privately (never GitHub/chat).

`./scripts/start_local.sh` prepares the local volume and starts one dashboard and one network-disabled CPU worker. Validate with `docker compose ps`, inspect internal service logs, and on the approved host browse http://127.0.0.1:8755.

Only the dashboard container gets `MUSITU_STUDIO_ADMIN_TOKEN`. The CPU worker receives no API token and has `network_mode:none`, caps dropped, `read_only` root filesystem, nonroot UID, 4 GiB memory, 2-CPU and 128-PID ceilings. Worker output lives in `./studio-data/runs`.

## Job lifecycle

Create a project, compose a strict JSON job (1–30 primitives), save as DRAFT, check its scope, then explicitly Approve. Only then does the offline worker atomically claim it. If execution is interrupted, mark it FAILED; create and approve a new job rather than overwriting evidence.

The browser displays `VERIFIED` only after Blender writes real `.blend`, GLB and PNG and a separate verifier confirms hashes and contents. Downloads recompute hashes against the worker receipt. Renders are CPU-only in v0.1.

## Backup and disaster recovery

Use `python -m studio.backup create --data ./studio-data --out /separate-safe-device/date.zip`. Always run `python -m studio.backup verify ZIP`. Restore into an empty folder only and independently validate that a project and completed renders can be opened. A simple same-disk ZIP is not an independent backup.

Backup transfer to another account/storage must be approved. Never upload tokens, confidential assets, keys, or private customer designs to public CI or archives.

## Monitoring and incident response

Look at `/healthz` only as an *API process* liveness signal, **not** proof a GPU or production host exists. Review `/api/audit`, worker receipts, disk space and container logs. On any authentication leak or unauthorized execution, stop containers, revoke/rotate the admin secret, preserve forensic logs, and perform a restore from a trusted backup.

## GPU gate

`studio/gpu_probe.py` only discovers hardware/Cycles capability; it cannot certify a GPU render. To enable production GPU rendering, require documented enterprise commercial rights, an approved NVIDIA GPU host and driver, matching Blender version, separate worker isolation and a successful actual CUDA or OptiX output with verified hashes. v0.1 intentionally does not implement a CUDA execution path to avoid false GPU-ready claims.

## Current go-live decision

**HOLD — software available, owned/approved host not evidenced.** The complete code can be built and operated on an appropriately qualified host, but no external commercial worker, TLS/VPN path or live GPU has been provisioned within this conversation. Do not advertise it as continuously hosted or enterprise security-certified.
