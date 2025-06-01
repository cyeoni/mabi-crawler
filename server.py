import os
from flask import Flask, request, jsonify
from threading import Thread
import mabi_update  # 수정된 mabi_update 임포트

app = Flask(__name__)

@app.route("/")
def home():
    return "Mabinogi Crawler 서버 작동 중!"

@app.route("/update-power", methods=["GET"])
def update_power():
    if request.args.get("key") != "mabi123":
        return jsonify({"error": "Unauthorized"}), 403

    # 크롤러 작업을 백그라운드 쓰레드에서 실행
    Thread(target=mabi_update.main).start()
    return jsonify({"status": "크롤링 시작됨!"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway 등 환경변수 포트 지원
    app.run(host="0.0.0.0", port=port)
