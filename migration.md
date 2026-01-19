# Migration Plan

GitHub repo (the “mirror repo”) showing what you would add so it is ready to deploy, but not yet active. Server filesystem showing what it looks like after you sync the repo to the box, but before you actually start the Compose stack or enable the systemd unit.

## GitHub repo hierarchy (ready-to-deploy, not yet enabled)
```bash
aws-ec2-mini-linux-box/
├── README.md
├── deploy/
│   ├── rsync_to_server.sh
│   └── notes.md
│
├── etc/
│   ├── nginx/
│   │   ├── sites-available/
│   │   │   ├── fruitfulnetworkdevelopment.com.conf
│   │   │   ├── greenfieldberryfarm.com.conf
│   │   │   ├── api.fruitfulnetworkdevelopment.com.conf               # NEW
│   │   │   └── auth.fruitfulnetworkdevelopment.com.conf              # NEW
│   │   └── snippets/
│   │       ├── ssl_params.conf                                       # NEW
│   │       └── proxy_common.conf                                     # NEW (optional but recommended)
│   │
│   ├── systemd/
│   │   └── system/
│   │       ├── platform.service
│   │       ├── certbot-renew.service                                 # NEW
│   │       ├── certbot-renew.timer                                   # NEW
│   │       └── compose-platform.service                              # NEW
│   │
│   └── logrotate.d/                                                  # NEW
│       └── nginx
│
├── srv/
│   ├── webapps/
│   │   ├── clients/
│   │   │   ├── fruitfulnetworkdevelopment.com/
│   │   │   │   └── frontend/
│   │   │   │       ├── index.html
│   │   │   │       └── assets/...
│   │   │   ├── greenfieldberryfarm.com/
│   │   │   │   └── frontend/...
│   │   │   └── ...other client sites...
│   │   │
│   │   └── platform/
│   │       ├── app.py
│   │       ├── modules/
│   │       ├── requirements.txt
│   │       └── ...existing platform code...
│   │
│   └── compose/                                                      # NEW
│       └── platform/                                                 # NEW (stack name boundary)
│           ├── docker-compose.yml                                    # NEW
│           ├── .env                                                  # NEW (not committed; template often is)
│           ├── env.example                                           # NEW (committed template)
│           │
│           ├── keycloak/                                             # NEW
│           │   ├── realm/                                            # NEW (optional)
│           │   │   └── fruitful-realm-export.json                    # NEW (optional)
│           │   └── themes/                                           # NEW (optional)
│           │       └── fruitful-theme/...
│           │
│           ├── postgres/                                             # NEW
│           │   ├── initdb/                                           # NEW (optional)
│           │   │   └── 00-keycloak-db.sql                            # NEW (optional)
│           │   └── backups/                                          # NEW (directory exists; contents ignored)
│           │
│           └── flask-bff/                                            # NEW
│               ├── Dockerfile                                        # NEW
│               ├── gunicorn.conf.py                                  # NEW
│               └── entrypoint.sh                                     # NEW (optional)
│
└── .gitignore
```

### Notes on intent:

  - `etc/nginx/sites-available/auth.*` and `api.*` are present in the repo, but you do not enable them yet (no symlinks in `sites-enabled` or you keep the symlink step as a manual action).
  - `etc/systemd/system/compose-platform.service` exists, but you do not `systemctl enable` it yet.
  - `srv/compose/platform/` contains a production-ish Compose stack: Keycloak + Postgres + Flask BFF.

The Postgres here is dedicated to Keycloak only. Your platform remains “no Postgres” unless you later choose to add one.

---

## Server hierarchy (intermediate state after sync, not active yet)

This shows what exists on the box after you deploy files, but before you:
  - enable vhosts,
  - reload NGINX for new sites,
  - enable/start compose-platform.service,
  - run docker compose up -d.

