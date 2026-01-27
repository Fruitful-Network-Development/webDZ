## Workflow

### Update the repo on the server

```bash
ssh -i ~/.ssh/aws-main-key.pem admin@52.70.228.90
```

Run on the instance:

```bash
cd /home/admin/aws-box
git fetch origin
git pull --ff-only
```

If `git pull --ff-only` fails, stop (it means local drift). Don’t “fix” it in
prod. Reset to origin (see the drift section below).

### Deploy `/srv` payload (static sites + platform stack)

For the initial commit that only includes changes under `srv/`:
```bash
sudo rsync -a --delete /home/admin/aws-box/srv/ /srv/
sudo chown -R admin:admin /srv/webapps /srv/compose
```

#### Dry run Test
To check what files would be updated before deploying run:
```bash
sudo rsync -av --delete --dry-run /home/admin/aws-box/srv/ /srv/
```

### Deploy `/etc` payload (nginx, systemd, etc.)

Only if your commit includes changes under `etc/`:

```bash
sudo rsync -a --delete /home/admin/aws-box/etc/nginx/ /etc/nginx/
```

#### Dry run Test
To check what files would be updated before deploying run:
```bash
sudo rsync -av --delete --dry-run /home/admin/aws-box/etc/nginx/ /etc/nginx/
```

### Apply service changes safely

Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

systemd units (only if you changed `etc/systemd/system/*.service`):

```bash
sudo systemctl daemon-reload
sudo systemctl restart compose-platform.service
sudo systemctl status compose-platform.service --no-pager
```

### Sanity checks

```bash
curl -I https://fruitfulnetworkdevelopment.com | head -10
curl -I https://cuyahogaterravita.com | head -10
sudo certbot renew --dry-run
```

---

Good hygene in a deployment like this includes excludes that just always stay safe with:
```bash
sudo rsync -a --delete --dry-run \
  --exclude '__pycache__/' --exclude '*.pyc' --exclude '.pytest_cache/' \
  /home/admin/aws-box/srv/compose/platform/flask-bff/ \
  /srv/compose/platform/flask-bff/

sudo rsync -a --delete --dry-run \
  /home/admin/aws-box/srv/compose/platform/platform-schema/ \
  /srv/compose/platform/platform-schema/
```

Here are the direct links to test:
  Login → admin console
    `https://api.fruitfulnetworkdevelopment.com/login?tenant=platform&return_to=/admin`
  Admin home (after login)
    `https://api.fruitfulnetworkdevelopment.com/admin`
  Tables admin
    `https://api.fruitfulnetworkdevelopment.com/admin/tables`
  Lists admin
    `https://api.fruitfulnetworkdevelopment.com/admin/lists`
  Record browser (example, replace IDs)
    `https://api.fruitfulnetworkdevelopment.com/admin/tables/<table_local_id>/records?tenant_id=platform`
  If you want the tenant console too:
    `https://api.fruitfulnetworkdevelopment.com/t/platform/console`


---

# Rescue workflow

In EC2 console → Instance → Actions → Monitor and troubleshoot:
  - Get system log
  - Get instance screenshot

1. Stop the affected instance
2. Detach the root EBS volume
3. Attach to a rescue instance
  - Attach as secondary volume (e.g. `/dev/xvdbf`)
  - Use an instance you can SSH into
4. SSH into the Rescue Instance
```bash
ssh -i ~/.ssh/aws-main-key-2026.pem admin@54.172.16.165
```

5. Mount the volume
```bash
sudo mkdir -p /mnt/rescue
sudo mount /dev/xvdbf1 /mnt/rescue   # partition name may vary
```

## After Fixes

### A. Treat SSH as immutable infrastructure
```bash
sudo systemctl enable ssh
sudo systemctl status ssh
```

Then verify:
```bash
ls -l /etc/systemd/system/multi-user.target.wants/ssh.service
```

