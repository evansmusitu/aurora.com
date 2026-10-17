# MUSITU Studio — Approved-Host Worker (CPU First)

**Status:** Enterprise hardening prototype, not a deployed production render farm or live GPU service. This adds a dedicated single-use render worker to the previously verified `musitu.blender.job.v1` contract. It does not weaken or replace the existing schema validation.

## Guarantees provided by the application

- Exactly one fully validated, **SHA-256-bound** job file per run. The worker refuses unapproved mutations, symlinked input, unsupported Blender paths, and reused job IDs.
- Atomic output directory per job. No overwrite or silent retry, even after a failure.
- No shell interpolation, no inherited tokens or credentials, `--factory-startup`, fixed CPU rendering in the existing Blender scene executor, 2-thread application limit, at most 600-second timeout, and a per-file 64 MiB size ceiling. The job schema also caps objects, animation tracks, location, dimensions and frames.
- Independent verification of scene.blend, scene.glb and preview.png; every completed job has a retained worker receipt with `VERIFIED` or `FAILED` state. GPU use is disabled and recorded as unverified.
- GPU acceleration is not enabled or attested by this CPU worker.\n
## Security boundary — MUST enforce outside Python

The worker *is not an isolation mechanism*. A trusted administrator must run it as an unprivileged service in an enterprise-approved rootless container/VM, with **network denied**, no service tokens, read-only job/source mounts, distinct writable output volume, and runtime-enforced CPU, RAM, disk/PID caps. Production input requires an upstream authenticated approval and immutable job digest. Container image provenance and Blender hash must be verified. Never expose the Python executor, Blender Python console or external shell to anonymous callers. Logs may contain source metadata and belong in restricted storage.

## Manual smoke test on an approved x64 Linux workstation

Blender 4.5.14 LTS must exist as a real executable. Before running, compute the exact job digest with `sha256sum examples/approved_demo.json` and create a private output root `mkdir -m 700 -p runs`.

```bash
python3 studio/enterprise_worker.py --job examples/approved_demo.json \
  --expected-sha256 "$(sha256sum examples/approved_demo.json | awk '{print $1}')" \
  --output-root runs --blender /opt/blender/blender --timeout-seconds 180 --cpu-threads 2
```

A passing job produces `runs/<job_id>/artifacts/{scene.blend,scene.glb,preview.png,evidence.json,verification.json}` plus `worker_receipt.json` and a bounded process log. For a legitimate retry, issue a fresh job ID and new approved digest; never silently overwrite evidence.

## Commercial/GPU boundary

- **No GPU allocation or payment has been authorized or performed.** Do not deploy to paid GPU instances, even where a free-trial credit is offered without a hard provider-enforced spending guard.
- GitHub-hosted Actions CI is restricted to bounded *development integration tests* (software verification), not customer rendering, a 24/7 worker, or commercial compute.
- CPU and GPU results must be distinguished. Merely seeing a GPU in `gpu_probe.py` is **not** proof that Cycles rendered on it. Enabling CUDA/OptiX render paths needs a separate, independently verified authorization and provider decision.
