# aws-box

This repository is the **infrastructure sandbox** for the EC2 instance that
hosts the shared Flask platform and multiple client frontends. It mirrors key
parts of `/etc/` and `/srv/webapps/` and provides scripts for auditing and
deploying changes safely.

---

## Overview

The EC2 instance serves two kinds of content:

1. **Static frontends** for each client domain – delivered directly by Nginx
   from `/srv/webapps/clients/<domain>/frontend`. These sites can function
   entirely on their own.
2. **Optional JSON APIs** provided by a shared Flask application. This app runs
   under Gunicorn and only becomes part of a site when `/api` proxying is
   enabled in the Nginx configuration.

Keeping these concerns separated means you can host simple brochure sites
without running any Python code, while still having the option to expose
structured data via the API when needed.

---

## Environment overview

This infrastructure runs on a freshly rebuilt Debian-based EC2 instance.

Key components:

- **Nginx**: virtual hosting, static file serving, and reverse-proxy for backend APIs
- **Gunicorn**: application server for the Flask platform
- **Flask**: shared backend platform serving multiple client sites
- **Certbot / Let’s Encrypt**: automatic TLS certificate provisioning and renewal

This instance replaces an older degraded EC2 instance and incorporates
additional recovery and access mechanisms not previously present.

---

## Directory structure & ownership

Primary sources of truth and where this repo exists are on the server as:

```text
home/admin/srv/webapps/
├── platform/
│   ├── app.py
│   ├── multi-tennant-data-access.py
│   ├── client-data-acess.py
│   ├── requirements.txt
│   ├── venv/                  # Python virtual environment (NOT in git)
│   └── platform.service       # systemd service (installed under /etc/systemd)
├── clients/
│   ├── fruitfulnetworkdevelopment.com/
│   │   ├── frontend/
│   │   └── data/
│   └── cuyahogaterravita.com/
│       ├── frontend/
│       └── data/

home/admin/etc/
├── nginx/
│   ├── nginx.conf
│   ├── mime.types
│   ├── sites-available/
│   │   ├── fruitfulnetworkdevelopment.com.conf
│   │   └── cuyahogaterravita.com.conf
│   └── sites-enabled/
│       └── (symlinks only — default site removed)
└── systemd/system/
    └── platform.service
```

Key points:

- Each client gets its own directory under `/srv/webapps/clients/` and is
  identified by its domain name. All static files live in that directory.
- Manifests live at the root of each client directory (e.g. `msn_admin.json`),
  not under `frontend/`. They define the client title, logo, and the
  `backend_data` array listing which files in `data/` may be served by the API.
- The `platform/venv/` directory is not stored in git and must be created on the
  server. Use `python3 -m venv venv` to set it up.

This repo is then mirrored by the live directories under:

```text
/etc/
/srv/webapps/
```

---

## Python virtual environments (venv)

All Python services are run inside explicit virtual environments.

Create the venv and install requirements:
```bash
cd /srv/webapps/platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
, then make sure Gunicorn exists:
```bash
which gunicorn
```
- We expect to see `/srv/webapps/platform/venv/bin/gunicorn`

If sucessful, we can exit:
```bash
deactivate
```
, and then restart:
```bash
sudo systemctl restart platform.service
sudo systemctl status platform.service --no-pager
```

---

## Access methods

### SSH (primary)

- Access is performed using a PEM key:

  ```bash
  ssh -i ~/.ssh/aws-main-key.pem admin@<Elastic-IP>
  ```

- The `admin` user’s `~/.ssh/authorized_keys` contains the public key material.

---

## System services

### Gunicorn (Flask platform)

- Managed by systemd via `platform.service`.
- Restart via:

  ```bash
  sudo systemctl restart platform.service
  ```

### Nginx

- Managed by systemd.
- Validate config with:

  ```bash
  sudo nginx -t
  ```

- Reload after config changes:

  ```bash
  sudo systemctl reload nginx
  ```

### Logging & disk safety

- `journald` limits enforced:

  ```text
  SystemMaxUse=200M
  RuntimeMaxUse=200M
  ```

- Prevents disk exhaustion from runaway logs.

---

## SSL & DNS

- DNS `A` records for all domains point to the Elastic IP of this instance.
- Certificates are managed by Certbot using the nginx authenticator.
- Renewal can be tested via:

  ```bash
  sudo certbot renew --dry-run
  ```

- Port 80 must remain open for HTTP-01 challenges.

---

## Troubleshooting & differences from old instance

- The original instance suffered SSH banner hangs due to system-level corruption.
- Recovery was not possible without rebuilding.
- This instance was rebuilt cleanly with:
  - explicit systemd services
  - enforced logging limits
  - SSM access for recovery
  - cleaner separation of platform vs client assets

---

## Multi-tenant platform & manifests (MSN)

At a high level, the platform follows a **manifest-first** design:

- One manifest per client: `msn_<userId>.json` contains site configuration and
  `backend_data` whitelists.
- Nginx serves static frontends from `/srv/webapps/clients/<domain>/frontend`.
- The shared Flask backend in `/srv/webapps/platform` discovers these manifests
  and serves APIs and data according to each manifest.

### Platform data access files

The platform’s data-access logic is consolidated into two files:

- `multi-tennant-data-access.py` handles host-based client detection, filesystem
  path resolution, and manifest parsing.
- `client-data-acess.py` handles dataset discovery, dataset resolution, and
  backend data filename validation.

The filenames contain hyphens, so the Flask app loads them using `importlib`
when it starts.

### Client-specific data access

Each client directory contains a `data/` directory alongside `frontend/`. The
`data/` directory holds client-specific JSON that the frontend can read through
API routes. Files must be whitelisted in the manifest before Flask will read
or write them.

Flask behaves like a dataset registry rather than a generic file server:

- It exposes a list of dataset IDs found in the allowed directory.
- It provides a single dataset load endpoint by dataset ID.

This prevents path traversal issues, accidental leakage of arbitrary server
files, and tight coupling between frontend code and filesystem structure.

---
