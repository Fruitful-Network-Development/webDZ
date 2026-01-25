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

### Deploy `/srv` payload (static sites + platform code)

For the initial commit that only includes changes under `srv/`:
```bash
sudo rsync -a --delete /home/admin/aws-box/srv/ /srv/
sudo chown -R admin:admin /srv/webapps
```
, otherwise run:
```bash
sudo rsync -a --delete --exclude 'webapps/platform/venv' /home/admin/aws-box/srv/ /srv/
```
This prevents the deletion of /srv/webapps/platform/venv because it’s not in git.

#### Dry run Test
To check what files would be updated before deploying run:
```bash
sudo rsync -av --delete --dry-run --exclude 'webapps/platform/venv' /home/admin/aws-box/srv/ /srv/
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
sudo systemctl restart platform.service
sudo systemctl status platform.service --no-pager
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
