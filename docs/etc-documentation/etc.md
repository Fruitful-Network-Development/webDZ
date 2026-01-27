## /etc

## Layout

```text
├── etc/
    ├── nginx/
    │   ├── mime.types
    │   ├── nginx.conf
    │   ├── sites-available/
    │   └── sites-enabled/
    └── systemd/system
            ├── certbot-renew.service
            ├── platform.service
            ├── certbot-renew.timer
            ├── compose-platform.service
            ├── sshd.service
            ├── multi-user.target.wants/
            └── sockets.target.wants/
```

## Host OS configuration

This directory documents the **host-level responsibilities** that must remain
on the OS instead of inside containers.

**Responsibilities**
- **Ingress & TLS**: NGINX configuration and TLS termination (Certbot).
- **Service supervision**: systemd unit files for host-native services and
  Compose stacks.
- **Host safety controls**: log rotation, journald limits, and other OS-level
  guardrails.

**Non-responsibilities**

- Application business logic (lives under `/srv`).
- Identity logic (managed by the Auth stack under `/srv/compose`).
- Stateful application data (lives in runtime directories or volumes).

**Change policy**
> Changes are inert until services are explicitly reloaded or restarted.
> New vhosts are inactive until symlinked into `sites-enabled`.
> New systemd units are inactive until explicitly enabled and started.

## /etc/nginx

**Responsibilities**
- TLS termination for all domains.
- Static site delivery for client frontends.
- Reverse-proxy routing to localhost-bound backends.
- Maintaining shared snippets (`ssl_params.conf`, `proxy_common.conf`).

**Routing model**

- Domain-based separation for each client site.
- Static sites are served directly from `/srv/webapps/clients/<domain>/frontend`.
- API or auth traffic is proxied to backend services that bind only to
  `127.0.0.1`.

**Security posture**

- No direct exposure of container ports to the public internet.
- No authentication or business logic inside NGINX.
- Consistent headers and TLS configuration via shared snippets.

mime.types
```
types {
    text/html                             html htm shtml;
    text/css                              css;
    text/xml                              xml;
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    application/javascript                js;
    application/json                      json;
    application/xml                       rss atom;
    image/png                             png;
    image/x-icon                          ico;
    image/svg+xml                         svg svgz;
    application/pdf                       pdf;
    application/zip                       zip;
    application/gzip                      gz;
    audio/mpeg                            mp3;
    video/mp4                             mp4;
    video/x-msvideo                       avi;
    application/octet-stream              bin exe dll;
}
```

