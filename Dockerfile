FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

# gunicorn으로 backend/app.py의 Flask 앱(app) 실행
CMD ["sh", "-c", "gunicorn --chdir backend app:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 60"]
