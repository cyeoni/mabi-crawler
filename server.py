from flask import Flask, request
from threading import Thread
import mabi_update  # 크롤링 코드 불러오기

app = Flask(__name__)

@app.route("/")
def home():
    return "Mabinogi Crawler 서버 작동 중!"

@app.route("/update-power", methods=["GET"])
def update_power():
    if request.args.get("key") != "mabi123":
        return "Unauthorized", 403
    Thread(target=mabi_update.main).start()
    return "크롤링 시작됨!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)