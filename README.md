# DECILLION: THE ONE 1D E2E

**Status: review-branch software prototype.** Decillion (`10^33`) is a long-horizon scale aspiration, **not** a verified parameter count, training result, or deployed model. The initial `main` commit only initializes the repository; implementation is on `review/e2e-foundation-20260920`.

## Run on Windows PowerShell

```powershell
$ErrorActionPreference = 'Stop'
$repo = Join-Path $HOME 'DECILLION-THE-ONE-1D-E2E'
if (-not (Test-Path "$repo\.git")) { git clone https://github.com/AdvanceDisrto/DECILLION-THE-ONE-1D-E2E.git $repo; if ($LASTEXITCODE -ne 0) { throw 'Clone failed' } }
git -C $repo fetch origin review/e2e-foundation-20260920
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git -C $repo status --short
# Review local changes before checking out; this command does not reset or delete anything.
git -C $repo switch --track origin/review/e2e-foundation-20260920
if ($LASTEXITCODE -ne 0) { throw 'Switch failed; inspect existing branch/worktree' }
Push-Location $repo
try {
    python -B -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python -B decillion_one.py 'Explain the architecture' --out receipt-local.json
    # Without an explicit provider this intentionally exits 2 and writes a not_executed receipt.
} finally { Pop-Location }
```

If the review branch already exists locally, switch to it only after reviewing `git status`; do not reset or overwrite local work.

## Provider contract

Set `I_ONE_PROVIDER_ENDPOINT` to an explicitly trusted HTTPS URL or loopback HTTP URL accepting `POST` JSON `{ "request_id": "...", "prompt": "..." }` and returning `{ "request_id": "same id", "output": "text" }`. Set `I_ONE_PROVIDER_TOKEN` only if the provider requires a bearer token; do not commit credentials. Run `python -B decillion_one.py 'Your prompt' --out receipt-unique.json`. No endpoint means **no inference**; a configured endpoint's response is **not proof of native i™ model weights**.

Optional `I_ONE_RECEIPT_KEY` adds a local HMAC-SHA256 integrity tag. It is **not** an Ed25519 signature, Decillion storage integration, independent attestation, correctness certification, or model provenance. A receipt records request, outcome, timestamp, and SHA-256 digest; verification remains `not_verified` until independently supported. Do not use this prototype to execute arbitrary commands or claim production security.

## Verification

`python -B -m unittest discover -s tests -v` exercises absent-provider behavior, loopback provider contract, integrity tampering, optional HMAC, insecure endpoint rejection, and empty prompt rejection. GitHub Actions runs syntax checks and the same tests. Test execution and CI status must be observed before declaring PASS. No merges or deployments are performed by this implementation.
