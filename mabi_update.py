import os
import json
import time
import gspread
import undetected_chromedriver as uc
import functools
import subprocess

print = functools.partial(print, flush=True)

from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, request, jsonify

app = Flask(__name__)

# 크롬 버전 체크 함수
def check_chrome_version():
    cmds = [
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chrome",
        "chromedriver",
    ]
    for cmd in cmds:
        try:
            version = subprocess.check_output([cmd, "--version"]).decode().strip()
            print(f"브라우저 버전 확인: {version} ({cmd})")
            return
        except Exception:
            print(f"{cmd} 명령어를 실행할 수 없습니다.")
    print("브라우저 버전 확인 실패: 사용 가능한 명령어 없음")

# ---------------------------------------------------------------------------
# 유틸: 페이지 열기 (재시도 + 간단한 HTML 덤프)
# ---------------------------------------------------------------------------
def open_page_with_retry(driver, url, wait, retries=3):
    for attempt in range(1, retries + 1):
        try:
            print(f"[{attempt}/{retries}] 페이지 열기 시도: {url}")
            driver.get(url)

            # 페이지 상단 ‘서버 선택’ 드롭다운이 보일 때까지 대기
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".select_server .select_box")
                )
            )
            print("✅ 페이지 열림")
            return True
        except Exception as e:
            print(f"❌ 로딩 실패({attempt}): {e}")
            print("----- page source (truncated) -----")
            print(driver.page_source[:1024])
            print("-----------------------------------")
            time.sleep(2)

    print("🚫 페이지 열기에 최종 실패")
    return False

# ---------------------------------------------------------------------------
# 캐릭터 1명 크롤링
# ---------------------------------------------------------------------------
def crawl_character_info(driver, wait, char_name):
    print(f"  • {char_name} 크롤링 시작")
    # 모달 팝업(공지) 닫기
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "body > div.modal.alert_modal")
        if modal.is_displayed():
            modal.find_element(
                By.CSS_SELECTOR, "div.button_area > button"
            ).click()
            time.sleep(1)
    except Exception:
        pass  # 모달이 없으면 무시

    try:
        search_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search']"))
        )
        search_input.clear()
        search_input.send_keys(char_name)
        driver.find_element(
            By.CSS_SELECTOR, "button[data-searchtype='search']"
        ).click()
        time.sleep(2)
    except Exception as e:
        print(f"    검색 단계 에러: {e}")
        return None

    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")
            )
        )
        items = driver.find_elements(
            By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li"
        )
    except Exception:
        print("    검색 결과 로딩 실패")
        return None

    for item in items:
        try:
            if item.find_element(By.CSS_SELECTOR, "div:nth-child(3)").text.strip() == char_name:
                job = item.find_element(By.CSS_SELECTOR, "div:nth-child(4)").text.strip()
                power_text = item.find_element(By.CSS_SELECTOR, "div:nth-child(5)").text.strip()
                power_val = int(power_text.replace(",", ""))
                print(f"    완료: 직업={job}, 전투력={power_text}")
                return (char_name, job, power_text, power_val)
        except Exception:
            continue

    print("    대상 캐릭터 미발견")
    return None

# ---------------------------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------------------------
def main():
    print("=== 스크립트 시작 ===")
    check_chrome_version()  # 크롬 버전 출력

    # 1) 구글 시트 인증
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]), scope
        )
        worksheet = (
            gspread.authorize(creds)
            .open_by_url(
                "https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752"
            )
            .worksheet("전투력")
        )
        print("✅ 구글 시트 연결 성공")
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        return False

    # 2) 캐릭터명 수집
    try:
        names = list(dict.fromkeys(n.strip() for n in worksheet.col_values(2)[1:] if n.strip()))
        print(f"✅ 캐릭터 {len(names)}명 수집")
    except Exception as e:
        print(f"❌ 캐릭터명 수집 실패: {e}")
        return False

    # 3) 브라우저 실행 (headful: 차단 회피)
    try:
        opts = uc.ChromeOptions()
        opts.binary_location = "/usr/bin/chromium"  # 환경에 맞게 조정 필요
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--remote-debugging-port=9222")
        # opts.add_argument("--headless=new")  # 필요시 주석 해제

        driver = uc.Chrome(options=opts)
        wait = WebDriverWait(driver, 10)
        print("✅ Chrome 실행")
    except Exception as e:
        print(f"❌ Chrome 실행 실패: {e}")
        return False

    # 4) 랭킹 페이지 열기
    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_page_with_retry(driver, url, wait):
        driver.quit()
        return False

    # 5) 서버(알리사) 선택
    try:
        print("서버 선택 중...")
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".select_server .select_box")
        )).click()
        time.sleep(0.3)
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".select_server .select_option li[data-serverid='4']")
        )).click()
        print("✅ 알리사 서버 선택")
        time.sleep(1)
    except Exception as e:
        print(f"❌ 서버 선택 실패: {e}")
        driver.quit()
        return False

    # 6) 캐릭터별 크롤링
    results = []
    for name in names:
        info = crawl_character_info(driver, wait, name)
        if info:
            results.append(info)

    driver.quit()

    if not results:
        print("🚫 결과 없음")
        return False

    # 7) 결과 정렬 및 시트 업데이트
    results.sort(key=lambda x: x[3], reverse=True)
    rows = [["랭킹", "캐릭터명", "직업", "전투력"]] + [
        [i + 1, n, j, p] for i, (n, j, p, _) in enumerate(results)
    ]
    try:
        worksheet.update(f"A1:D{len(rows)}", rows)
        extra = len(worksheet.get_all_values()) - len(rows)
        if extra > 0:
            worksheet.update(f"A{len(rows)+1}:D{len(rows)+extra}", [[""] * 4] * extra)
        print("✅ 시트 업데이트 완료")
    except Exception as e:
        print(f"❌ 시트 업데이트 실패: {e}")
        return False

    print("=== 스크립트 종료 ===")
    return True

# ---------------------------------------------------------------------------
# Flask 엔드포인트
# ---------------------------------------------------------------------------
@app.route("/update-power")
def update_power():
    print("API 호출 도착 /update-power")
    if request.args.get("key") != "mabi123":
        return jsonify({"error": "Invalid key"}), 403

    return (
        jsonify({"status": "success"})
        if main()
        else (jsonify({"status": "failed"}), 500)
    )

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=False)
