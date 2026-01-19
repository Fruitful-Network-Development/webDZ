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
