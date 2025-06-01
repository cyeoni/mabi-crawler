from flask import Flask, jsonify, request
import traceback
import crawler  # crawler.py 모듈

app = Flask(__name__)

@app.route('/update-power')
def update_power():
    key = request.args.get("key")
    if key != "mabi123":
        return jsonify({"error": "Invalid key"}), 403

    try:
        driver, wait = crawler.create_driver()
        try:
            crawler.main(driver, wait)
        finally:
            driver.quit()
        return jsonify({"status": "success"})
    except Exception:
        traceback.print_exc()
        return jsonify({"status": "failed", "reason": "crawler error"}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
