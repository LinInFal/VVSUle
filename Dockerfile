FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    firefox-esr \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libxcomposite1 \
    libasound2 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libnss3 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем последнюю версию geckodriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz" \
    && tar -xzf geckodriver-v0.36.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver-v0.36.0-linux64.tar.gz \
    && geckodriver --version

# Проверяем версию Firefox
RUN firefox --version

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Проверяем доступность geckodriver
RUN which geckodriver && ls -la /usr/local/bin/geckodriver

# Устанавливаем зависимости с указанием версий для совместимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Устанавливаем переменные окружения для Firefox
ENV MOZ_HEADLESS=1
ENV DISPLAY=:99

# Команда запуска
CMD ["python", "main.py"]