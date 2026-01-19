# /srv/compose

## Containerization rationale

Compose stacks live here when a service benefits from isolation, portability,
or when upstream tooling expects container boundaries.

## Purpose

Explain why Docker exists here and what responsibilities it owns.

## Why these services are containerized

- Isolation of third-party services (e.g., Keycloak).
- Safer upgrades and rollbacks via image pinning.
- Clear separation between host-native services (NGINX) and app services.

## Why others are not

- NGINX remains on the host for direct TLS termination and lowest-latency
  ingress control.
- Static files remain on the host for simple, direct serving.

## Operational model

- One Compose stack per responsibility group.
- Stacks are supervised by systemd units (e.g., `compose-platform.service`).
- Environment files live alongside stack definitions; templates are committed
  while secrets are not.
