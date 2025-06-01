import os
from flask import Flask, request
from threading import Thread
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Mabinogi Crawler 서버 작동 중!"

@app.route("/update-power", methods=["GET"])
def update_power():
    if request.args.get("key") != "mabi123":
        return "❌ Unauthorized", 403

    def run_update():
        try:
            res = requests.get("http://localhost:8080/update-power?key=mabi123")
            print(f"크롤링 트리거 요청 응답: {res.status_code} {res.text}")
        except Exception as e:
            print("크롤링 트리거 실패:", e)

    Thread(target=run_update).start()
    return "✅ 크롤링 요청 보냄", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
