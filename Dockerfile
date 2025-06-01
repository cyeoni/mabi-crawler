# 베이스 이미지 (Python + Chrome 포함)
FROM python:3.11-slim

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive

# 필요한 OS 패키지 설치 (Chrome, Chromium 드라이버 등)
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg2 \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Chrome 설치
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉터리 설정
WORKDIR /app

# 요구사항 복사 및 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . /app/

# 환경 변수 (Chromedriver가 Chrome 위치를 찾도록)
ENV CHROME_PATH=/usr/bin/google-chrome

# Flask 실행 포트 설정
ENV PORT=8080

# 외부에 8080 포트 노출
EXPOSE 8080

# 컨테이너 시작 시 서버 실행
CMD ["python", "server.py"]
