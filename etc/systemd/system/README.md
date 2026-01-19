# /etc/systemd/system

## Service supervision

systemd is the host-level supervisor for both native services and Compose
stacks. It defines what starts on boot and how services are restarted.

## Purpose

Clarify what systemd manages and why.

## Service categories

- **Host-native services**: NGINX, certbot renewals.
- **Application platform**: `platform.service` for the shared Flask API.
- **Compose orchestration**: `compose-platform.service` for the Auth/BFF stack.

## Lifecycle expectations

- `enable` controls boot-time activation; it does not start a service
  immediately.
- `start` and `stop` are manual operations and part of change control.
- One-shot units may be used for periodic jobs (e.g., Certbot renewal).

## Design rule

systemd supervises process lifecycles and orchestration boundaries, not
application internals or business logic.
