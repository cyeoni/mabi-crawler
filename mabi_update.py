import os
import json
import time
import gspread
import undetected_chromedriver as uc
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, request, jsonify

app = Flask(__name__)

def open_page_with_retry(driver, url, wait, retries=3):
    for attempt in range(retries):
        try:
            print(f"페이지 열기 시도 {attempt+1}회: {url}")
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#mabinogim > div.ranking.container")))
            print("사이트 열림")
            return True
        except Exception as e:
            print(f"페이지 로딩 실패, 재시도 {attempt+1}/{retries} 중... 에러: {e}")
            time.sleep(2)
    print("페이지 열기에 실패했습니다.")
    return False

def crawl_character_info(driver, wait, char_name):
    print(f"  - {char_name} 크롤링 시작")
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "body > div.modal.alert_modal")
        if modal.is_displayed():
            modal_close_btn = modal.find_element(By.CSS_SELECTOR, "div.button_area > button")
            print("  모달 팝업 발견! 닫기 클릭합니다.")
            modal_close_btn.click()
            time.sleep(1.5)
    except:
        pass  # 모달이 없을 수도 있음

    try:
        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search']")))
        search_input.clear()
        search_input.send_keys(char_name)
    except Exception as e:
        print(f"  검색 입력창 처리 중 에러: {e}")
        return None, None, None

    try:
        search_button = driver.find_element(By.CSS_SELECTOR, "button[data-searchtype='search']")
        search_button.click()
        time.sleep(3)
    except Exception as e:
        print(f"  검색 버튼 클릭 중 에러: {e}")
        return None, None, None

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")))
        items = driver.find_elements(By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")
    except:
        print(f"  {char_name} 검색 결과 없음 또는 로딩 실패")
        return None, None, None

    target_char = None
    for item in items:
        try:
            name_elem = item.find_element(By.CSS_SELECTOR, "div:nth-child(3)")
            if name_elem.text.strip() == char_name:
                target_char = item
                break
        except:
            continue

    if not target_char:
        print(f"  {char_name} 캐릭터를 찾을 수 없습니다.")
        return None, None, None

    try:
        job = target_char.find_element(By.CSS_SELECTOR, "div:nth-child(4)").text.strip()
    except:
        job = "(정보 없음)"

    try:
        power = target_char.find_element(By.CSS_SELECTOR, "div:nth-child(5)").text.strip()
        power_int = int(power.replace(',', ''))
    except:
        power = "0"
        power_int = 0

    print(f"  {char_name} 크롤링 완료: 직업={job}, 전투력={power}")
    return job, power, power_int

def main():
    print("=== 스크립트 시작 ===")
    # Google 인증
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        print("Google 인증 완료")
    except Exception as e:
        print(f"Google 인증 중 에러: {e}")
        return False

    try:
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752")
        worksheet = sheet.worksheet("전투력")
        print("구글 시트 열기 완료")
    except Exception as e:
        print(f"구글 시트 열기 중 에러: {e}")
        return False

    try:
        char_names = worksheet.col_values(2)[1:]
        char_names = list(dict.fromkeys([name.strip() for name in char_names if name.strip()]))
        print(f"캐릭터명 수집 완료: 총 {len(char_names)}개 캐릭터")
    except Exception as e:
        print(f"캐릭터명 수집 중 에러: {e}")
        return False

    try:
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")  # 우회 가능한 headless
        options.add_argument("--window-size=1920,1080")
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 10)
        print("브라우저 실행 완료")
    except Exception as e:
        print(f"브라우저 실행 중 에러: {e}")
        return False

    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_page_with_retry(driver, url, wait):
        driver.quit()
        return False

    try:
        print("서버 선택 중...")
        server_select_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_box")))
        server_select_box.click()
        time.sleep(0.5)
        alisa_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_option li[data-serverid='4']")))
        alisa_option.click()
        print("알리사 서버 선택 완료")
        time.sleep(2)
    except Exception as e:
        print(f"서버 선택 중 에러: {e}")
        driver.quit()
        return False

    results = []
    for char_name in char_names:
        job, power, power_int = crawl_character_info(driver, wait, char_name)
        if job is None or power is None:
            continue
        results.append((char_name, job, power, power_int))

    driver.quit()

    try:
        results.sort(key=lambda x: x[3], reverse=True)
    except:
        pass

    try:
        data_to_update = [["랭킹", "캐릭터명", "직업", "전투력"]]
        for i, (name, job, power, _) in enumerate(results, start=1):
            data_to_update.append([i, name, job, power])

        worksheet.update(f"A1:D{len(data_to_update)}", data_to_update)

        all_rows = len(worksheet.get_all_values())
        if all_rows > len(data_to_update):
            clear_range = f"A{len(data_to_update)+1}:D{all_rows}"
            worksheet.update(clear_range, [[""]*4] * (all_rows - len(data_to_update)))

        print("시트 업데이트 완료")
    except Exception as e:
        print(f"시트 업데이트 중 에러: {e}")

    print("=== 스크립트 종료 ===")
    return True

@app.route('/update-power')
def update_power():
    print("API 요청 도착 - /update-power")
    key = request.args.get('key')
    if key != "mabi123":
        return jsonify({"error": "Invalid key"}), 403

    success = main()
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "failed"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
