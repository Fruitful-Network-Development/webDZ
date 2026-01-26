
# BFF
## CORE CONSOLE DESIGN
> Core is what must remain stable for every tenant and every module. It is your operating system. Core contract: modules plug into the shell; the shell does not embed business logic.

### IDENTITY + TENANCY
* Tenant selection and routing (tenant_registry, allowed_return_to, /t/<tenant>/…)
* Session/auth integration (Keycloak/OIDC)
* Authorization primitives (root-admin vs tenant-admin vs tenant-user)
* Provisioning gate (“not provisioned” via MSS profile)
> **Core contract**: every request has a resolved tenant context + user context or a deterministic error/redirect.

### DATA CONTORL PLANE (MSS)
> Omits serving static client frontends or controlling infrastructure services `github.com`. It is a *control plane* for identity and data access; external business logic must call through the BFF to reach the data.

### RUN TIME DATA PLANE 

#### PLATFORM DATA
  *shaping the space, not filling it.*
Tables:
  - Registry-backed
  - Archetype-validated
  - Not tenant-scoped unless explicitly bound
Lists:
  - Ordered references (not categories)
  - Used to resolve ordinals and structural linkage

#### GENERIC CRUD

### UI SHELL

## MODUELS
### PLATFORM MODUELS
> A platform module is a reusable capability that many tenants might use, but that is not required for the platform to function.
> Platform module contract: it uses core identity + data contracts; it does not redefine them.
### TENANT MODUELS
> Tenant modules are the use cases for a specific type of tenant. They’re often thin UI + workflows on top of core + platform modules.
> Tenant modules differ from platform modules because they are not universally reusable. They can still be built using the same core + platform components.

---

