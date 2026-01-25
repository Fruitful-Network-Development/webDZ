FROM python:3.12-slim
# FROM python:3.11-slim ~ OLD

# ENV PYTHONDONTWRITEBYTECODE=1 \ ~ OLD
#     PYTHONUNBUFFERED=1 ~ v0

WORKDIR /app
# RUN addgroup --system app && adduser --system --ingroup app app ~ v0

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# COPY requirements.txt ./ ~ v0
# RUN pip install --no-cache-dir --upgrade pip \ ~ v0
#     && pip install --no-cache-dir -r requirements.txt ~ v0

# Copy application code (full tree)
COPY . /app
# COPY app.py . ~ v1
# COPY gunicorn.conf.py . ~ v1
# COPY entrypoint.sh . ~ v1
# COPY . . ~ v0

RUN chmod +x /app/entrypoint.sh
# RUN chmod +x entrypoint.sh ~ OLD

# USER app  ~ OLD
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# ENTRYPOINT ["./entrypoint.sh"] ~ OLD
