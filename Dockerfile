FROM python:3.11-slim

# 필수 패키지 설치 + Chromium & 드라이버
RUN apt-get update && apt-get install -y \
    wget unzip \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils chromium chromium-driver \
    python3-distutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

# 환경 변수로 크롬 경로 지정 (undetected_chromedriver가 자동으로 찾아서 안 해도 됨)
ENV CHROME_PATH=/usr/bin/chromium

# Flask 서버를 실행하도록 변경 (mabi_update.py는 크롤러만 하므로 서버용 server.py 실행 권장)
CMD ["python", "server.py"]
