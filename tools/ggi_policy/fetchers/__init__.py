"""Pluggable framework-control fetchers.

Each fetcher module exposes a ``fetch(*, fetched_at: date | None = None)``
function returning a FrameworkData. The REGISTRY below maps the framework
key (which appears in policy frontmatter under `frameworks:` and in the
framework-controls.json file) to its fetcher module.
"""

from ggi_policy.fetchers import (
    cis as _cis,
    hipaa as _hipaa,
    nist_800_53 as _nist_800_53,
    nist_800_171 as _nist_800_171,
    nist_csf as _nist_csf,
    soc2 as _soc2,
)


REGISTRY = {
    "nist_csf":     _nist_csf,
    "cis":          _cis,
    "soc2":         _soc2,
    "hipaa":        _hipaa,
    "nist_800_53":  _nist_800_53,
    "nist_800_171": _nist_800_171,
}
