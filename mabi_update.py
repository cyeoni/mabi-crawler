import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def setup_google_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logging.info("Google 인증 완료")
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752")
        worksheet = sheet.worksheet("전투력")
        logging.info("스프레드시트 열기 완료")
        return worksheet
    except Exception as e:
        logging.error(f"Google 인증 또는 스프레드시트 접근 실패: {e}")
        return None

def get_character_names(worksheet):
    try:
        names = worksheet.col_values(2)[1:]
        names = [n.strip() for n in names if n.strip()]
        unique = list(dict.fromkeys(names))  # 중복 제거
        logging.info(f"{len(unique)}개 캐릭터명 수집 완료")
        return unique
    except Exception as e:
        logging.error(f"캐릭터명 수집 실패: {e}")
        return []

def init_webdriver():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10)
        logging.info("웹 드라이버 실행 완료")
        return driver, wait
    except Exception as e:
        logging.error(f"웹 드라이버 초기화 실패: {e}")
        return None, None

def open_ranking_page(driver, wait, url, retries=3):
    for i in range(retries):
        try:
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#mabinogim > div.ranking.container")))
            logging.info("랭킹 페이지 열기 성공")
            return True
        except Exception as e:
            logging.warning(f"랭킹 페이지 열기 실패 ({i+1}/{retries}): {e}")
            time.sleep(2)
    return False

def select_server(driver, wait, server_id="4"):
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_box"))).click()
        time.sleep(0.3)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f".select_server .select_option li[data-serverid='{server_id}']"))).click()
        time.sleep(1)
        logging.info("서버 선택 완료")
        return True
    except Exception as e:
        logging.error(f"서버 선택 실패: {e}")
        return False

def crawl_character(driver, wait, name):
    try:
        # 모달 처리
        try:
            modal = driver.find_element(By.CSS_SELECTOR, "body > div.modal.alert_modal")
            if modal.is_displayed():
                modal.find_element(By.CSS_SELECTOR, "div.button_area > button").click()
                time.sleep(1)
        except:
            pass

        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search']")))
        search_input.clear()
        search_input.send_keys(name)

        driver.find_element(By.CSS_SELECTOR, "button[data-searchtype='search']").click()
        time.sleep(2)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")))
        items = driver.find_elements(By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")

        for item in items:
            try:
                char_name = item.find_element(By.CSS_SELECTOR, "div:nth-child(3)").text.strip()
                if char_name == name:
                    job = item.find_element(By.CSS_SELECTOR, "div:nth-child(4)").text.strip()
                    power_text = item.find_element(By.CSS_SELECTOR, "div:nth-child(5)").text.strip()
                    power_value = int(power_text.replace(',', ''))
                    return name, job, power_text, power_value
            except:
                continue
        logging.info(f"{name}: 캐릭터 찾을 수 없음")
        return None
    except Exception as e:
        logging.error(f"{name} 크롤링 중 오류: {e}")
        return None

def update_sheet(worksheet, results):
    try:
        results.sort(key=lambda x: x[3], reverse=True)
        rows = [["랭킹", "캐릭터명", "직업", "전투력"]] + [
            [i+1, name, job, power] for i, (name, job, power, _) in enumerate(results)
        ]
        worksheet.update(f"A1:D{len(rows)}", rows)

        all_data = worksheet.get_all_values()
        if len(all_data) > len(rows):
            clear_range = f"A{len(rows)+1}:D{len(all_data)}"
            worksheet.update(clear_range, [[""] * 4] * (len(all_data) - len(rows)))
            logging.info(f"불필요한 {len(all_data) - len(rows)}행 삭제 완료")

        logging.info("구글 시트 업데이트 완료")
    except Exception as e:
        logging.error(f"시트 업데이트 실패: {e}")

def main():
    logging.info("=== 스크립트 시작 ===")
    worksheet = setup_google_sheet()
    if not worksheet:
        return False

    char_names = get_character_names(worksheet)
    if not char_names:
        return False

    driver, wait = init_webdriver()
    if not driver:
        return False

    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_ranking_page(driver, wait, url):
        driver.quit()
        return False

    if not select_server(driver, wait):
        driver.quit()
        return False

    results = []
    for name in char_names:
        result = crawl_character(driver, wait, name)
        if result:
            results.append(result)
        else:
            logging.warning(f"{name} 정보 없음, 건너뜀")

    driver.quit()

    if results:
        update_sheet(worksheet, results)

    logging.info("=== 스크립트 종료 ===")
    return True

@app.route('/update-power')
def update_power():
    logging.info("요청 도착 - /update-power")
    if request.args.get('key') != "mabi123":
        logging.warning("잘못된 API 키 요청")
        return jsonify({"error": "Invalid key"}), 403

    if main():
        return jsonify({"status": "success"})
    return jsonify({"status": "failed"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"서버 시작 - 포트 {port}")
    app.run(host="0.0.0.0", port=port)
