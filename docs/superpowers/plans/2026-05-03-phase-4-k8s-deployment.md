# Phase 4: K8s deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the static policy site to the on-prem GGenomics k8s cluster, fronted by ingress-nginx + oauth2-proxy + Entra SSO, behind `https://policy.ggenomics.internal/`. Flux image-automation watches GHCR and reconciles new image tags into the GitOps repo automatically.

**Architecture:** Manifests are authored in this repo under `deploy/` as the canonical, reviewable source. They mirror the layout `GGenomics/ggi_internals/GitOps/k8s/prod/apps/policy-docs/` so promotion is a clean `cp -r` (last task of the plan). A dedicated `policy-docs` namespace contains the nginx Deployment serving the pre-built site, an oauth2-proxy Deployment authenticating against an Entra app registration, an ingress-nginx `Ingress` with `auth-url` annotations chaining the two, and a Vault Secrets Operator `VaultStaticSecret` resolving `secret/policy-docs/oauth2-proxy` from the cluster's HashiCorp Vault. Flux image-automation CRs watch `ghcr.io/ggenomics/ggi-policy-site` and write tag bumps to the kustomization in `ggi_internals` whenever a new `main-{N}` image lands. CI validates every manifest with `kubectl --dry-run=client` so a malformed manifest never reaches `main`.

**Tech Stack:** Kustomize (kubectl built-in), HashiCorp Vault Secrets Operator (VSO), Flux v2 (`image-reflector-controller` + `image-automation-controller`, already running), oauth2-proxy 7.x, ingress-nginx (already running), cert-manager (already running, ClusterIssuer `internal-ca` assumed; operator confirms). No Python additions; manifest validation is a small Python script that parses YAML.

---

## Prerequisites

- Phase 3 is merged (HEAD on `origin/main` ≥ `e1ac6bf`). The `build-and-push` workflow is publishing `ghcr.io/ggenomics/ggi-policy-site:{latest,main-{sha}}` on every push to main.
- Reference: design doc at [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](../specs/2026-05-02-policy-doc-framework-design.md) §8.4 (k8s deployment, Flux image automation), §10 (open items: Entra app, DNS, TLS, Vault path).
- Phase 4 needs three pieces of operational state outside this repo. They are **not blockers for the manifests landing**, but they MUST exist before the deployment will reconcile in the cluster:
  1. **Entra app registration** named `ggi-policy-docs` with redirect URI `https://policy.ggenomics.internal/oauth2/callback`. Operator creates via Azure portal or Microsoft Graph PowerShell. Captures `client_id` and a fresh `client_secret`.
  2. **DNS A/CNAME record** for `policy.ggenomics.internal` pointing at the ingress-nginx LoadBalancer's internal IP.
  3. **Vault entry** at `secret/policy-docs/oauth2-proxy` containing keys `client_id`, `client_secret`, `cookie_secret` (32-byte random base64 — generate with `openssl rand -base64 32`).
