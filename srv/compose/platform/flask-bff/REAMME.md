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
├── app.py
├── auth/
|  ├── authz.py
|  ├── entrypoint.sh
|  └── __init__.py
├── webapp/
|  ├── web-app.py
|  └── __init__.py
└── portal/
   ├── portal-app.py
   ├── UI/
   |  ├── tenant/
   |  └── admin/
   └── services/
```

There are no uses of in-memory state (temporary, per worker). Rather, the configuration exists inside Postgres and is treated it as the authoritative source (dictated by the schema).

The webapp directory is for later development of services that involve api calls, that are verified by the portal apllication.
