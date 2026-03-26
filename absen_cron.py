from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import time
import os
import telebot
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from google import genai
from google.genai import types

load_dotenv()

nim = os.getenv('BIRRUL_NIM')
passw = os.getenv('BIRRUL_PASS')
chatid = os.getenv('BIRRUL_CHAT_ID')
api = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(api)

def solve_captcha_gemini(image_path):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                "Tolong bacakan kode captcha pada gambar ini. Hanya berikan kodenya saja (case sensitive) tanpa teks tambahan apapun."
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

def main_absen():
    bot.send_message(chatid, "Menjalankan Absen Otomatis via GitHub Actions...")
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get("https://simkuliah.usk.ac.id/index.php/login")
        
        driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").send_keys(nim)
        driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(passw)
        
        captcha_img = driver.find_element(By.XPATH, "//img[contains(@src, 'captcha_image')]")
        captcha_img.screenshot('captcha.png')
        
        auto_code = solve_captcha_gemini('captcha.png')
        
        if auto_code:
            bot.send_photo(chatid, photo=open('captcha.png', 'rb'), 
                           caption=f"Gemini menebak kode: {auto_code}. Mencoba login otomatis...")
            
            # Submit
            driver.find_element(By.ID, "captcha_answer").send_keys(auto_code)
            
            driver.save_screenshot('before_login.png')
            bot.send_photo(chatid, photo=open('before_login.png', 'rb'), caption="Screenshot sebelum klik Login")
            
            driver.find_element(By.XPATH, "//button[contains(., 'Login')]").click()
            time.sleep(2)
            
            if "login" in driver.current_url.lower():
                 bot.send_message(chatid, "Login gagal. Captcha mungkin salah. Bot Github Actions berhenti di sini.")
                 return
                 
            # Proses Absen di dalam Portal
            try:
                absen1_button = driver.find_element(By.XPATH, '//*[@id="konfirmasi-kehadiran"]')
                absen1_button.click()
                time.sleep(3)
                absen2_button = driver.find_element(By.XPATH, '/html/body/div[4]/div[7]/div/button')
                absen2_button.click()
                time.sleep(3)
                driver.refresh()
                driver.get_screenshot_as_file('creen.png')
                bot.send_photo(chatid, photo=open('creen.png', 'rb'), caption="Berhasil Absen Otomatis!")
            except NoSuchElementException:
                bot.send_message(chatid, "Belum masuk waktu absen atau sudah absen.")
                driver.get_screenshot_as_file('creen.png')
                bot.send_photo(chatid, photo=open('creen.png', 'rb'))
                
        else:
            bot.send_photo(chatid, photo=open('captcha.png', 'rb'), 
                             caption="Gemini gagal absen otomatis. Karena script berjalan di GitHub Actions, proses dihentikan.")
                             
    except Exception as e:
        bot.send_message(chatid, f"Gagal memulai login: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    main_absen()
