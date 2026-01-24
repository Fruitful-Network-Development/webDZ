# /etc

## Host OS configuration

This directory documents the **host-level responsibilities** that must remain
on the OS instead of inside containers.

## Purpose

Define the host boundary and what is managed directly on the EC2 instance.

## Responsibilities

- **Ingress & TLS**: NGINX configuration and TLS termination (Certbot).
- **Service supervision**: systemd unit files for host-native services and
  Compose stacks.
- **Host safety controls**: log rotation, journald limits, and other OS-level
  guardrails.

## Non-responsibilities

- Application business logic (lives under `/srv`).
- Identity logic (managed by the Auth stack under `/srv/compose`).
- Stateful application data (lives in runtime directories or volumes).

## Change policy

- Changes are inert until services are explicitly reloaded or restarted.
- New vhosts are inactive until symlinked into `sites-enabled`.
- New systemd units are inactive until explicitly enabled and started.

## Current initiatives

- Introduce `certbot-renew.service` and `certbot-renew.timer` for scheduled
  certificate management.
- Add `compose-platform.service` to supervise the Auth/BFF Compose stack.

---

## /etc/systemd/system

### Service supervision

systemd is the host-level supervisor for both native services and Compose
stacks. It defines what starts on boot and how services are restarted.

### Purpose

Clarify what systemd manages and why.

### Service categories

- **Host-native services**: NGINX, certbot renewals.
- **Application platform**: `platform.service` for the shared Flask API.
- **Compose orchestration**: `compose-platform.service` for the Auth/BFF stack.

### Lifecycle expectations

- `enable` controls boot-time activation; it does not start a service
  immediately.
- `start` and `stop` are manual operations and part of change control.
- One-shot units may be used for periodic jobs (e.g., Certbot renewal).

### Design rule

systemd supervises process lifecycles and orchestration boundaries, not
application internals or business logic.

