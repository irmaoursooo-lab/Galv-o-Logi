FROM python:3.11-slim

WORKDIR /app

# Instalar dependências essenciais de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante da aplicação
COPY . .

# Variáveis de ambiente
ENV PYTHONPATH=.
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

# Comando de inicialização em produção
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
