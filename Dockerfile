FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

# Un seul worker (l'état des jobs est en mémoire) ; les threads gèrent la
# concurrence des requêtes, les téléchargements tournent dans leurs propres threads.
CMD gunicorn --workers 1 --threads 16 --timeout 600 --bind 0.0.0.0:$PORT app:app