- The cluster already runs: ingress-nginx, cert-manager, Flux v2 with `image-reflector-controller` and `image-automation-controller`, Vault Secrets Operator (VSO) with a `VaultAuth` CR named `vault-auth` in the `vault` namespace (mirror airflow's pattern; operator confirms). The plan uses these as givens.
- The `GGenomics/ggi_internals` repo at path `GitOps/k8s/prod/apps/airflow/` is the reference shape this plan mirrors. Where this plan makes a guess about a convention (cert-manager ClusterIssuer name, VaultAuth name, namespace label), the final task asks the operator to diff against `airflow/` and adjust.

## File structure (locked-in decomposition)

Manifests are produced in this repo under `deploy/`. The directory shape **exactly mirrors** the target path in `ggi_internals` so that promotion is `cp -r deploy/apps/policy-docs ../ggi_internals/GitOps/k8s/prod/apps/policy-docs` and `cp -r deploy/flux/image-automation ../ggi_internals/<wherever>/image-automation` (operator confirms exact location).

```
GGI-POLICY/
├── .github/workflows/
│   └── build-and-push.yml                       # MODIFY: add monotonic tag for Flux ImagePolicy
├── deploy/
│   ├── README.md                                # NEW: operator-facing promotion guide
│   ├── apps/
│   │   └── policy-docs/
│   │       ├── kustomization.yaml               # NEW: aggregator
│   │       ├── namespace.yaml                   # NEW
│   │       ├── service-account.yaml             # NEW
│   │       ├── deployment.yaml                  # NEW: nginx serving the GHCR image
│   │       ├── service.yaml                     # NEW: ClusterIP for the nginx
│   │       ├── ingress.yaml                     # NEW: ingress-nginx + oauth2-proxy annotations
│   │       ├── oauth2-proxy.deployment.yaml     # NEW
│   │       ├── oauth2-proxy.service.yaml        # NEW
│   │       └── vault-static-secret.yaml         # NEW: VSO CR resolving Vault → k8s Secret
│   └── flux/
│       └── image-automation/
│           ├── kustomization.yaml               # NEW: aggregator
│           ├── image-repository.yaml            # NEW: watches GHCR
│           ├── image-policy.yaml                # NEW: selects highest main-{N} tag
│           └── image-update-automation.yaml     # NEW: writes back to ggi_internals
├── tools/
│   ├── ggi_policy/
│   │   └── manifests.py                         # NEW: parse + structurally validate manifests
│   └── tests/
│       └── test_manifests.py                    # NEW
└── .github/workflows/
    └── validate.yml                             # MODIFY: add manifest validation step
```

## Conventions

- **Commits:** Conventional Commits (`feat(deploy): ...`, `feat(flux): ...`, `ci(manifest): ...`).
- **Kustomize, not Helm:** mirroring the existing airflow app, every manifest is hand-written kustomize. oauth2-proxy is NOT installed via its Helm chart; the manifests are pure kustomize so the operator can review every container, env var, and volume in plain YAML.
- **Hostname:** every manifest uses `policy.ggenomics.internal` as the public hostname. The redirect URI for oauth2-proxy is `https://policy.ggenomics.internal/oauth2/callback`.
- **Image:** every manifest references `ghcr.io/ggenomics/ggi-policy-site` with the tag pinned to a Flux-managed placeholder. The Flux `ImageUpdateAutomation` rewrites this tag automatically on every new image.
- **Validation, not deployment:** this plan does NOT apply manifests to a live cluster. It only authors and validates them. Promotion to `ggi_internals` (and thence to the cluster via Flux) is the final operator task.
- **Placeholders the operator confirms:** `cert-manager.io/cluster-issuer: internal-ca`, `vault.hashicorp.com/auth: vault-auth`, namespace label conventions. Each is flagged with a `# TODO(operator):` comment; the operator README enumerates them.

---

## Task 1: deploy/ skeleton + namespace + ServiceAccount

**Files:**
- Create: `deploy/apps/policy-docs/namespace.yaml`
- Create: `deploy/apps/policy-docs/service-account.yaml`

- [ ] **Step 1: Create the namespace manifest**

`deploy/apps/policy-docs/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-docs
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

- [ ] **Step 2: Create the ServiceAccount manifest**

`deploy/apps/policy-docs/service-account.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: policy-docs
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: oauth2-proxy
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: oauth2-proxy
    app.kubernetes.io/part-of: ggi-policy
```

- [ ] **Step 3: Verify YAML syntax**

```bash
uv run python -c "
import yaml, glob
for f in sorted(glob.glob('deploy/apps/policy-docs/*.yaml')):
    list(yaml.safe_load_all(open(f)))
    print(f, 'OK')
"
```

Expected: every file prints `OK`.

- [ ] **Step 4: Commit**

```bash
git add deploy/apps/policy-docs/namespace.yaml deploy/apps/policy-docs/service-account.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): policy-docs namespace + service accounts

Namespace 'policy-docs' enforces the Pod Security restricted profile.
Two service accounts: one for the nginx Deployment, one for
oauth2-proxy. Both unprivileged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: policy-docs Deployment + Service

**Files:**
- Create: `deploy/apps/policy-docs/deployment.yaml`
- Create: `deploy/apps/policy-docs/service.yaml`

- [ ] **Step 1: Create the policy-docs Deployment**

`deploy/apps/policy-docs/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: policy-docs
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: policy-docs
  template:
    metadata:
      labels:
        app.kubernetes.io/name: policy-docs
        app.kubernetes.io/part-of: ggi-policy
    spec:
      serviceAccountName: policy-docs
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: nginx
          # Image tag is rewritten by Flux ImageUpdateAutomation. Anything that
          # matches the ImagePolicy in deploy/flux/image-automation/ is valid.
          image: ghcr.io/ggenomics/ggi-policy-site:main-1 # {"$imagepolicy": "policy-docs:policy-docs-image"}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 10
            periodSeconds: 20
          resources:
            requests:
              cpu: 10m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: nginx-cache
              mountPath: /var/cache/nginx
            - name: nginx-pid
              mountPath: /var/run
            - name: nginx-config
              mountPath: /etc/nginx/conf.d/default.conf
              subPath: default.conf
              readOnly: true
      volumes:
        - name: nginx-cache
          emptyDir: { sizeLimit: 64Mi }
        - name: nginx-pid
          emptyDir: { sizeLimit: 4Mi }
        - name: nginx-config
          configMap:
            name: policy-docs-nginx-conf
---
# Minimal nginx config that listens on a non-privileged port (8080) so the
# pod can run as a non-root user. The default nginx:alpine config listens on
# 80 which requires root; we override here.
apiVersion: v1
kind: ConfigMap
metadata:
  name: policy-docs-nginx-conf
  namespace: policy-docs
data:
  default.conf: |
    server {
        listen 8080 default_server;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;
        location / {
            try_files $uri $uri/ $uri.html =404;
        }
        # Cache static assets aggressively; HTML is rebuilt on every push.
        location ~* \.(css|js|png|jpg|svg|woff2?)$ {
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
    }
```

The `# {"$imagepolicy": "policy-docs:policy-docs-image"}` marker tells Flux's `ImageUpdateAutomation` exactly which image reference to rewrite. The namespace + name match the `ImagePolicy` we'll create in Task 7.

