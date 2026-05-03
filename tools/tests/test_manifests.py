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
