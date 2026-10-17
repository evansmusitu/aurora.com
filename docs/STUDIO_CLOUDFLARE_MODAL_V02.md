# MUSITU Studio v0.2 — GitHub / Cloudflare / Modal

**Status: source implemented; production resources and provider budget authority NOT verified.** This is an integration candidate, not a live production or a billing promise.

## Existing project assets
- Canonical versioned source is isolated on this **private branch**. This branch inherits prior MUSITU Studio v0.1 and its proven CPU Blender scene executor.
- Existing MUSITU Axiom uses GitHub Actions, Cloudflare and Modal. **Do not modify the Axiom Worker, production D1, R2, Modal app, routes, or existing secrets.** Always create dedicated studio resources.
- All controls default to CLOSED; no Modal CPU/GPU calls, R2/D1 provisioning or dashboard deployment are activated by a Git push.

## Components
1. `edge/`: Cloudflare Worker + responsive browser UI, D1 project/job/audit tables, R2 verified files, no external JS or CDN.
2. `modal/`: authenticated Modal ASGI job endpoint; bounded Blender CPU worker and separately guarded T4/CUDA worker; callback carries SHA-256 attestation and outputs.
3. `studio/`: existing declarative validation, Blender scene generation, and verifier, with strictly opt-in CUDA renderer.
4. `edge/tests/`: pure Node tests; CI runs tests and an actual bounded Blender CPU smoke render for software QA only.

## Provider spending and authorization — blocking gates
- GitHub Actions remains **software QA** only, never a commercial render farm.
- Modal Starter includes a compute credit but is **pay-as-you-go above credits**. Software budgets, max-containers, and timeouts are not provider-enforced zero-spend guarantees. Before deploying, an authorized person must inspect workspace **spend limits** and verify a real zero-out-of-pocket control; else the GPU and CPU dispatch must remain off.
- Cloudflare D1 and R2 may bill according to the existing Cloudflare account/plan; inspect actual account entitlements, storage and row limits before provisioning.
- `edge/wrangler.jsonc` intentionally contains a placeholder database_id and `workers_dev=false`: setup must be deliberate.
- Dispatch additionally requires Cloudflare `ENABLE_RENDER_DISPATCH=true`, Cloudflare secret `BUDGET_GUARD_APPROVED=true`, and Modal secret `STUDIO_BILLING_GUARD_APPROVED=1` after provider budget confirmation. GPU also requires `GPU_EXECUTION_APPROVED=true` and Modal `STUDIO_GPU_GATE_ON_MODAL=1`.
- `STUDIO_MODAL_URL` must be exact HTTPS URL of the Modal **submit_asgi** endpoint with `/jobs` suffix and `*.modal.run` hostname.
- Cloudflare `STUDIO_ADMIN_TOKEN`, `STUDIO_MODAL_CONTROL_KEY`, `STUDIO_MODAL_CALLBACK_KEY` must be distinct randomly generated >=32-character secrets. Modal secret names: `STUDIO_MODAL_CONTROL_KEY`, `STUDIO_CALLBACK_TOKEN`, `STUDIO_CALLBACK_URL`, and spending guards as above. Callback token equals Cloudflare's `STUDIO_MODAL_CALLBACK_KEY` and callback URL is https://<studio-domain>/internal/callback.
- Require and verify Cloudflare Access authorization in front of the dashboard for production; the bearer token is **only** a second control in this pilot. Do not embed tokens in HTML, GitHub, screenshots or static JS.

## Provisioning checklist for authorized account administrator
1. Confirm existing GitHub/Cloudflare/Modal account permissions and hard billing controls, **read-only**. No automatic secret copying from Axiom.
2. Create NEW R2 bucket `musitu-studio-v02-assets`, NEW D1 database `musitu-studio-v02` in the approved Cloudflare account. Record the newly assigned D1 ID in `edge/wrangler.jsonc`. Never reuse the Axiom production database.
3. From `edge/`, run `npm install`, `npx wrangler d1 migrations apply musitu-studio-v02 --remote` and only after approval `npx wrangler deploy`. Bind a **new** Cloudflare hostname/route and configure Cloudflare Access.
4. Install secrets with `wrangler secret put` for Cloudflare; do not commit credentials. Modal `modal secret create musitu-studio-v02 ...` in approved account. Keep both dispatch gates closed.
5. Review Modal image/D1/R2 anticipated charges and verify $0 spending cap at PROVIDER level. If absent, **NO-GO** for any render jobs; the dashboard remains read-only/approval capable.
6. With approval, from project root `modal deploy modal/studio_modal.py`, record verified endpoint; configure Cloudflare endpoint and callback; run authenticated/unauthenticated tests.
7. Run one approved *CPU* scene through browser. Require D1 COMPLETED, native .blend, .glb, .png, verified hashes, downloadable R2 files; then separately GPU qualification with actual NVIDIA T4 Cycles CUDA and positive `gpu_verified` evidence.
8. Test duplicate submissions, cross-origin rejection, callback wrong key/hash/device, restart/recovery, rollback and backup before any enterprise service designation.

## Scope limits of v0.2
- One studio administrator token, not enterprise multi-user RBAC; an external Cloudflare Access team policy must be configured.
- The Modal callback uses a bounded inline file transfer (total 5 MB) for small scenes, not large production assets. Larger production work requires direct, authenticated, time-limited R2 uploads from Modal with integrity receipts.
- Asynchronous results may arrive after a failed edge request; D1 conditional state transitions prevent most false promotions. A provider-hosted queue with retries, dead-letter handling, idempotent per-object writes, and stronger recovery is required for high availability.
- Commercial full-load BIM/CAD, collaborative multi-tenant projects, large assets, and GPU performance are **not certified**.

## Verification
`cd edge && node --test tests/*.test.mjs`, `python -m compileall -q modal studio`.
The isolated GitHub CI workflow executes a full CPU Blender smoke render; its logs and evidence are authoritative for actual execution results.

## Source and provider documentation
https://developers.cloudflare.com/workers/wrangler/configuration/
https://developers.cloudflare.com/workers/runtime-apis/bindings/
https://modal.com/docs/sdk/py/latest/App
https://modal.com/pricing
