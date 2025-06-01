import functools
import traceback
import shutil
import subprocess
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
import crawler  # crawler.py 임포트

print = functools.partial(print, flush=True)

def find_chrome_binary():
    candidates = ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"]
    for cmd in candidates:
        path = shutil.which(cmd)
        if path:
            print(f"발견된 크롬 실행 파일: {cmd} -> {path}")
            return path
        else:
            print(f"{cmd} 명령어를 실행할 수 없습니다.")
    print("사용 가능한 크롬 실행 파일을 찾지 못했습니다.")
    return None

def check_chrome_version():
    candidates = ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"]
    for cmd in candidates:
        try:
            version = subprocess.check_output([cmd, "--version"]).decode().strip()
            print(f"브라우저 버전 확인: {version} ({cmd})")
            return
        except Exception:
            print(f"{cmd} 명령어를 실행할 수 없습니다.")
    print("브라우저 버전 확인 실패: 사용 가능한 명령어 없음")

def launch_chrome():
    binary_path = find_chrome_binary()
    if not binary_path:
        print("크롬 실행 파일을 찾지 못해 종료합니다.")
        return None, None

    opts = uc.ChromeOptions()
    opts.binary_location = binary_path
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--remote-debugging-port=9222")
    # opts.add_argument("--headless=new")

    try:
        driver = uc.Chrome(options=opts)
        wait = WebDriverWait(driver, 10)
        print("✅ Chrome 실행 성공")
        return driver, wait
    except Exception:
        print("❌ Chrome 실행 실패:")
        traceback.print_exc()
        return None, None

def main():
    check_chrome_version()
    driver, wait = launch_chrome()
    if not driver:
        print("chrome launch failed")
        return

    try:
        crawler.main(driver, wait)
    except Exception as e:
        print("crawler error:", e)
        traceback.print_exc()
    finally:
        driver.quit()