nginx.conf
```
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    ##
    # Basic settings
    ##
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ##
    # Logging
    ##
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    ##
    # Gzip settings (optional)
    ##
    gzip on;
    gzip_disable "msie6";

    ##
    # Load additional configs
    ##
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

---

## /etc/nginx/sites-available

**Vhost patterns**

This directory holds **inactive** virtual host definitions. Files here do
nothing until symlinked into `sites-enabled`.

**Naming convention**

- `<domain>.conf` for site-specific vhosts.
- `auth.<domain>.conf` for Keycloak/Auth proxy vhosts.
- `api.<domain>.conf` for BFF/API proxy vhosts.

**Static site vhost**

- Serves `root` from `/srv/webapps/clients/<domain>/frontend`.
- Provides `.well-known/acme-challenge` handling for Certbot.
- Redirects HTTP to HTTPS after certificates are provisioned.

**Proxy-only vhost**

- Proxies all requests to localhost-bound upstreams.
- Uses shared proxy snippets to standardize headers and timeouts.
- Intended for the Auth/BFF stack (auth.* and api.* domains).

api.fruitfulnetworkdevelopment.com.conf
```
server {
    server_name api.fruitfulnetworkdevelopment.com;

    # Flask BFF via localhost-only published port from Docker
    location / {
        proxy_pass http://127.0.0.1:8001;

        # Explicit proxy headers (avoid hidden behavior via snippets)
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Keepalive/correctness
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/api.fruitfulnetworkdevelopment.com/fullchain>
    ssl_certificate_key /etc/letsencrypt/live/api.fruitfulnetworkdevelopment.com/privk>
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    listen 80;
    server_name api.fruitfulnetworkdevelopment.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    return 301 https://$host$request_uri;
}

```

api.fruitfulnetworkdevelopment.com.http-only.conf
```
server {
    listen 80;
    server_name api.fruitfulnetworkdevelopment.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        default_type "text/plain";
    }

    # Everything else is intentionally inert for now
    location / {
        return 404;
    }
}
```

auth.fruitfulnetworkdevelopment.com.conf
```
server {
    server_name auth.fruitfulnetworkdevelopment.com;

    # Keycloak via localhost-only published port from Docker
    location / {
        proxy_pass http://127.0.0.1:8081;
        include /etc/nginx/sites-available/snippets/proxy_common.conf;

        # Keepalive / correctness
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/auth.fruitfulnetworkdevelopment.com/fullchai>
    ssl_certificate_key /etc/letsencrypt/live/auth.fruitfulnetworkdevelopment.com/priv>
    include /etc/nginx/sites-available/snippets/ssl_params.conf; # managed by Certbot
}

server {
    listen 80;
    server_name auth.fruitfulnetworkdevelopment.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    return 301 https://$host$request_uri;
}
```

cuyahogaterravita.com.conf
```
server {
    server_name cuyahogaterravita.com www.cuyahogaterravita.com;

    root /srv/webapps/clients/cuyahogaterravita.com/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/privkey.p>
    # Certbot created one certificate lineage stored at:
    # /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/
    # That single certificate is cryptographically valid for all hostnames

    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}
server {
    listen 80;
    server_name cuyahogaterravita.com www.cuyahogaterravita.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    return 301 https://$host$request_uri;
}
```

cuyahogavalleycountrysideconservancy.org.conf
```
# /etc/nginx/sites-available/cuyahogavalleycountrysideconservancy.org.conf

# HTTPS server block
server {
    server_name cuyahogavalleycountrysideconservancy.org www.cuyahogavalleycountryside>

    root /srv/webapps/clients/cuyahogavalleycountrysideconservancy.org/frontend/;
    index index.html index.htm;

    # Default handler for the rest of the paths
    location / {
        try_files $uri $uri/ =404;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/privkey.p>
    # Certbot created one certificate lineage stored at:
    # /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/
    # That single certificate is cryptographically valid for all hostnames

    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

# HTTP server block: redirect to HTTPS
server {
    listen 80;
    server_name cuyahogavalleycountrysideconservancy.org www.cuyahogavalleycountryside>

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    return 301 https://$host$request_uri;
}
```

fruitfulnetworkdevelopment.com.conf
```
server {
    server_name fruitfulnetworkdevelopment.com www.fruitfulnetworkdevelopment.com;

    root /srv/webapps/clients/fruitfulnetworkdevelopment.com/frontend;
    index index.html;

    # Serve the main HTML with no-cache so new deployments are visible
    # without needing a cache-busting query string like ?v=2
    location = / {
        add_header Cache-Control "no-cache, must-revalidate";
        try_files $uri $uri/ =404;
    }

    # Default handler for the rest of the paths
    location / {
        try_files $uri $uri/ =404;
    }

    # NOTE: Intentionally no /api/ proxy here.
    # This enforces "no client-site coupling" — the static site does not
    # route any paths to the BFF.

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/fullchain.pem>
    ssl_certificate_key /etc/letsencrypt/live/fruitfulnetworkdevelopment.com/privkey.p>
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    listen 80;
    server_name fruitfulnetworkdevelopment.com www.fruitfulnetworkdevelopment.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    return 301 https://$host$request_uri;
}
```

---

## /etc/nginx/sites-available/snippets/

proxy_common.conf
```
HERE
```

ssl_params.conf
```
HERE
```

---
