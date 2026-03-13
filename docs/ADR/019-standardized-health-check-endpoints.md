# ADR 019: Standardized Health Check Endpoints

## Status

Accepted

## Context

Aragora's deploy and operations documentation currently points different environments at different health endpoints. `docs/governance/deploy-truth-table.md` records this as **DRIFT-003: Health check endpoint inconsistency** and identifies four incompatible probe patterns in active docs:

1. `/healthz`
2. `/api/v1/health`
3. `/health/live` and `/health/ready`
4. `/api/health`

That drift creates three operational problems:

1. Monitoring and load balancer checks are not portable across deployment surfaces.
2. Documentation reviewers cannot tell which endpoint is the actual contract versus a leftover alias.
3. Future cleanup becomes risky because removing any one endpoint can silently break a deployment path that was documented against a different surface.

The repository already documents versioned health routes under `/api/v1/health*`, while some older runbooks and deployment guides still rely on unversioned or probe-specific aliases. Aragora needs one deploy-facing contract for liveness and readiness so environment-specific packaging details do not redefine the health API.

## Decision

Aragora standardizes health checks for deploy surfaces as follows:

1. **Canonical liveness endpoint**
   The canonical liveness endpoint is `/api/v1/health`.
2. **Canonical readiness endpoint**
   The canonical readiness endpoint is `/api/v1/health/ready`.
3. **Versioned health namespace**
   Deploy, infrastructure, and operator documentation should treat `/api/v1/health*` as the canonical health namespace. Component-specific health checks should remain underneath that namespace.
4. **Legacy endpoint classification**
   Existing endpoints such as `/healthz`, `/health/live`, `/health/ready`, and `/api/health` are compatibility paths only. They must not be introduced in new deployment guidance as the primary probe contract.
5. **Documentation and automation rule**
   When a document, Helm chart, compose file, reverse proxy, uptime monitor, or validation script needs one health URL, it should use `/api/v1/health` for liveness and `/api/v1/health/ready` for readiness unless a later ADR explicitly supersedes this rule.
6. **Migration expectation**
   If an existing environment still depends on a legacy probe path, that dependency should be treated as migration drift relative to this ADR and to `DRIFT-003`, not as an alternate standard.

## Consequences

### Positive

- Deployment surfaces now have one explicit liveness contract and one explicit readiness contract.
- Documentation cleanup can converge on a single rule instead of preserving multiple endpoint families indefinitely.
- Reviewers have a clear standard for identifying drift in runbooks, Helm values, reverse proxies, and smoke tests.

### Negative

- Existing docs and deploy artifacts that still reference `/healthz`, `/health/live`, `/health/ready`, or `/api/health` will require follow-up migration work.
- If some runtime surfaces do not yet expose `/api/v1/health/ready`, implementation work will be needed to align runtime behavior with the canonical contract defined here.

### Neutral

- This ADR defines the contract for health endpoint usage; it does not itself modify runtime code or remove legacy aliases.
- Component-specific health endpoints may continue to exist, but they should be documented as subordinate checks under the `/api/v1/health*` namespace rather than as deployment-wide defaults.

## Related

- `docs/governance/deploy-truth-table.md` (`DRIFT-003`)
- `docs/ADR/006-api-versioning-strategy.md`
- `docs/ADR/018-self-hosted-worker-canonicalization.md`
