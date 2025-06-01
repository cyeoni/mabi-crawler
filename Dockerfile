FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils chromium chromium-driver python3-distutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV PATH=$PATH:/usr/lib/chromium

# chromedriver 위치 심볼릭 링크 (필요시)
RUN ln -sf /usr/lib/chromium/chromedriver /usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "server.py"]
