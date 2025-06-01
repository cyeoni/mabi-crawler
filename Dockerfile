FROM python:3.11-slim

# 크롬, 크롬 드라이버, 필요 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    fonts-liberation \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    ca-certificates \
    fonts-liberation \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 구글 크롬 설치 (stable)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 코드 복사
COPY . /app

# Python 패키지 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 환경변수로 Chrome 실행 옵션 설정
ENV CHROME_BIN=/usr/bin/google-chrome-stable

# 앱 실행
CMD ["python", "server.py"]
