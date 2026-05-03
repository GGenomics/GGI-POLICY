"""Canonical domain prefix → folder mapping.

The single source of truth for the 12 GGI policy domains. Imported by the
runner (which uses it to validate ID/folder consistency) and by tests that
need to drive the consistency validator with the production mapping.
"""

DOMAIN_TO_FOLDER: dict[str, str] = {
    "IAM":  "identity-and-access",
    "DAT":  "data",
    "PRV":  "privacy",
    "APP":  "applications",
    "END":  "endpoints",
    "NET":  "network",
    "IR":   "incident-response",
    "VND":  "vendor-and-third-party",
    "SEC":  "security-operations",
    "BCP":  "business-continuity",
    "HR":   "human-resources",
    "META": "meta",
}