```bash
/home/admin/
├── aws-box/                                                          # your checked-out mirror repo (optional)
│   ├── etc/...
│   └── srv/...
│
/etc/
├── nginx/
│   ├── sites-available/
│   │   ├── fruitfulnetworkdevelopment.com.conf
│   │   ├── greenfieldberryfarm.com.conf
│   │   ├── api.fruitfulnetworkdevelopment.com.conf                   # PRESENT but not enabled yet
│   │   └── auth.fruitfulnetworkdevelopment.com.conf                  # PRESENT but not enabled yet
│   │
│   ├── sites-enabled/
│   │   ├── fruitfulnetworkdevelopment.com.conf -> ../sites-available/fruitfulnetworkdevelopment.com.conf
│   │   └── greenfieldberryfarm.com.conf -> ../sites-available/greenfieldberryfarm.com.conf
│   │   # NOTE: no symlink yet for api.* or auth.* (intermediate state)
│   │
│   └── snippets/
│       ├── ssl_params.conf
│       └── proxy_common.conf                                         # PRESENT, referenced by new vhosts
│
├── systemd/
│   └── system/
│       ├── platform.service
│       ├── certbot-renew.service
│       ├── certbot-renew.timer
│       └── compose-platform.service                                  # PRESENT but not enabled/started
│
└── letsencrypt/
    └── ...existing certbot state...

/srv/
├── webapps/
│   ├── clients/
│   │   ├── fruitfulnetworkdevelopment.com/
│   │   │   └── frontend/...
│   │   ├── greenfieldberryfarm.com/
│   │   │   └── frontend/...
│   │   └── ...other clients...
│   │
│   └── platform/
│       └── ...existing flask platform code...
│
└── compose/                                                          # NEW directory is present
    └── platform/
        ├── docker-compose.yml
        ├── env.example                                               # exists
        ├── .env                                                      # may or may not exist yet (you decide)
        │
        ├── keycloak/
        │   ├── realm/
        │   │   └── fruitful-realm-export.json                         # optional
        │   └── themes/...
        │
        ├── postgres/
        │   ├── initdb/
        │   │   └── 00-keycloak-db.sql                                 # optional
        │   └── backups/
        │
        └── flask-bff/
            ├── Dockerfile
            ├── gunicorn.conf.py
            └── entrypoint.sh

/var/lib/
└── docker/
    ├── volumes/
    │   ├── platform_keycloak_data/                                    # will be created on first up
    │   └── platform_postgres_data/                                    # will be created on first up
    └── ...

/var/log/
├── nginx/
│   └── ...existing logs...
└── journal/
    └── ...systemd logs...
```

---

## Low-risk Migration Path
  - Containerize Keycloak first (new capability, isolated change).
  - Keep Flask platform as-is under systemd initially.
  - Once Keycloak is stable, containerize Flask:
  - build container for your platform code
  - change NGINX upstream from host Gunicorn → container port
  - remove/disable platform.service afterward
  This minimizes the risk of breaking production while you introduce authentication.

### Port model and “localhost binding”
  A secure, simple approach on a single EC2 host is:
  - Publish container ports only to localhost (not 0.0.0.0)
  - NGINX is the only public ingress
  #### For example:
  - Keycloak container listens internally on 8080, published to `127.0.0.1:8081`
  - Flask container listens internally on 8000, published to `127.0.0.1:8001`
  Then:
  - `auth.fruitfulnetworkdevelopment.com` → NGINX → `http://127.0.0.1:8081`
  - `api.fruitfulnetworkdevelopment.com` → NGINX → `http://127.0.0.1:8001`
  This reduces exposed surface area and keeps the security model crisp.

### Lightweight production DB
  Run a small DB container inside the same Compose stack (Postgres). This does not mean your application “uses Postgres”; it means Keycloak’s state (users, sessions, config) is persisted safely.

### How BFF fits into the setup (what actually happens at runtime)
  “client sites remain mostly static; all sign-ins are on `fruitfulnetworkdevelopment.com` using BFF.”
  #### A clean flow is:
  - User visits a static client site (served by NGINX).
  - User clicks “Sign in” → redirect to your BFF (Flask) at fruitfulnetworkdevelopment.com/login (or api.fruitfulnetworkdevelopment.com/login).
  - BFF initiates OIDC redirect to Keycloak (auth.*).
  - Keycloak authenticates user → redirects back to BFF callback endpoint.
  - BFF exchanges code for tokens server-to-server, then sets a secure session cookie.
  - Static site JS calls `https://api.fruitfulnetworkdevelopment.com/api/`... (or the same domain via reverse-proxy) and the cookie authenticates the call.
  Key point: static sites never store tokens. The session lives in the BFF.

### NGINX config pattern
  - vhosts is already managed under /etc/nginx/sites-available and symlink into sites-enabled.
  Add:
  - auth.fruitfulnetworkdevelopment.com.conf → proxy to Keycloak
  - api.fruitfulnetworkdevelopment.com.conf → proxy to Flask container
  Conceptually:
  - auth.* is a “pure proxy vhost”
  - api.* is a “pure proxy vhost”
  fruitfulnetworkdevelopment.com remains static, but can optionally proxy /login, /logout, /account, etc., for the BFF auth UI to “live” on the main domain.

### Systemd unit that runs docker compose up -d
  Keep NGINX as it is, and add a unit like compose-platform.service that:
  - starts after Docker
  - runs docker compose up -d
  - optionally runs docker compose down on stop
  Fits in existing “systemd is the supervisor” pattern.

 ---
