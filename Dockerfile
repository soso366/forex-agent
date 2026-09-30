# Image unique pour le cloud : backtest (maintenant) et scheduler 24/7 (plus tard, après validation).
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# data/ et results/ doivent être sur un volume persistant (reprise après redémarrage).
VOLUME ["/app/data", "/app/results"]
# Par défaut : le premier vrai backtest. Le scheduler 24/7 se lancera plus tard avec : python -m forex_agent loop
CMD ["python", "-m", "forex_agent", "pipeline"]