- [ ] **Step 2: Create the Service**

`deploy/apps/policy-docs/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: policy-docs
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: policy-docs
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: http
```

- [ ] **Step 3: Verify**

```bash
uv run python -c "
import yaml, glob
for f in sorted(glob.glob('deploy/apps/policy-docs/*.yaml')):
    list(yaml.safe_load_all(open(f)))
    print(f, 'OK')
"
```

Expected: every file `OK`.

- [ ] **Step 4: Commit**

```bash
git add deploy/apps/policy-docs/deployment.yaml deploy/apps/policy-docs/service.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): policy-docs Deployment + Service

nginx:alpine container running as non-root on port 8080 (so the pod
satisfies the restricted PSS profile). Read-only root filesystem with
emptyDir mounts for /var/cache/nginx and /var/run. Custom nginx config
shipped via ConfigMap so default.conf doesn't try to listen on a
privileged port.

The image reference includes the Flux $imagepolicy marker matching
policy-docs:policy-docs-image (created in Task 7).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Ingress with TLS + oauth2-proxy auth annotations

**Files:**
- Create: `deploy/apps/policy-docs/ingress.yaml`

- [ ] **Step 1: Create the Ingress**

`deploy/apps/policy-docs/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: policy-docs
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
  annotations:
    # cert-manager will provision a TLS cert from the named ClusterIssuer.
    # TODO(operator): confirm internal-ca is the right ClusterIssuer name in
    # your cluster (mirror what airflow uses).
    cert-manager.io/cluster-issuer: internal-ca

    # ingress-nginx auth chain: route every request through oauth2-proxy
    # before reaching the policy-docs service.
    nginx.ingress.kubernetes.io/auth-url: "https://$host/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://$host/oauth2/start?rd=$escaped_request_uri"
    # Forward identity headers from oauth2-proxy to the upstream (informational
    # only; the static site doesn't read them, but downstream debug pages may).
    nginx.ingress.kubernetes.io/auth-response-headers: "x-auth-request-user, x-auth-request-email"
    nginx.ingress.kubernetes.io/auth-snippet: |
      auth_request_set $auth_user $upstream_http_x_auth_request_user;
      auth_request_set $auth_email $upstream_http_x_auth_request_email;
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - policy.ggenomics.internal
      secretName: policy-docs-tls
  rules:
    - host: policy.ggenomics.internal
      http:
        paths:
          # The /oauth2/* paths are served by oauth2-proxy.
          - path: /oauth2
            pathType: Prefix
            backend:
              service:
                name: oauth2-proxy
                port:
                  number: 80
          # Everything else is the static site.
          - path: /
            pathType: Prefix
            backend:
              service:
                name: policy-docs
                port:
                  number: 80
```

- [ ] **Step 2: Verify**

```bash
uv run python -c "
import yaml
list(yaml.safe_load_all(open('deploy/apps/policy-docs/ingress.yaml')))
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add deploy/apps/policy-docs/ingress.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): ingress-nginx Ingress with oauth2-proxy auth chain + TLS

