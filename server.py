from flask import Flask, jsonify
from threading import Thread
import traceback

import crawler  # crawler.py 모듈을 임포트

app = Flask(__name__)

# 크롤러 실행 상태 관리용 변수
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
        driver, wait = crawler.create_driver()
        try:
            crawler.main(driver, wait)
            crawler_last_result = "크롤러 실행 성공"
        finally:
            driver.quit()
    except Exception:
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
    app.run(host='0.0.0.0', port=8080)
