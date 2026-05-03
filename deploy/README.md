# Deploying GGI Policy to k8s

This directory holds the canonical kustomize manifests and Flux image-automation
CRs for the policy-docs deployment. They are the **source of truth**; promotion
to `ggi_internals` is a `cp -r` away.

This deployment depends on three pieces of operational state that live outside
this repo. Set them up first:

## Prerequisites

### 1. Entra app registration

In the Azure portal (or via Microsoft Graph PowerShell):

1. **Microsoft Entra ID → App registrations → New registration**
   - Name: `ggi-policy-docs`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: `Web` → `https://policy.ggenomics.internal/oauth2/callback`
2. After creation, capture from **Overview**:
   - `Application (client) ID` (a GUID)
   - `Directory (tenant) ID` (a GUID)
3. **Certificates & secrets → New client secret** with a 24-month expiry.
   Capture the *Value* immediately — it disappears after page navigation.
4. **API permissions** must include at least `openid`, `profile`, `email`. These
   are part of the default `User.Read` permission grant; no additional consent
   needed.
5. **Token configuration → Add optional claim → ID token → email**. Without
   this, oauth2-proxy's `--email-domain=ggenomics.com` filter has nothing to
   match against.

### 2. DNS record

Allocate `policy.ggenomics.internal` and point it at the cluster's
ingress-nginx LoadBalancer internal IP:

```
policy.ggenomics.internal.    300    IN    A    <ingress-nginx LB IP>
```

Confirm the airflow ingress uses the same `internal-ca` ClusterIssuer; if it
uses a different issuer name, update `cert-manager.io/cluster-issuer:` in
`apps/policy-docs/ingress.yaml` to match.

### 3. Vault entry

Generate a 32-byte cookie secret:

```bash
openssl rand -base64 32
```

Then write the four-key entry:

```bash
vault kv put secret/policy-docs/oauth2-proxy \
    tenant_id=<directory-id-from-step-1.2> \
    client_id=<application-id-from-step-1.2> \
    client_secret=<value-from-step-1.3> \
    cookie_secret=<output-of-openssl-above>
```

Confirm the `VaultAuth` CR named `vault-auth` exists in the `vault` namespace
and grants the `policy-docs/oauth2-proxy` ServiceAccount permission to read
`secret/policy-docs/oauth2-proxy`. If your cluster uses a different
VaultAuth name (mirror airflow), update `vaultAuthRef:` in
`apps/policy-docs/vault-static-secret.yaml`.

## Promotion to `ggi_internals`

The cluster's Flux watches `GGenomics/ggi_internals`, not this repo. To deploy:

```bash
# From the GGI-POLICY repo root, with ggi_internals checked out as a sibling.
cp -r deploy/apps/policy-docs ../ggi_internals/GitOps/k8s/prod/apps/policy-docs
cp -r deploy/flux/image-automation ../ggi_internals/<flux-bootstrap-path>/image-automation
```

Replace `<flux-bootstrap-path>` with whichever directory holds your cluster's
Flux bootstrap CRs (often `clusters/prod/flux-system/` or similar — match
where airflow's image-automation lives if applicable).

Open a PR in `ggi_internals` titled `feat(apps): add policy-docs`.

When that PR merges, Flux:

1. Reconciles the `policy-docs` namespace, ServiceAccounts, Deployment,
   Service, Ingress, oauth2-proxy, and VaultStaticSecret.
2. VSO syncs the Vault entry into the `oauth2-proxy` k8s Secret.
3. cert-manager provisions a TLS cert for `policy.ggenomics.internal`.
4. Image-automation begins watching `ghcr.io/ggenomics/ggi-policy-site` and
   updates the Deployment's `image:` tag whenever a higher `main-{N}` is
   published.

## Smoke verification

After Flux reconciles, from a workstation that resolves
`policy.ggenomics.internal`:

```bash
# 1. DNS resolves.
dig +short policy.ggenomics.internal

# 2. TLS cert is valid.
curl -sI https://policy.ggenomics.internal/ | head -1
# Expected: HTTP/2 302 (redirect to /oauth2/start)

# 3. Auth flow lands on Microsoft.
curl -sIL -o /dev/null -w '%{url_effective}\n' \
    https://policy.ggenomics.internal/
# Expected: a https://login.microsoftonline.com/.../oauth2/v2.0/authorize?... URL

# 4. From a browser, sign in. You should land back on the home page with
#    "GGI Policy Library" in the title.

# 5. Confirm Flux picked up the latest image:
kubectl -n policy-docs get deployment policy-docs -o jsonpath='{.spec.template.spec.containers[0].image}'
# Expected: ghcr.io/ggenomics/ggi-policy-site:main-{N} where {N} is current

# 6. Confirm oauth2-proxy is healthy:
kubectl -n policy-docs logs deployment/oauth2-proxy --tail=20 | head
# Expected: no error stack traces; possibly some "OIDC discovery" + ping logs
```

## TODO(operator) markers

Search `deploy/` for `TODO(operator)` and confirm each placeholder against
your cluster:

```bash
grep -rn "TODO(operator)" deploy/
```

Common adjustments:

- `cert-manager.io/cluster-issuer: internal-ca` — confirm the ClusterIssuer
  name. Mirror what airflow uses.
- `vaultAuthRef: vault-auth` and Vault `mount: secret` — confirm the VaultAuth
  CR name + KV mount path match the airflow pattern.
- `sourceRef: { name: flux-system }` in `image-update-automation.yaml` —
  confirm the GitRepository name pointing at `ggi_internals`.
- The image-reflector may need a pull secret for ghcr.io; uncomment
  `secretRef: { name: ghcr-pull }` in `image-repository.yaml` if so.

After confirming and adjusting, the manifests are ready to promote.
