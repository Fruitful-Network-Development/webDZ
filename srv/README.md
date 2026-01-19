# /srv

## Runtime domain

`/srv` is the runtime and deployment surface. It is where live web assets,
platform code, and Compose stacks reside.

## Purpose

Define what belongs on the runtime surface and how it should be managed.

## What lives here

- Client static sites under `/srv/webapps/clients/`.
- Shared platform code under `/srv/webapps/platform/`.
- Container stacks under `/srv/compose/`.

## What does not

- Host configuration (belongs under `/etc`).
- Secrets (only templates or examples may live in the repo).
- One-off ad hoc data that should be stored elsewhere.

## Backup expectations

- **Must back up**: client frontends, manifest files, client data files, and
  environment templates that document required variables.
- **Can be rebuilt**: platform virtual environments and container images.
- **External volumes**: container volumes are stored under `/var/lib/docker`
  and should be backed up separately if persistence is required.
