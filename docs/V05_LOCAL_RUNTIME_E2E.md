# Studio v0.5: local Cloudflare D1/R2 + genuine Blender artifact integration
This is an **offline/local Cloudflare Workers runtime integration proof**.
It runs `wrangler dev --local` and D1 migrations in a disposable runner;
a real Blender 4.5 LTS **CPU** software-QA render is then supplied as a
mocked Modal callback (Cloudflare endpoint receives real artifact bytes).
D1, R2, authentication, checksums, and download APIs run in Cloudflare's
local simulator. No real Cloudflare resources, Modal deployments, GPU
containers, third-party billing changes, or production domains are activated.
The SQL state flip to RUNNING is a local test fixture and **is not evidence
of a real Modal dispatch**.
The test keeps `ENABLE_RENDER_DISPATCH=false` and `GPU_EXECUTION_APPROVED=false`.
Production remains blocked pending account-authorized resource provisioning,
Cloudflare Access configuration, Modal budget guard evidence and authenticated
end-to-end provider execution.
