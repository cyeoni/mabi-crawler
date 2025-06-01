import os
from flask import Flask, request
from threading import Thread
from mabi_update import update_power_data  # 크롤링 함수 직접 호출

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
            update_power_data()
            print("✅ 크롤링 완료")
        except Exception as e:
            print("❌ 크롤링 실패:", e)

    Thread(target=run_update).start()
    return "✅ 크롤링 실행 시작", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
