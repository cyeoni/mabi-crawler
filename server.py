from flask import Flask, jsonify
from threading import Thread
import time
import sys
import traceback

import crawler.py  # 크롤러 코드가 있는 파일 이름을 여기로 바꾸세요 (예: crawler.py)

app = Flask(__name__)

# 백그라운드에서 크롤러 실행 상태 관리용
crawler_running = False
crawler_last_result = None
crawler_last_error = None

def run_crawler():
    global crawler_running, crawler_last_result, crawler_last_error
    if crawler_running:
        return
    crawler_running = True
    crawler_last_result = None
    crawler_last_error = None
    try:
        # 크롤러 함수 실행 (your_crawler_module.main 등)
        driver, wait = your_crawler_module.create_driver()
        try:
            your_crawler_module.main(driver, wait)
            crawler_last_result = "크롤러 실행 성공"
        finally:
            driver.quit()
    except Exception as e:
        crawler_last_error = traceback.format_exc()
    finally:
        crawler_running = False

@app.route('/start-crawl', methods=['POST'])
def start_crawl():
    if crawler_running:
        return jsonify({"status": "already_running"}), 409
    # 백그라운드 스레드로 크롤러 실행
    thread = Thread(target=run_crawler)
    thread.start()
    return jsonify({"status": "started"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "running": crawler_running,
        "last_result": crawler_last_result,
        "last_error": crawler_last_error
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
