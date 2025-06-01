import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def open_page_with_retry(driver, url, wait, retries=3):
    for attempt in range(retries):
        try:
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#mabinogim > div.ranking.container")))
            print("사이트 열림")
            return True
        except Exception as e:
            print(f"페이지 로딩 실패, 재시도 {attempt+1}/{retries} 중...")
            time.sleep(2)
    print("페이지 열기에 실패했습니다.")
    return False

def crawl_character_info(driver, wait, char_name):
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "body > div.modal.alert_modal")
        if modal.is_displayed():
            modal_close_btn = modal.find_element(By.CSS_SELECTOR, "div.button_area > button")
            print("모달 팝업 발견! 닫기 클릭합니다.")
            modal_close_btn.click()
            time.sleep(1.5)
    except Exception:
        pass

    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search']")))
    search_input.clear()
    search_input.send_keys(char_name)
    search_button = driver.find_element(By.CSS_SELECTOR, "button[data-searchtype='search']")
    search_button.click()
    time.sleep(3)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")))
    except:
        print(f"{char_name} 검색 결과 없음")
        return None, None, None

    items = driver.find_elements(By.CSS_SELECTOR, "section.ranking_list_wrap div.list_area ul > li")

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
        print(f"{char_name} 캐릭터를 찾을 수 없습니다.")
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

    return job, power, power_int

def main(driver, wait):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('mabiguildsheetbot-64542e93dafc.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752")
    worksheet = sheet.worksheet("전투력")

    char_names = worksheet.col_values(2)[1:]
    char_names = [name.strip() for name in char_names if name.strip()]

    seen = set()
    unique_char_names = []
    for name in char_names:
        if name not in seen:
            unique_char_names.append(name)
            seen.add(name)
    char_names = unique_char_names

    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_page_with_retry(driver, url, wait):
        return

    server_select_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_box")))
    server_select_box.click()
    time.sleep(0.5)
    alisa_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".select_server .select_option li[data-serverid='4']")))
    alisa_option.click()
    print("알리사 서버 선택 완료")
    time.sleep(2)

    results = []
    for char_name in char_names:
        print(f"{char_name} 정보 크롤링 시작...")
        job, power, power_int = crawl_character_info(driver, wait, char_name)
        if job is None or power is None:
            print(f"{char_name} 정보 없음, 건너뜀")
            continue
        results.append((char_name, job, power, power_int))

    results.sort(key=lambda x: x[3], reverse=True)

    data_to_update = [["랭킹", "캐릭터명", "직업", "전투력"]]
    for i, (name, job, power, _) in enumerate(results, start=1):
        data_to_update.append([i, name, job, power])

    worksheet.update('A1:D{}'.format(len(data_to_update)), data_to_update)

    all_rows = len(worksheet.get_all_values())
    rows_to_clear = all_rows - len(data_to_update)
    if rows_to_clear > 0:
        start_row = len(data_to_update) + 1
        end_row = all_rows
        clear_range = f"A{start_row}:D{end_row}"
        empty_data = [[""] * 4] * rows_to_clear
        worksheet.update(clear_range, empty_data)

    print("구글 시트 업데이트 및 잔여 데이터 삭제 완료!")