### B. Add an explicit boot-time assertion (simple and effective)
Create a drop-in safeguard unit that fails loudly if SSH is not enabled.
```bash
sudo nano /etc/systemd/system/ssh-assert.service
```
```ini
[Unit]
Description=Assert SSH enabled
After=network.target
ConditionPathExists=/etc/systemd/system/multi-user.target.wants/ssh.service

[Service]
Type=oneshot
ExecStart=/bin/true

[Install]
WantedBy=multi-user.target
```
Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ssh-assert.service
```

### C. Lock down SSH enablement explicitly (optional but strong)
If you want to be aggressive:
```bash
sudo chattr +i /etc/systemd/system/multi-user.target.wants/ssh.service
```
This makes the symlink immutable until you remove the flag.

To undo later:
```bash
sudo chattr -i /etc/systemd/system/multi-user.target.wants/ssh.service
```
This is rarely necessary, but for single-admin servers it is effective.

When you re-enable Docker later, do it intentionally:
```bash
sudo systemctl enable docker
sudo systemctl start docker
```
And ensure:
  - SSH starts before Docker
  - Heavy services (Keycloak) are not auto-started on tiny instances


---

# Debian EC2 Rebuild Guide (aws-box)

> **Scope:** Manual, step-by-step rebuild instructions for a new Debian EC2 instance using the **single** repository `Fruitful-Network-Development/aws-box`.

### 0) Provision the EC2 instance
1. Launch a **Debian** EC2 instance.
2. Open inbound security group ports: **22**, **80**, **443**.
3. Confirm DNS A records point to the new instance IP:
   - fruitfulnetworkdevelopment.com
   - www.fruitfulnetworkdevelopment.com
   - cuyahogaterravita.com
   - www.cuyahogaterravita.com

### 1) One-time base packages and permissions (Debian)
```bash
ssh admin@<public-ip>

sudo apt-get update
sudo apt-get install -y git rsync nginx python3 python3-venv python3-pip certbot python3-certbot-nginx
```
Enable nginx:
```bash
sudo systemctl enable --now nginx
```
Create live app directories:
```
sudo mkdir -p /srv/webapps/clients /srv/compose/platform
sudo chown -R admin:admin /srv/webapps /srv/compose
```

### 2) Set up GitHub access from the server

#### 2.A) Generate an SSH key on the server
```bash
ssh-keygen -t ed25519 -C "admin@$(hostname)-aws-box"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```
The program will prompted  for a "file in which to save the key."
      Pressed Enter (leaving it blank), defaulting it to: /home/admin/.ssh/id_ed25519
Copy the printed public key into GitHub:
      GitHub → Settings → SSH and GPG keys → New SSH key

Test auth
```bash
ssh -T git@github.com
```

#### 2.B) Clone your aws-box repo to become the only source-of-truth
```bash
cd /home/admin
git clone git@github.com:Fruitful-Network-Development/aws-box.git
cd /home/admin/aws-box
git status
```

### 3) Install the repo’s system configs into live `/etc` safely

#### 3.A) Deploy nginx from repo → live
```bash
sudo rsync -a --delete /home/admin/aws-box/etc/nginx/ /etc/nginx/
```
Remove the default site (prevents wrong site being served):
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```
Validate and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### 3.B) Deploy systemd units from repo → live
```bash
sudo rsync -a /home/admin/aws-box/etc/systemd/system/ /etc/systemd/system/
sudo systemctl daemon-reload
```
Do not start services yet unless platform code exists.

### 4) Deploy client frontends (repo → live)
If your repo contains client skeletons under `srv/webapps/clients/...`:
```bash
sudo rsync -a /home/admin/aws-box/srv/webapps/clients/ /srv/webapps/clients/
sudo chown -R admin:admin /srv/webapps/clients
```

### 5) Deploy platform stack (Compose)
Platform stack comes from aws-box:
```bash
sudo rsync -a --delete /home/admin/aws-box/srv/compose/platform/ /srv/compose/platform/
sudo chown -R admin:admin /srv/compose/platform
```

