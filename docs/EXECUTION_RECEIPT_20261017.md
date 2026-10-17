# MUSITU Studio v0.1 — independently checked software execution receipt

Date: 2026-10-17 (UTC). Scope: GitHub Actions software-development proof ONLY.

## Source and remote software check

- Private source: `evansmusitu/musitu-foundry-forge`, isolated `experiments/studio-v0-1-20261017` branch.
- Sanitized integration test: `evansmusitu/aurora.com`, same isolated branch.
- Successful initial CI: https://github.com/evansmusitu/aurora.com/actions/runs/39026948349
- Python tests: **35 passed, 0 failures**. Python compilation and JavaScript syntax checks passed.
- Tested authentic Blender **4.5.14 LTS**, Linux x64 official archive SHA-256: `9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3`.
- Job record: `J_34514ba719ad51954d4418f4`.
- Actual worker state: `VERIFIED`, CPU-only, `gpu_verified=false`.
- Real Blender export result: **12 verified GLB meshes**, **3 animation clips**.

## Independent artifact readback and hash checks

- `scene.blend` 722,536 bytes, SHA-256 `d172dfbdf1ccd741a5b22969d5575af4b8266ae822581efae267acb7fce03f3e`.
- `scene.glb` 171,096 bytes, SHA-256 `0c49f549615988daa018475cfd0ea4d94ebc284728e5b3fde1fd313e481535c3`.
- `preview.png` 47,930 bytes, SHA-256 `aa3c182f6f50025149b1a212cdb294a1def0c2e4ce23828b782d8a0a59ca8771`.
- Proof ZIP SHA-256 `e82da48dff8d8ca27c57bab54c283a563a5ff7f531413192a9ddff8912ae2e53`.
- Retrieved GitHub Actions archive was independently inspected in a separate local runtime: ZIP integrity passed, `.blend`/GLB/PNG headers passed, all three SHA-256 values matched independent worker verification, and the worker receipt identified `gpu_verified=false`.

## Interface proof

- Browser-rendered desktop and Android preview screenshots were produced in local Chromium with **mock project data** and zero JS exceptions. These screenshots demonstrate UI layout only, not a public deployment.
- The real authenticated API and state machine were tested locally by FastAPI TestClient and Python unit tests. No remotely accessible, continuously hosted API was provisioned.

## Production launch gates remain CLOSED

- No enterprise-owned/approved persistent CPU or NVIDIA GPU host verified here.
- No real CUDA/OptiX Blender GPU render measured.
- Rootless runtime isolation, host networking, TLS/VPN authentication, filesystem quotas and off-host backups not tested on an enterprise host.
- No enterprise IAM/SSO/multi-user separation or independently immutable audit ledger.
- Hosted GitHub Actions is used only for software development/testing, **not** enterprise customer rendering or 24/7 hosting.
- No chargeable cloud resource was intentionally ordered or activated in this integration.

**Conclusion:** Software proof is accepted. Enterprise production activation: **NO-GO until authentic host/operator evidence exists.**
