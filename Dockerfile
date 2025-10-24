# Backend Dockerfile
FROM python:3.12-slim

# Çalışma dizini
WORKDIR /app

# Sistemde gerekli paketler
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

# uv (hızlı paket yöneticisi) kurulumu
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Proje dosyalarını kopyala
COPY . .

# Bağımlılıkları kur
RUN uv sync --frozen

# Ortam değişkenlerini belirle (Docker içinden veritabanına bağlanmak için)
ENV POSTGRES_SERVER=localhost
ENV POSTGRES_PORT=5432

# Portu aç
EXPOSE 8000

# Uygulamayı çalıştır
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