### 6) Start the platform services (Compose)
```bash
cd /srv/compose/platform
docker compose up -d
```
Verify local backend:
```bash
curl -sS -I http://127.0.0.1:8001/health | head
```

### 8) TLS (certbot) after DNS and port 80 are correct
Confirm DNS points at this instance:
```bash
sudo apt install -y dnsutils
dig +short fruitfulnetworkdevelopment.com
curl -s https://checkip.amazonaws.com
```
Confirm port 80 reachable (from your laptop too). Then:
```bash
sudo certbot --nginx -d fruitfulnetworkdevelopment.com -d www.fruitfulnetworkdevelopment.com \
  -d cuyahogaterravita.com -d www.cuyahogaterravita.com
```
Test renewal:
```bash
sudo certbot renew --dry-run
```

### 9) Add the deploy scripts (prevention)
Create a scripts folder in your repo and add:
 - scripts/deploy_nginx.sh (rsync → nginx -t → reload)
   - scripts/deploy_systemd.sh (rsync → daemon-reload → restart platform)
If you want, I will give you the exact scripts again but with your final chosen paths.


## Historical Note (Deprecated)
Earlier versions of this document described a monolithic deployment
workflow using GH-etc, per-file sync scripts, and a single deploy_platform.sh.
That approach has been retired.

The current and supported model is:
- Single source-of-truth repo: /home/admin/aws-box
- Explicit deploy scripts for nginx and systemd
- No direct editing of /etc or partial syncs

Refer only to the steps above for new instance setup and updates.

## Repo Deploy

### Update the repo working copy (/home/admin/aws-box)
```bash
cd /home/admin/aws-box
git status
git fetch origin
git pull --ff-only
```
If git pull --ff-only fails with “not possible to fast-forward,” stop and paste the output (it means local changes exist and we need to reconcile safely).

### Sanity check what changed (recommended)
```bash
git log -5 --oneline
git diff --name-only HEAD@{1}..HEAD
```

### Deploy nginx config from repo → live /etc/nginx
Assuming your repo contains etc/nginx/...:
```bash
sudo rsync -a --delete /home/admin/aws-box/etc/nginx/ /etc/nginx/
```

Prevent the default site from hijacking requests (common source of “old site showing”):
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Validate and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

Confirm the correct server blocks are live:
```bash
sudo nginx -T | grep -RIn "server_name .*fruitfulnetworkdevelopment.com" /etc/nginx
```

### Deploy systemd units from repo → live /etc/systemd/system

If your repo contains etc/systemd/system/...:
```bash
sudo rsync -a /home/admin/aws-box/etc/systemd/system/ /etc/systemd/system/
sudo systemctl daemon-reload

```

If you have platform.service and want it restarted to pick up changes:
```bash
sudo systemctl restart platform.service
sudo systemctl status platform.service --no-pager
```

### Deploy /srv content from repo → live /srv
Be careful here: you generally want /srv/webapps content, not everything under /srv.

#### Deploy client frontends
If repo has srv/webapps/clients/...:
```bash
sudo rsync -a --delete /home/admin/aws-box/srv/webapps/clients/ /srv/webapps/clients/
sudo chown -R admin:admin /srv/webapps/clients
```
#### Deploy platform stack (Compose)
If repo has srv/compose/platform/...:
```bash
sudo rsync -a --delete /home/admin/aws-box/srv/compose/platform/ /srv/compose/platform/
sudo chown -R admin:admin /srv/compose/platform
cd /srv/compose/platform
docker compose up -d
```

### Quick end-to-end checks
Local (on the server):
```bash
curl -sS -I http://127.0.0.1:8001/health | head -20
curl -sS -I http://localhost/ | head -20
```
From your laptop:
```bash
curl -I https://fruitfulnetworkdevelopment.com
curl -I https://cuyahogaterravita.com
```
---
