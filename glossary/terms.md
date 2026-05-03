# Glossary

Controlled vocabulary used in GGI policies. Terms are added when first
referenced in a policy and stay here as a reference for both employees
and AI agents.

## Identity and Access (IAM)

- **M365 Group** (also: Microsoft 365 Group, Office 365 Group) — A group
  type in Microsoft Entra ID that bundles a shared mailbox, SharePoint
  document library, OneNote notebook, Planner plan, and (optionally) a
  Teams channel under one identity. Members get all the resources at
  once. Used for collaboration scenarios that span email + files + chat.
  Reference: https://learn.microsoft.com/microsoft-365/admin/create-groups/compare-groups

- **Distribution Group** (also: Distribution List) — An Exchange-managed
  group used solely to distribute email to multiple recipients. Cannot
  be used to grant permissions and has no SharePoint, Teams, or files
  surface. Synced from on-prem AD or created cloud-only. Reference:
  https://learn.microsoft.com/exchange/recipients-in-exchange-online/manage-distribution-groups

- **Mail-enabled Security Group** — An Exchange-extended security group:
  it can both grant permissions to resources (like a security group) and
  receive email (like a distribution group). Useful when a permission
  set and a distribution list have identical membership. Reference:
  https://learn.microsoft.com/microsoft-365/admin/email/create-edit-or-delete-a-security-group

- **Security Group** — An Entra ID (or on-prem AD synced) group used to
  grant access to resources — file shares, SharePoint sites, applications,
  Azure RBAC role assignments. Has no email surface and no associated
  collaboration resources. The most common group type for technical
  permission grants. Reference:
  https://learn.microsoft.com/entra/fundamentals/concept-learn-about-groups

- **Shared Mailbox** — A mailbox in Exchange Online that multiple users
  can access via delegation; not associated with a single user account
  and does not consume a per-user license. Used for role-based addresses
  like `support@`, `info@`. Reference:
  https://learn.microsoft.com/exchange/collaboration-exo/shared-mailboxes

- **Conditional Access** — Entra ID's policy engine that evaluates each
  sign-in attempt against a set of conditions (user, device, location,
  application, risk level) and applies controls (require MFA, require
  compliant device, block, require password change). The primary
  mechanism by which GGenomics enforces zero-trust access at the identity
  layer. Reference:
  https://learn.microsoft.com/entra/identity/conditional-access/overview

- **PIM (Privileged Identity Management)** — An Entra ID Premium feature
  that converts standing privileged role assignments (Global Administrator,
  Privileged Role Administrator, etc.) into time-bound, just-in-time
  activations. Users request the role for a specific window with optional
  approval; the role auto-deactivates when the window expires. Used for
  any high-privilege Entra or Azure RBAC role. Reference:
  https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure

## Data (DAT)

*(populated as data policies are added)*

## Privacy (PRV)

*(populated as privacy policies are added)*

## Applications (APP), Endpoints (END), Network (NET), Incident Response (IR), Vendor & Third-Party (VND), Security Operations (SEC), Business Continuity (BCP), Human Resources (HR), Meta (META)

*(populated as those domains' policies are added)*
