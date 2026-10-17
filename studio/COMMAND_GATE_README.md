# MUSITU Enterprise Studio — Restrained Blender Job Command Gate (prototype)

The **already verified real Blender 4.5 LTS CPU CI execution** is extended here to a constrained, machine-readable job contract. The goal is to prove that ChatGPT → versioned JSON → actual Blender → .blend/.glb/.png → independently checked evidence works without opening a free-form Python execution interface.

## Security and usage boundary

- Demonstration and software QA only. GitHub-hosted runners are NOT a general-purpose commercial render farm.
- The `approved_demo.json` fixture contains no confidential client data, images, external assets, credentials, or URLs.
- The command schema supports up to 30 cubes, cylinders, or spheres, seven fixed materials, 16 keyed rotations, capped dimensions, and 120 frames. Unknown fields, embedded code, filenames, duplicate JSON keys, unsafe identifiers, NaN, and Infinity are rejected.
- The Blender executor never opens a network connection, launches shell commands, reads credentials, installs add-ons, or runs arbitrary code from the job JSON.
- Each run uses pinned official Blender 4.5.14 (SHA-256 `9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3`).
- Source is developed on separate branches. No production service or external GPUs were provisioned.

## What is verified

1. Python validation and unit tests reject dangerous/malformed job shapes before Blender starts.
2. A real Blender process creates native `.blend`, GLB, preview PNG from a permitted JSON job.
3. `verify_job.py` independently checks hashes, headers, mesh count, frame animation export and preview dimensions.
4. GitHub Actions retains bounded evidence for development and testing (not a persistent asset service).

## Running on an enterprise-approved workstation

Install Blender 4.5 LTS and Python 3.12+. Validate the job with Python (using `studio/job_schema.py`) then run:

```bash
blender -b --factory-startup --threads 2 --python studio/execute_job.py -- --job examples/approved_demo.json --outdir outputs/demo
python studio/verify_job.py examples/approved_demo.json outputs/demo
```

Blender is the execution authority, not this ChatGPT session. For enterprise production use a dedicated approved worker with resource controls, secret isolation, access controls, jobs queue, audit receipts and backups. The $0 proof cannot establish continuous GPU/GUI access.
