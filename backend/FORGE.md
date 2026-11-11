# Deploy the EcoTrees backend to the Forge sandbox

The Forge kubeconfig (`team09.yml`) is a credential. It is ignored by Git; keep it private and do not upload it to GitHub or include it in support messages.

## What this deployment contains

- `api`: FastAPI backend, exposed through the Forge-required `app` Service at `https://team09.xtradot.co`.
- `finance-worker`: background webhook, expiry, and payout processing.
- `migrate-job`: one-off database migration runner.

The Kubernetes manifests use the public GitHub Container Registry image
`ghcr.io/obed-ojingwa/eco_trees`. The GitHub Actions workflow at
`.github/workflows/publish-forge-image.yml` builds and publishes a `linux/amd64`
image on pushes to `main` or `master`.

## Prerequisites

1. Apply the Supabase setup SQL and confirm the application role can connect. Use the `ecotrees` role for `DB_URL`; reserve the Supabase `postgres` role for `DB_MIGRATION_URL`.
2. Keep the connection strings out of Git. Prepare two ignored local files:
   - `backend/.env.forge` with `DB_URL`, `JWT_SECRET`, `INGEST_TOKEN`, `CARBON_SIGNING_KEY`, `FORGE_WEBHOOK_SECRET`, `PAYOUT_ENCRYPTION_KEY`, and `TREASURY_ACCOUNT`.
   - `backend/.env.forge-migration` with only `DB_MIGRATION_URL`.
3. Generate independent random values for the JWT, ingest, carbon signing, webhook, and payout-encryption secrets. The signing, webhook, and payout-encryption keys must each be at least 32 bytes. Keep the payout-encryption key backed up and unchanged.
4. Push this repository change to GitHub and wait for **Publish Forge backend image** to succeed.
5. In GitHub Packages, make `eco_trees` public so the Forge cluster can pull it without an image-pull secret. If the package must remain private, configure a `regcred` pull secret in the `team09` namespace and add `imagePullSecrets` to all three workload manifests.
6. Confirm `ghcr.io/obed-ojingwa/eco_trees:latest` exists before applying the manifests.

Do not use the development/example secrets from `.env.example` in the sandbox.

## Deploy from PowerShell

Run commands from the repository root. The following commands do not display secret values:

```powershell
$env:KUBECONFIG = (Resolve-Path .\team09.yml).Path
kubectl config current-context
kubectl get pods -n team09

kubectl create secret generic ecotrees-secrets `
  --namespace team09 `
  --from-env-file .\backend\.env.forge `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic ecotrees-migration `
  --namespace team09 `
  --from-env-file .\backend\.env.forge-migration `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply --namespace team09 -f .\backend\k8s\migrate-job.yaml
kubectl wait --for=condition=complete job/ecotrees-migrate -n team09 --timeout=300s
kubectl logs job/ecotrees-migrate -n team09

kubectl apply --namespace team09 -f .\backend\k8s\api.yaml
kubectl apply --namespace team09 -f .\backend\k8s\worker.yaml
kubectl rollout status deployment/api -n team09 --timeout=180s
kubectl rollout status deployment/finance-worker -n team09 --timeout=180s
kubectl get pods,services -n team09
```

The migration job name is fixed. Before rerunning it after a completed or failed run, remove only that job (`kubectl delete job ecotrees-migrate -n team09`) and then apply it again. The migration runner verifies migration checksums and safely skips migrations already recorded as applied.

## Verify the published service

```powershell
Invoke-RestMethod https://team09.xtradot.co/healthz
```

Expected response: `status = ok`. Also check pod events and logs if the API is not ready:

```powershell
kubectl describe pods -n team09
kubectl logs deployment/api -n team09
kubectl logs deployment/finance-worker -n team09
```

Use synthetic test data only. Do not send real personal, bank, BVN, NIN, or payment data to the sandbox.

## Current known limitations

- The local `DB_MIGRATION_URL` connects, but the runtime `DB_URL` currently fails Supabase password authentication for the existing `ecotrees` role. The role has database-connect and public-schema usage privileges. If this persists, rotate the application role password in the Supabase SQL Editor (never use the migration URL as the runtime URL):

  ```sql
  ALTER ROLE ecotrees WITH PASSWORD '<new-random-password>';
  ```

  Update `DB_URL` in the local backend environment and `backend/.env.forge` with that password URL-encoded, then recheck the application connection before creating the Kubernetes secret. Keep `DB_MIGRATION_URL` unchanged and private.
- The backend's live-bank adapter still returns `BANK_SCHEMA_UNCONFIRMED`; the guide is an operational summary, not the authoritative Sandbox API Mock Specification v2. Do not treat checkout or payout as working until the real sandbox contract is implemented and tested from inside Forge.
- Carbon registry integration is still configured as `mock`, and the current carbon parameters are illustrative placeholders.
- The Forge Kubernetes API has timed out during TLS handshakes, and Docker Desktop was unavailable during preparation. Resolve cluster/image-publishing prerequisites before treating the service as deployed.
