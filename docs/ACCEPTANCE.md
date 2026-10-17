# Acceptance and limits — MUSITU Studio v0.1

A release is a **software package** only. A real service needs a paid-for-or-already-owned approved host, OS isolation, separate TLS/VPN access control, verified backup protection, and security review.

## Gate ledger

1. Input schema rejects free-form code, paths, extensions, external URLs; <=30 primitives and <=16 animation tracks.
2. Host API rejects malformed/duplicate JSON properties and restricts methods, login, sessions and manual approvals.
3. Job content is immutably named by server-generated ID and fingerprinted before approval, before worker execution.
4. Queue uses atomic SQLite claims and refuses concurrent worker launches; stale running jobs fail closed.
5. Worker starts external pinned Blender CPU binary with no inherited API secrets, CPU cap, timeout and independent verification. Operating-system isolation remains external.
6. Output asset downloads restricted to `VERIFIED`, named-only and checked against signed-in-DB worker receipt SHA and artifact hashes.
7. Backups use consistent SQLite snapshot, SHA manifest and clean-room-only restore.
8. Enterprise GPU, persistent hosting, remote desktop, tenant isolation, off-host backups, audit immutability and compliance are not achieved by this software test.

## Spending / terms

This project does not provision cloud machines, chargeable GPUs, domains, third-party APIs or persistent servers. The existing GitHub-hosted CI is exclusively a bounded software-development test. Do not use free Colab or Kaggle as commercial rendering workers. An administrator must obtain a written approval for a commercial-use-capable computing host and verify provider-enforced cost controls before production GPU work.
