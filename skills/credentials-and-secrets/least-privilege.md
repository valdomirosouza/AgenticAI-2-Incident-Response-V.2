# Least Privilege — Policies by Layer

## Cloud IAM

```yaml
forbidden:
  - roles/owner or AdministratorAccess on application workloads
  - Long-lived credentials (static access key) for services
  - Shared roles between distinct services
  - Cross-account access without explicit audited STS AssumeRole

required:
  - IAM Roles with minimum scope per service (IRSA on EKS, Workload Identity on GKE)
  - Temporary credentials via STS (max duration: 1h in production)
  - Resource-based policies with explicit conditions
  - SCPs (Service Control Policies) at OU/org level blocking unused services

review:
  frequency: quarterly
  tool: AWS IAM Access Analyzer / GCP IAM Recommender
  action: Revoke permissions unused for > 90 days
```

## Kubernetes RBAC

```yaml
# Required rules
namespaces:
  - Each service in its own namespace
  - No application workloads in default or kube-system

service_accounts:
  - automountServiceAccountToken: false   # Disabled by default
  - Explicit SA per deployment (never default SA)
  - Projected token with short duration (1h)

roles:
  - No ClusterRole admin for application workloads
  - ClusterRoles only for platform operators and controllers
  - Namespaced roles with minimum verbs

# Correct example
correct_role:
  apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]                  # Not "watch", "patch", "delete"
  resourceNames: ["payment-service-config"] # Specific resource, not wildcard

# Audit tools
audit_tools:
  - rbac-tool (visualize effective permissions)
  - kubectl-who-can (reverse validation)
  - Polaris / OPA Gatekeeper (enforcement via admission controller)
```

## Database

```sql
-- Each service has its own DB user with minimum permissions
-- ❌ FORBIDDEN: full access user
GRANT ALL PRIVILEGES ON DATABASE production TO payment_service;

-- ✅ CORRECT: exact permissions by operation
CREATE USER payment_service_rw WITH PASSWORD '[managed by vault]';
GRANT CONNECT ON DATABASE production TO payment_service_rw;
GRANT USAGE ON SCHEMA payments TO payment_service_rw;
GRANT SELECT, INSERT, UPDATE ON TABLE payments.transactions TO payment_service_rw;
-- No DELETE, DROP, CREATE, TRUNCATE

-- Read-only user for analytics/BI
CREATE USER payment_service_ro WITH PASSWORD '[managed by vault]';
GRANT SELECT ON ALL TABLES IN SCHEMA payments TO payment_service_ro;

-- Password rotation via vault (automatic, every 24h)
```

## CI/CD Pipeline

```yaml
ci_permissions:
  authentication:
    method: OIDC federation (no static access keys in CI)
    github_actions_example:
      permissions:
        id-token: write  # For OIDC
        contents: read   # For checkout
        # Nothing else

  roles_per_stage:
    validate_test:
      can: [read repository, publish test results]
      cannot: [deploy, production access, read prod secrets]
    build_push:
      can: [push to staging registry]
      cannot: [push to production registry, DB access]
    deploy_staging:
      can: [deploy to staging namespace, read staging secrets]
      cannot: [production namespace access]
    deploy_production:
      requires: [explicit human approval]
      can: [deploy to production namespace, read production secrets]
      credential_duration: 15min (Just-in-Time)
      audit: "Full action log with approver identity"
```

## Human Access — Just-in-Time

```yaml
production_access:
  principle: "No permanent production access. JIT only."
  tools: [HashiCorp Boundary, AWS IAM Identity Center, Teleport]

  jit_flow:
    1: "Engineer requests access with justification and linked ticket"
    2: "Manager or peer approval (self-approval forbidden)"
    3: "Access granted for limited time (max 4h)"
    4: "Session recorded and audited"
    5: "Access automatically revoked on expiry"

  forbidden:
    - Direct SSH with permanent static key
    - Production DB credentials on developer local machine
    - Permanent root/admin access for anyone

  audit_schedule:
    continuous: "Alert on permissions never used"
    weekly: "Review JIT access granted but unused"
    quarterly: "Formal access review — revoke stale permissions"
    on_offboarding: "Revoke 100% of access within 1h of departure"
```

## Least Privilege Checklist per Service

```markdown
### Cloud IAM
- [ ] Exclusive Service Account created for this service
- [ ] Role with minimum permissions reviewed by SecOps
- [ ] No admin/owner role attached
- [ ] Temporary credentials (IRSA / Workload Identity), no static access key

### Kubernetes
- [ ] Dedicated namespace created
- [ ] Own ServiceAccount with automount disabled
- [ ] Namespaced Role with minimum verbs and resources
- [ ] NetworkPolicy defined (ingress and egress restricted)

### Database
- [ ] Exclusive user created (not shared)
- [ ] Permissions only on necessary tables/schemas
- [ ] No DDL permissions (CREATE, DROP, ALTER) in production
- [ ] Password managed by vault with automatic rotation

### CI/CD
- [ ] Pipeline uses OIDC (no static credentials)
- [ ] Per-stage permissions (not global to the job)
- [ ] Production access requires explicit human approval

### Human Access
- [ ] Zero permanent production access
- [ ] JIT configured with max 4h limit
- [ ] Session recording enabled
- [ ] MFA required for any privileged access
```
