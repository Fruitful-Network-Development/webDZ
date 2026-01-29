# FLASK BFF APLICATION

At this aplications core, there is `main.py`. IT employs two secondary principal files, `websites.py` & `portal.py`.

## LAYOUT
```
aws-box/srv/compose/platform/flask-bff/
├── README.md
├── .dockerignore
├── Dockerfile
├── gunicorn.conf.py
├── requirements.txt
├── main.py
├── auth/
  ├── authz.py
  ├── entrypoint.sh
├── webapp/
  ├── web-app.py
└── portal/
  ├── portal-app.py
  ├── UI/
  ├── services/


├── portal.py
├── websites.py
└── __init__.py
```

There are no uses of in-memory state (temporary, per worker). Rather, the configuration exists inside Postgres and is treated it as the authoritative source (dictated by the schema).