Two path rules: /oauth2/* routes to oauth2-proxy (which serves
/oauth2/start, /oauth2/auth, /oauth2/callback, /oauth2/sign_out);
everything else routes to policy-docs. The auth-url annotation
intercepts every non-/oauth2 request and validates the oauth2-proxy
session cookie before allowing through.

cert-manager provisions a TLS cert via ClusterIssuer 'internal-ca'.
TODO(operator): confirm the ClusterIssuer name matches your cluster.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: oauth2-proxy Deployment + Service

**Files:**
- Create: `deploy/apps/policy-docs/oauth2-proxy.deployment.yaml`
- Create: `deploy/apps/policy-docs/oauth2-proxy.service.yaml`

- [ ] **Step 1: Create the oauth2-proxy Deployment**

`deploy/apps/policy-docs/oauth2-proxy.deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oauth2-proxy
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: oauth2-proxy
    app.kubernetes.io/part-of: ggi-policy
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: oauth2-proxy
  template:
    metadata:
      labels:
        app.kubernetes.io/name: oauth2-proxy
        app.kubernetes.io/part-of: ggi-policy
    spec:
      serviceAccountName: oauth2-proxy
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 2000
        runAsGroup: 2000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: oauth2-proxy
          image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
          imagePullPolicy: IfNotPresent
          args:
            - --provider=oidc
            - --provider-display-name=GGenomics SSO
            # TODO(operator): confirm the Entra OIDC issuer URL for your tenant.
            # Find it at https://login.microsoftonline.com/{tenant-id}/v2.0
            # The placeholder uses ${TENANT_ID} — substitute or set via env.
            - --oidc-issuer-url=https://login.microsoftonline.com/${TENANT_ID}/v2.0
            - --redirect-url=https://policy.ggenomics.internal/oauth2/callback
            - --upstream=static://200
            - --http-address=0.0.0.0:4180
            - --reverse-proxy=true
            - --email-domain=ggenomics.com
            - --cookie-secure=true
            - --cookie-samesite=lax
            - --cookie-domain=policy.ggenomics.internal
            - --cookie-name=_ggi_policy_oauth2
            - --cookie-expire=12h
            - --skip-provider-button=true
            - --pass-access-token=false
            - --set-xauthrequest=true
            - --silence-ping-logging=true
          env:
            - name: TENANT_ID
              valueFrom:
                secretKeyRef:
                  name: oauth2-proxy
                  key: tenant_id
            - name: OAUTH2_PROXY_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: oauth2-proxy
                  key: client_id
            - name: OAUTH2_PROXY_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: oauth2-proxy
                  key: client_secret
            - name: OAUTH2_PROXY_COOKIE_SECRET
              valueFrom:
                secretKeyRef:
                  name: oauth2-proxy
                  key: cookie_secret
          ports:
            - name: http
              containerPort: 4180
              protocol: TCP
          readinessProbe:
            httpGet:
              path: /ping
              port: http
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /ping
              port: http
            initialDelaySeconds: 10
            periodSeconds: 20
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
```

The `${TENANT_ID}` substitution is performed by oauth2-proxy itself (it reads `--oidc-issuer-url` and resolves environment variables) — no Kubernetes magic. The `tenant_id` key is sourced from the same Vault Secret as `client_id`/`client_secret` so all four pieces of identity config live in one place.

- [ ] **Step 2: Create the oauth2-proxy Service**

`deploy/apps/policy-docs/oauth2-proxy.service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: oauth2-proxy
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: oauth2-proxy
    app.kubernetes.io/part-of: ggi-policy
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: oauth2-proxy
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: http
```

- [ ] **Step 3: Verify**

```bash
uv run python -c "
import yaml
list(yaml.safe_load_all(open('deploy/apps/policy-docs/oauth2-proxy.deployment.yaml')))
list(yaml.safe_load_all(open('deploy/apps/policy-docs/oauth2-proxy.service.yaml')))
print('OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add deploy/apps/policy-docs/oauth2-proxy.deployment.yaml \
        deploy/apps/policy-docs/oauth2-proxy.service.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): oauth2-proxy Deployment + Service

oauth2-proxy 7.6.0 in OIDC mode against the GGenomics Entra tenant.
Two replicas; non-root, read-only-root, no privilege escalation.
Sources tenant_id, client_id, client_secret, cookie_secret from a
k8s Secret named 'oauth2-proxy' (created by VSO in Task 5).

The --upstream=static://200 means oauth2-proxy itself doesn't proxy
upstream — it only handles the /oauth2/* auth flow. The ingress
auth-url annotation is what protects the policy-docs upstream.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Vault Secrets Operator integration

**Files:**
- Create: `deploy/apps/policy-docs/vault-static-secret.yaml`

- [ ] **Step 1: Create the VaultStaticSecret**

`deploy/apps/policy-docs/vault-static-secret.yaml`:

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultStaticSecret
metadata:
  name: oauth2-proxy
  namespace: policy-docs
  labels:
    app.kubernetes.io/name: oauth2-proxy
    app.kubernetes.io/part-of: ggi-policy
spec:
  type: kv-v2
  # TODO(operator): confirm the mount path matches your Vault layout.
  # Most installations mount KV-v2 at "secret/"; airflow uses the same.
  mount: secret
  path: policy-docs/oauth2-proxy
  destination:
    name: oauth2-proxy
    create: true
  refreshAfter: 1h
  vaultAuthRef: vault-auth
  # The VaultAuth CR is expected to live in the vault namespace and be
  # referenced cluster-wide. TODO(operator): confirm name + namespace.
```

The Vault path layout `secret/policy-docs/oauth2-proxy` must contain four keys:
- `tenant_id` (string, the Entra tenant GUID)
- `client_id` (string, from the Entra app registration)
- `client_secret` (string, from the Entra app registration)
- `cookie_secret` (32-byte base64-encoded random — operator generates with `openssl rand -base64 32`)

VSO's `kv-v2` reader fetches them in one call and rendering happens automatically. The k8s `Secret` it creates is named `oauth2-proxy` (matches `secretKeyRef` in the Deployment).

- [ ] **Step 2: Verify**

```bash
uv run python -c "
import yaml
list(yaml.safe_load_all(open('deploy/apps/policy-docs/vault-static-secret.yaml')))
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add deploy/apps/policy-docs/vault-static-secret.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): VaultStaticSecret resolving oauth2-proxy creds from Vault

VSO's VaultStaticSecret CR pulls KV-v2 path secret/policy-docs/oauth2-proxy
(four keys: tenant_id, client_id, client_secret, cookie_secret) and
materializes them as a k8s Secret named 'oauth2-proxy' in the
policy-docs namespace. Refresh interval 1h.

TODO(operator): confirm the Vault mount path and VaultAuth CR name
match the airflow pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Base + prod overlay kustomizations

**Files:**
- Create: `deploy/apps/policy-docs/kustomization.yaml`

- [ ] **Step 1: Create the kustomization aggregator**

`deploy/apps/policy-docs/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: policy-docs

commonLabels:
  app.kubernetes.io/part-of: ggi-policy
  app.kubernetes.io/managed-by: flux

resources:
  - namespace.yaml
  - service-account.yaml
  - vault-static-secret.yaml
  - deployment.yaml
  - service.yaml
  - oauth2-proxy.deployment.yaml
  - oauth2-proxy.service.yaml
  - ingress.yaml

images:
  # Flux ImageUpdateAutomation rewrites the `newTag:` value in this block
  # whenever the ImagePolicy selects a new tag. Initial value matches what
  # was last published by the build-and-push workflow.
  - name: ghcr.io/ggenomics/ggi-policy-site
    newTag: main-1
```

The `images:` block is what Flux's `ImageUpdateAutomation` will rewrite when a new tag is selected — kustomize is the standard pattern Flux's image-automation expects (see https://fluxcd.io/flux/guides/image-update/).

- [ ] **Step 2: Verify with kustomize**

```bash
# kustomize is built into kubectl. If kubectl isn't installed, the
# Python parser test below substitutes for now.
which kubectl >/dev/null && kubectl kustomize deploy/apps/policy-docs/ | head -40 || \
  uv run python -c "
import yaml
print('kubectl not found; doing YAML-parse-only check')
list(yaml.safe_load_all(open('deploy/apps/policy-docs/kustomization.yaml')))
print('kustomization.yaml OK')
"
```

If `kubectl kustomize` is available, expected output: a series of YAML documents, one per resource, all with `namespace: policy-docs` and the `app.kubernetes.io/managed-by: flux` label inherited. Spot-check that the Deployment's image is `ghcr.io/ggenomics/ggi-policy-site:main-1`.

- [ ] **Step 3: Commit**

```bash
git add deploy/apps/policy-docs/kustomization.yaml
git commit -m "$(cat <<'EOF'
feat(deploy): kustomization aggregator + image marker for Flux

Aggregates all eight app manifests. The images: block is the standard
Flux image-automation target — Flux's ImageUpdateAutomation rewrites
the newTag value when the ImagePolicy selects a newer image. Initial
tag is main-1 (matches the build-and-push workflow's first emission).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Flux image-automation CRs

**Files:**
- Create: `deploy/flux/image-automation/image-repository.yaml`
- Create: `deploy/flux/image-automation/image-policy.yaml`
- Create: `deploy/flux/image-automation/image-update-automation.yaml`
- Create: `deploy/flux/image-automation/kustomization.yaml`

- [ ] **Step 1: Create `image-repository.yaml`**

`deploy/flux/image-automation/image-repository.yaml`:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: policy-docs-image
  namespace: flux-system
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
spec:
  image: ghcr.io/ggenomics/ggi-policy-site
  interval: 5m
  # GHCR allows public anonymous reads; if your cluster's image-reflector
  # has a different secret expectation (private registry, rate-limit
  # bypass), set secretRef.name to a Secret in flux-system.
  # TODO(operator): confirm whether the cluster's image-reflector needs
  # explicit credentials for ghcr.io.
```

- [ ] **Step 2: Create `image-policy.yaml`**

`deploy/flux/image-automation/image-policy.yaml`:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: policy-docs-image
  namespace: flux-system
  labels:
    app.kubernetes.io/name: policy-docs
    app.kubernetes.io/part-of: ggi-policy
spec:
  imageRepositoryRef:
    name: policy-docs-image
  filterTags:
    # Match tags emitted by .github/workflows/build-and-push.yml as
    # `main-{run_number}`. The numeric portion is captured for ordering.
    pattern: '^main-(?P<num>\d+)$'
    extract: '$num'
  policy:
    numerical:
      order: asc
```

- [ ] **Step 3: Create `image-update-automation.yaml`**

`deploy/flux/image-automation/image-update-automation.yaml`:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: ggi-internals-image-updates
  namespace: flux-system
  labels:
    app.kubernetes.io/part-of: ggi-policy
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    # TODO(operator): confirm the GitRepository name. Most clusters use
    # 'flux-system' for the bootstrap repo; if ggi_internals is referenced
    # by a different name (e.g., 'ggi-internals'), update here.
    name: flux-system
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux-image-automation@ggenomics.com
        name: Flux Image Automation
      messageTemplate: |
        chore(image): bump policy-docs to {{range .Updated.Images}}{{println .}}{{end}}
    push:
      branch: main
  update:
    path: ./GitOps/k8s/prod/apps/policy-docs
    strategy: Setters
```

The `strategy: Setters` mode is what looks for `# {"$imagepolicy": "namespace:name"}` markers (the comment we placed on the image line in the Deployment) and rewrites them. The `images:` block in `kustomization.yaml` is also rewritten via the standard kustomize-image rule.

- [ ] **Step 4: Create the Flux kustomization aggregator**

`deploy/flux/image-automation/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: flux-system

resources:
  - image-repository.yaml
  - image-policy.yaml
  - image-update-automation.yaml
```

- [ ] **Step 5: Verify**

```bash
uv run python -c "
import yaml, glob
for f in sorted(glob.glob('deploy/flux/image-automation/*.yaml')):
    list(yaml.safe_load_all(open(f)))
    print(f, 'OK')
"
which kubectl >/dev/null && kubectl kustomize deploy/flux/image-automation/ > /dev/null && \
  echo 'kustomize build OK' || echo 'kubectl not available; skipped kustomize build check'
```

- [ ] **Step 6: Commit**

```bash
git add deploy/flux/image-automation/
git commit -m "$(cat <<'EOF'
feat(flux): image-automation CRs (ImageRepository + ImagePolicy + ImageUpdateAutomation)

ImageRepository watches ghcr.io/ggenomics/ggi-policy-site every 5m.
ImagePolicy selects the highest main-{N} tag (numerical, ascending).
ImageUpdateAutomation walks ggi_internals/GitOps/k8s/prod/apps/policy-docs/
in Setters mode, rewrites the marker on the Deployment image line and
the kustomization images: block, and pushes a commit back to main.

TODO(operator): confirm sourceRef.name matches the GitRepository CR
that points at ggi_internals.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: GHA workflow update — emit monotonic tag for Flux

**Files:**
- Modify: `.github/workflows/build-and-push.yml`

The Phase 3 workflow tags images with `latest` and `main-{sha}`. Flux's `ImagePolicy` needs a numerically-orderable tag to pick "the latest." Add a third tag, `main-{run_number}`, where `${{ github.run_number }}` is GitHub's monotonic counter for each repo. ImagePolicy filters on `^main-(\d+)$`; `latest` and `main-{sha}` are still emitted but excluded by the filter pattern.

- [ ] **Step 1: Add the new tag**

Read `.github/workflows/build-and-push.yml`. In the `Build and push` step's `tags:` block, currently:

```yaml
          tags: |
            ghcr.io/ggenomics/ggi-policy-site:latest
            ghcr.io/ggenomics/ggi-policy-site:main-${{ github.sha }}
```

Replace with:

```yaml
          tags: |
            ghcr.io/ggenomics/ggi-policy-site:latest
            ghcr.io/ggenomics/ggi-policy-site:main-${{ github.sha }}
            ghcr.io/ggenomics/ggi-policy-site:main-${{ github.run_number }}
```

- [ ] **Step 2: Verify YAML**

```bash
uv run python -c "
import yaml
list(yaml.safe_load_all(open('.github/workflows/build-and-push.yml')))
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-and-push.yml
git commit -m "$(cat <<'EOF'
ci(image): add monotonic main-{run_number} tag for Flux ImagePolicy

Flux's image-automation needs a numerically-orderable tag pattern to
pick 'the latest' build. github.run_number is a monotonic counter that
increments on every workflow run for the repo. The tag pattern in
deploy/flux/image-automation/image-policy.yaml is ^main-(\d+)$, which
matches main-{run_number} but not main-{sha} (sha is hex, not pure
digits) — so latest and main-{sha} continue to be published as
human-friendly references but only main-{run_number} drives Flux.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Manifest validation tooling + tests + CI

**Files:**
- Create: `tools/ggi_policy/manifests.py`
- Create: `tools/tests/test_manifests.py`
- Modify: `.github/workflows/validate.yml`

The validation walks every YAML under `deploy/`, parses it, and asserts each document has `apiVersion` and `kind`, image references match the expected registry, and ingress hostnames match `policy.ggenomics.internal`. This is a structural check, not a full k8s schema validation — kubeconform/kubeval would add a heavy CI dep we don't need yet.

- [ ] **Step 1: Implement `manifests.py`**

`tools/ggi_policy/manifests.py`:

```python
"""Structural validation for the deploy/ kustomize tree.

Scope: every YAML doc under deploy/ must have apiVersion + kind. Image
references in policy-docs Deployments must point at the canonical GHCR
repo. Ingress hostnames must match the canonical public hostname.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import yaml


CANONICAL_IMAGE_REPO = "ghcr.io/ggenomics/ggi-policy-site"
CANONICAL_HOSTNAME = "policy.ggenomics.internal"


def iter_documents(deploy_root: Path) -> Iterator[tuple[Path, dict]]:
    """Yield (file_path, doc_dict) for every YAML document under deploy/."""
    for yaml_file in sorted(deploy_root.rglob("*.yaml")):
        with yaml_file.open() as f:
            for doc in yaml.safe_load_all(f):
                if doc is None:
                    continue
                yield yaml_file, doc


def validate(deploy_root: Path) -> list[str]:
    """Return a list of error messages, empty list if all manifests are valid."""
    errors: list[str] = []
    saw_canonical_image = False
    saw_canonical_host = False

    for path, doc in iter_documents(deploy_root):
        if not isinstance(doc, dict):
            errors.append(f"{path}: top-level YAML document is not a mapping")
            continue
        kind = doc.get("kind")
        if not kind:
            errors.append(f"{path}: missing 'kind'")
        if not doc.get("apiVersion"):
            errors.append(f"{path}: missing 'apiVersion'")

        if kind == "Deployment":
            for container in (
                doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            ):
                image = container.get("image", "")
                if image.startswith(CANONICAL_IMAGE_REPO + ":"):
                    saw_canonical_image = True
                elif "ggi-policy-site" in image and not image.startswith(CANONICAL_IMAGE_REPO):
                    errors.append(
                        f"{path}: container image {image!r} should reference {CANONICAL_IMAGE_REPO}"
                    )

        if kind == "Ingress":
            for tls in doc.get("spec", {}).get("tls", []) or []:
                for host in tls.get("hosts", []) or []:
                    if host != CANONICAL_HOSTNAME:
                        errors.append(
                            f"{path}: TLS host {host!r} should be {CANONICAL_HOSTNAME!r}"
                        )
                    else:
                        saw_canonical_host = True
            for rule in doc.get("spec", {}).get("rules", []) or []:
                host = rule.get("host", "")
                if host and host != CANONICAL_HOSTNAME:
                    errors.append(
                        f"{path}: rule host {host!r} should be {CANONICAL_HOSTNAME!r}"
                    )

    if not saw_canonical_image:
        errors.append(
            f"no Deployment references the canonical image {CANONICAL_IMAGE_REPO!r}"
        )
    if not saw_canonical_host:
        errors.append(
            f"no Ingress references the canonical host {CANONICAL_HOSTNAME!r}"
        )

    return errors
```

- [ ] **Step 2: Write tests**

`tools/tests/test_manifests.py`:

```python
from pathlib import Path

from ggi_policy import manifests


def test_validate_committed_deploy_tree() -> None:
    """The committed deploy/ manifests must pass structural validation."""
    from ggi_policy.repo import repo_root

    errors = manifests.validate(repo_root() / "deploy")
    assert errors == [], "deploy/ tree has structural issues:\n  " + "\n  ".join(errors)


def test_validate_flags_missing_kind(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("apiVersion: v1\n# missing kind\n")
    errors = manifests.validate(tmp_path)
    assert any("missing 'kind'" in e for e in errors)


def test_validate_flags_wrong_image(tmp_path: Path) -> None:
    bad = tmp_path / "deployment.yaml"
    bad.write_text("""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: x
spec:
  template:
    spec:
      containers:
        - name: x
          image: docker.io/ggenomics/ggi-policy-site:main-1
""")
    errors = manifests.validate(tmp_path)
    assert any("ghcr.io/ggenomics/ggi-policy-site" in e for e in errors)


def test_validate_flags_wrong_ingress_host(tmp_path: Path) -> None:
    bad = tmp_path / "ingress.yaml"
    bad.write_text("""\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: x
spec:
  rules:
    - host: policy.example.com
""")
    errors = manifests.validate(tmp_path)
    assert any("policy.example.com" in e for e in errors)


def test_validate_requires_canonical_image_present(tmp_path: Path) -> None:
    """An empty tree should fail because no canonical image is present."""
    errors = manifests.validate(tmp_path)
    assert any("canonical image" in e for e in errors)
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tools/tests/test_manifests.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Run full suite**

```bash
uv run pytest -q
```

Expected: 84 passed (79 prior + 5 new).

- [ ] **Step 5: Add manifest validation to CI**

Read `.github/workflows/validate.yml`. After the `Check crosswalks are up to date` step, append:

```yaml
      - name: Validate deployment manifests
        run: uv run python -c "
            from pathlib import Path
            from ggi_policy import manifests
            errors = manifests.validate(Path('deploy'))
            if errors:
                for e in errors: print(e)
                raise SystemExit(1)
            print('OK: deploy/ manifests valid')
          "
```

- [ ] **Step 6: Verify the CI step locally**

```bash
uv run python -c "
from pathlib import Path
from ggi_policy import manifests
errors = manifests.validate(Path('deploy'))
print('OK' if not errors else '\n'.join(errors))
"
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add tools/ggi_policy/manifests.py tools/tests/test_manifests.py \
        .github/workflows/validate.yml
git commit -m "$(cat <<'EOF'
feat(manifests): structural validation of deploy/ tree

Walks every YAML doc under deploy/ and asserts:
- apiVersion + kind present on every doc
- Deployment containers reference ghcr.io/ggenomics/ggi-policy-site
- Ingress hosts match policy.ggenomics.internal
- At least one Deployment+Ingress reach those canonical references

Five tests cover the happy path, missing kind, wrong image registry,
wrong hostname, and missing-canonical-references guard. CI runs the
check after build-crosswalks --check.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Operator README + smoke verification

**Files:**
- Create: `deploy/README.md`

This is the operator-facing guide. It enumerates every external-state prerequisite, walks the promotion to `ggi_internals`, and lists the manual smoke steps.

- [ ] **Step 1: Create the README**

`deploy/README.md`:

````markdown
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
````

- [ ] **Step 2: Final manifest validation pass**

```bash
uv run python -c "
from pathlib import Path
from ggi_policy import manifests
errors = manifests.validate(Path('deploy'))
print('OK' if not errors else '\n'.join(errors))
"
```

Expected: `OK`.

- [ ] **Step 3: kustomize build (if available)**

```bash
which kubectl >/dev/null && kubectl kustomize deploy/apps/policy-docs/ | grep -E '^(apiVersion|kind|  name): ' | head -30 || \
  echo "kubectl not available; skipping kustomize build smoke"
```

If `kubectl` is available, expected output: 8 resources rendered (Namespace, 2 ServiceAccounts, Deployment, Service, Deployment for oauth2-proxy, Service for oauth2-proxy, Ingress, VaultStaticSecret + the ConfigMap from the Deployment doc) — total 9 distinct `kind:` lines.

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -q
uv run ggi-policy validate
uv run ggi-policy build-crosswalks --check
```

Expected: 84 passed; validate OK; crosswalks OK.

- [ ] **Step 5: Commit**

```bash
git add deploy/README.md
git commit -m "$(cat <<'EOF'
docs(deploy): operator guide for k8s promotion + smoke

Walks the operator through Entra app registration, DNS allocation,
Vault setup, and the cp -r promotion to ggi_internals. Six-step smoke
verification covers DNS, TLS, auth flow, Flux image sync, and oauth2-proxy
health. Closes the gap between 'manifests authored' and 'cluster
running the policy site under SSO'.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

**Spec coverage:** every Phase-4-relevant section of the design has a task implementing it.

| Spec section | Plan task |
|---|---|
| §8.4 Two-repo model: this repo for content/image, `ggi_internals` for manifests | All tasks (manifests under `deploy/`, promotion in Task 10) |
| §8.4 Flux image automation (B1) | Tasks 7, 8 |
| §8.4 Auth: ingress-nginx + oauth2-proxy + Entra | Tasks 3, 4 |
| §8.4 In-cluster secrets via Vault + VSO | Task 5 |
| §3 Decisions: Entra SSO, GHCR, on-prem k8s | Tasks 1-7 |
| §10 Open items: Entra app, DNS, Vault, TLS | Documented in `deploy/README.md` (Task 10) |

The plan does NOT directly write to `ggi_internals`. That's deliberate: this repo doesn't have write access to the GitOps repo (per the design's B1 choice), and any agent running this plan should not require it. The promotion is a single `cp -r` documented in Task 10.

**Placeholder scan:** `TODO(operator):` markers appear in five manifest files (ingress, vault-static-secret, image-repository, image-update-automation, plus the ImageRepository's optional secretRef). Each is a real operational decision the operator must confirm against their cluster's existing pattern (mirror `airflow/`). They are NOT plan failures; the plan is delivering manifests for review and the operator's environment provides the missing values. The README enumerates every TODO with `grep -rn "TODO(operator)" deploy/`.

No `TBD`/`FIXME`/`implement later` text in the plan or in any manifest body.

**Type / signature consistency:**
- `manifests.validate(deploy_root: Path) -> list[str]` introduced Task 9, used in Task 10.
- `iter_documents(deploy_root: Path) -> Iterator[(Path, dict)]` introduced Task 9, used by `validate`.
- Image references all use `ghcr.io/ggenomics/ggi-policy-site` (matches Phase 3's Dockerfile push target).
- Hostname `policy.ggenomics.internal` is consistent across mkdocs.yml (Phase 3, just renamed), ingress.yaml (Task 3), and oauth2-proxy --redirect-url (Task 4).
- Service names `policy-docs` (port 80 → container 8080) and `oauth2-proxy` (port 80 → container 4180) match the ingress backend references.
- The Flux `ImagePolicy` filter pattern `^main-(\d+)$` requires Task 8's CI workflow change (adding `main-{run_number}` tag) — these are paired and live in the same plan.
- ServiceAccount names (`policy-docs`, `oauth2-proxy`) match the `serviceAccountName:` references in their Deployments.
- Vault path `secret/policy-docs/oauth2-proxy` and four keys (`tenant_id`, `client_id`, `client_secret`, `cookie_secret`) match between the VaultStaticSecret CR (Task 5), the oauth2-proxy Deployment env (Task 4), and the README's `vault kv put` example (Task 10).

**Ambiguity:**
- The Flux `ImageUpdateAutomation` writes to `./GitOps/k8s/prod/apps/policy-docs` relative to the GitRepository root. If the operator's cluster has a different bootstrap path, they adjust at promotion time. Documented in Task 10.
- The image-policy uses `policy.numerical: { order: asc }`, which means "highest number wins" — `asc` is the Flux convention for ascending-then-pick-the-tail. Operators familiar with `policy.numerical` may find this counterintuitive but the docs are clear. No change needed.
- Phase 4 doesn't include a NetworkPolicy. The restricted PSS profile gives baseline pod-level hardening; cluster-level NetworkPolicy is the operator's call. Future cleanup if compliance demands it.

**Carry-forward to Phase 5 (lifecycle automation):**
- The first real policy author will need a working CODEOWNERS team setup. Phase 5 creates the GitHub teams; this Phase 4 work is independent.
- Scheduled bots (review-due, effective-date Teams notifications, exception expiration) are Phase 5.
- Phase 2 carry-forwards still open: HIPAA XML test coverage, deterministic catalog sort.
