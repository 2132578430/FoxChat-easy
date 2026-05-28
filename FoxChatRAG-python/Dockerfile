# ============================================
# App image: application code only (deps from base)
# ============================================
FROM foxchat-python-base:latest
WORKDIR /app

# Copy application code
COPY main.py .
COPY app/ app/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
