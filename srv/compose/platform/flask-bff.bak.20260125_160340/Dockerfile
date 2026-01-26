FROM python:3.12-slim
# FROM python:3.11-slim ~ OLD

# ENV PYTHONDONTWRITEBYTECODE=1 \ ~ OLD
#     PYTHONUNBUFFERED=1 ~ OLD

WORKDIR /app

# RUN addgroup --system app && adduser --system --ingroup app app ~ OLD

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# COPY requirements.txt ./ ~ OLD
# RUN pip install --no-cache-dir --upgrade pip \ ~ OLD
#     && pip install --no-cache-dir -r requirements.txt ~ OLD

# Copy application code
COPY app.py .
COPY gunicorn.conf.py .
COPY entrypoint.sh .
# COPY . . ~ OLD

RUN chmod +x /app/entrypoint.sh
# RUN chmod +x entrypoint.sh ~ OLD

# USER app  ~ OLD

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# ENTRYPOINT ["./entrypoint.sh"] ~ OLD
