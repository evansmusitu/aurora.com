# MUSITU Studio v0.1 — enterprise 3D control-plane source

**Verified milestone:** Authenticated, local-only dashboard + durable project/job queue + manual approval + offline CPU Blender 4.5 LTS worker + SHA-256 output verification + backup and restore. **Not a production deployment or approved GPU host.** This package requires an approved existing host to keep the user's USD 0 infrastructure spending boundary.

## What is built

- Responsive Android-compatible dashboard: secure login, projects, job composer, review/approval, queue states, audit events, previews and `.blend`/GLB downloads.
- Strict `musitu.blender.job.v1` schema. Restricted materials, primitive geometry, keyframe animations. No arbitrary Python, files, URLs, shell commands, add-ons, or AI-produced scripts enter Blender from job specifications.
- SQLite transactional states `DRAFT → QUEUED → RUNNING → VERIFIED / FAILED`, or cancellation before start. Job identity and SHA-256-bound inputs; no silent retries, and interrupted executions fail closed.
- One network-denied, unprivileged CPU worker using real pinned Blender 4.5.14 LTS. Independent output validation, immutable-at-API-level job/approval history, max 2 Blender threads, 180s job limit, per-output file size limits.
- Local FastAPI service with 8-hour HttpOnly SameSite Strict sessions, CSRF, login throttling, strong token check, security headers, loopback-by-default CLI and restrictive host checks.
- Portable SHA-256-verified backup+restore (restore to clean directory only), including SQLite snapshot, job inputs and stored output artifacts.
- Local container compose/reference images, development-only GitHub Actions CI, automated unit and integration tests.

**Operational constraints:** This is a **single-administrator prototype**, not an SSO/IAM/multi-tenant production platform. The worker's Python code is not a sandbox: external `network_mode:none`, OS/container privileges, disk limits and access controls are necessary. Database audit events are append-only through APIs but are *not tamper-proof against filesystem administrators*. GPU detection does not certify CUDA rendering. GitHub-hosted Actions can verify software but is not a commercial render farm.

## 1) Fast local software test, no Blender required

On an existing enterprise-approved Python 3.12+ computer:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -v -s tests
export MUSITU_STUDIO_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python -m studio.cli --host 127.0.0.1 --port 8755 --data ./studio-data
```

Open `http://127.0.0.1:8755` on **that computer**. It is intentionally not exposed to the internet. Your phone can reach it only through an approved private access path (such as enterprise VPN plus TLS reverse proxy). Do not expose the endpoint publicly over plain HTTP.

The dashboard lets you create `DRAFT` jobs and approve them; jobs will stay `QUEUED` until the separately isolated Blender worker is provisioned on an allowed computing host.

## 2) Private CPU worker — approved host only

`compose.yaml` is a development deployment *reference* for a previously authorized Linux Docker host. It publishes the dashboard **only on host loopback** and starts one **network-disabled CPU worker**. It makes no paid infrastructure API calls and never requests GPUs:

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
# Paste generated token into MUSITU_STUDIO_ADMIN_TOKEN in .env, privately.
./scripts/start_local.sh
```

The docker build downloads official Blender 4.5.14 and verifies its pinned SHA-256 `9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3`. Its runtime worker is configured `network_mode: none`, all Linux capabilities dropped, nonroot user, read-only root FS, 4 GiB memory / 2 CPU / 128 PID caps. **Image digest verification, actual Podman rootless policy, volume/disk quotas, TLS, IAM and host qualification still need independent validation.** Do not label this composition enterprise-certified merely because it starts.

`Containerfile` builds do not authorize any cloud account or fee. Container engines and host operations may require an organization's infrastructure approvals.

## 3) Backup and restore

```bash
python -m studio.backup create --data ./studio-data --out /separate-safe-location/musitu-YYYYMMDD.zip
python -m studio.backup verify /separate-safe-location/musitu-YYYYMMDD.zip
python -m studio.backup restore /separate-safe-location/musitu-YYYYMMDD.zip --data ./empty-restoration-folder
```

A backup on the same disk does not provide disaster recovery. Copy to an approved independent storage location, protect it appropriately, and run a restore drill.

## 4) CLI worker development proof (not commercial use)

For bounded CI software tests only, the action workflow downloads pinned Blender on GitHub-hosted Actions, generates one permitted demonstration scene, and retains verification output. Production customer jobs **must not** run on GitHub-hosted Actions. User-facing interface is **not hosted** by this source repository.

## Status / go-live boundary

| Requirement | Current status |
| --- | --- |
| UI and authenticated API code | Implemented, tested locally |
| Persistent jobs, approval, failures, audit | Implemented, tested locally |
| CPU worker integration on GitHub CI | Development proof only; see execution receipt |
| Network-disabled container running on an owned host | **Not verified** |
| Real GPU Cycles render | **Not verified** |
| User/organization-owned approved 24/7 host | **Not evidenced** |
| Private TLS/VPN mobile access | **Not provisioned** |
| Enterprise SSO, multi-tenancy, backups off-host, incident response | **Not certified** |
| Unplanned cloud spending | **No cloud infrastructure ordered or activated** |

This package offers the software needed to stand up a private studio on a qualified host, while explicitly leaving production activation blocked until operator/provider evidence exists.
