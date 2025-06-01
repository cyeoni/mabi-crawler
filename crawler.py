def main(driver, wait):
    print("크롤러 시작")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('mabiguildsheetbot-64542e93dafc.json', scope)
    client = gspread.authorize(creds)
    print("구글 시트 인증 완료")

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/19Ti_Sq75WpdE3vKGtxupCCCnBmzNXmRv_fafkD0X_Bo/edit#gid=1776704752")
    worksheet = sheet.worksheet("전투력")

    char_names = worksheet.col_values(2)[1:]
    char_names = list(dict.fromkeys(name.strip() for name in char_names if name.strip()))
    print(f"캐릭터 이름 총 {len(char_names)}개 읽음")

    url = "https://mabinogimobile.nexon.com/Ranking/List?t=1"
    if not open_page_with_retry(driver, url, wait):
        print("페이지 열기 실패로 크롤러 종료")
        return

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

    results.sort(key=lambda x: x[3], reverse=True)
    data_to_update = [["랭킹", "캐릭터명", "직업", "전투력"]]
    for i, (name, job, power, _) in enumerate(results, start=1):
        data_to_update.append([i, name, job, power])

    print("구글 시트 업데이트 시작")
    worksheet.update(f'A1:D{len(data_to_update)}', data_to_update)

    all_rows = len(worksheet.get_all_values())
    leftover = all_rows - len(data_to_update)
    if leftover > 0:
        clear_range = f"A{len(data_to_update)+1}:D{all_rows}"
        worksheet.update(clear_range, [[""] * 4] * leftover)

    print("✅ 구글 시트 업데이트 완료")
    print("크롤러 종료")
