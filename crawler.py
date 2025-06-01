import os
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc


def create_driver():
    options = uc.ChromeOptions()
    # 필요시 헤드리스 모드 활성화
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--single-process")
    options.add_argument("window-size=1920,1080")

    options.binary_location = os.getenv("CHROME_PATH", "/usr/bin/google-chrome")

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    options.add_argument(f"user-agent={user_agent}")

    # driver_executable_path 제거 (undetected_chromedriver가 알아서 처리)
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    return driver, wait


def open_page_with_retry(driver, url, wait, retries=1):
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            wait.until(EC.visibility_of_element_located((
                By.CSS_SELECTOR,
                "#mabinogimobile > div.ranking.container, #mabinogimobile > div.ranking"
            )))
            print("✅ 페이지 열림")
            return True
        except Exception as e:
            print(f"❌ 페이지 로딩 실패, 재시도 {attempt}/{retries}: {e}")

            html = driver.page_source.lower()
            print("🔎 현재 페이지 일부 내용 (앞 500자):\n", html[:500])

            bot_keywords = ["captcha", "verify", "bot", "blocked", "access denied", "authentication required"]
            if any(keyword in html for keyword in bot_keywords):
                print("🚨 봇 탐지 또는 캡챠 페이지로 추정됩니다.")
                time.sleep(5)
                driver.refresh()
                continue

            time.sleep(2)
    print("❌ 페이지 열기에 최종 실패")
    return False


def crawl_character_info(driver, wait, char_name):
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "body > div.modal.alert_modal")
        if modal.is_displayed():
            close_btn = modal.find_element(By.CSS_SELECTOR, "div.button_area > button")
            print("모달 팝업 발견 → 닫기 클릭")
            close_btn.click()
            time.sleep(1.5)
    except Exception:
        # 모달 없으면 무시
        pass

    # 검색창에 이름 입력 후 검색
    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search']")))
    search_input.clear()
    search_input.send_keys(char_name)

    search_button = driver.find_element(By.CSS_SELECTOR, "button[data-searchtype='search']")
    search_button.click()
    time.sleep(3)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")))
    except Exception:
        print(f"{char_name} 검색 결과 없음")
        return None, None, None

    items = driver.find_elements(By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")
    for item in items:
        try:
            name_elem = item.find_element(By.CSS_SELECTOR, "div:nth-child(3)")
            if name_elem.text.strip() == char_name:
                job = item.find_element(By.CSS_SELECTOR, "div:nth-child(4)").text.strip()
                power = item.find_element(By.CSS_SELECTOR, "div:nth-child(5)").text.strip()
                power_int = int(power.replace(',', ''))
                return job, power, power_int
        except Exception:
            continue

    print(f"{char_name} 캐릭터를 찾을 수 없습니다.")
    return None, None, None


def main(driver, wait):
    print("크롤러 시작")

    # 구글 API 범위 설정
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # 환경변수에서 인증 JSON 문자열 불러오기
    creds_json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json_str:
        raise RuntimeError("환경 변수 GOOGLE_APPLICATION_CREDENTIALS_JSON 가 설정되어 있지 않습니다.")

    creds_dict = json.loads(creds_json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    print("구글 시트 인증 완료")

    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752"
    )
    worksheet = sheet.worksheet("전투력")

    # 2열(캐릭터명) 전체 가져오기 (헤더 제외)
    char_names = worksheet.col_values(2)[1:]
    # 중복 제거 및 공백 제거
    char_names = list(dict.fromkeys(name.strip() for name in char_names if name.strip()))
    print(f"캐릭터 이름 총 {len(char_names)}개 읽음")

    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_page_with_retry(driver, url, wait):
        print("페이지 열기 실패로 크롤러 종료")
        return

    # 서버 선택 (알리사 서버 - 서버ID: 4)
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_box"))).click()
        time.sleep(0.5)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_option li[data-serverid='4']"))).click()
        print("✅ 알리사 서버 선택 완료")
        time.sleep(2)
    except Exception as e:
        print("❌ 서버 선택 실패:", e)
        return

    results = []
    for char_name in char_names:
        print(f"🔍 {char_name} 정보 조회 중...")
        job, power, power_int = crawl_character_info(driver, wait, char_name)
        if job is None or power is None:
            print(f"⚠️ {char_name} 정보 없음 → 건너뜀")
            continue
        print(f"✅ {char_name} 조회 완료: 직업={job}, 전투력={power}")
        results.append((char_name, job, power, power_int))

    # 전투력 순 내림차순 정렬
    results.sort(key=lambda x: x[3], reverse=True)

    data_to_update = [["랭킹", "캐릭터명", "직업", "전투력"]]
    for i, (name, job, power, _) in enumerate(results, start=1):
        data_to_update.append([i, name, job, power])

    print("구글 시트 업데이트 시작")
    worksheet.update(f'A1:D{len(data_to_update)}', data_to_update)

    # 기존 데이터 중 남는 행 초기화
    all_rows = len(worksheet.get_all_values())
    leftover = all_rows - len(data_to_update)
    if leftover > 0:
        clear_range = f"A{len(data_to_update)+1}:D{all_rows}"
        worksheet.update(clear_range, [[""] * 4] * leftover)

    print("✅ 구글 시트 업데이트 완료")
    print("크롤러 종료")


if __name__ == "__main__":
    driver, wait = create_driver()
    try:
        main(driver, wait)
    finally:
        driver.quit()
