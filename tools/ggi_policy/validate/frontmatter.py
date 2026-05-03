import json
from functools import cache

from jsonschema import Draft202012Validator, FormatChecker

from ggi_policy.io import LoadedPolicy
from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "policy-frontmatter.schema.json"
    schema = json.loads(schema_path.read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


def check(policy: LoadedPolicy, report: ValidationReport) -> None:
    for err in _validator().iter_errors(policy.metadata):
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="FRONTMATTER_INVALID",
            path=policy.path,
            message=f"{path}: {err.message}",
            locator=path,
        ))
