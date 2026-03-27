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
    status_msg = bot.send_message(chatid, "⏳ Menjalankan Absen Otomatis via GitHub Actions...")
    
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
        
        max_retries = 3
        sukses = False
        alasan_gagal = ""
        
        for attempt in range(max_retries):
            bot.edit_message_text(f"⏳ Percobaan {attempt+1}/{max_retries}: Menganalisis Captcha...", chat_id=chatid, message_id=status_msg.message_id)
            
            try:
                driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").clear()
                driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").send_keys(nim)
                driver.find_element(By.XPATH, "//input[@placeholder='Password']").clear()
                driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(passw)
            except: pass
            
            captcha_img = driver.find_element(By.XPATH, "//img[contains(@src, 'captcha_image')]")
            captcha_img.screenshot('captcha.png')
            
            auto_code = solve_captcha_gemini('captcha.png')
            
            if not auto_code:
                alasan_gagal = "Gemini Error API Limit (429)."
                break
                
            bot.edit_message_text(f"⏳ Percobaan {attempt+1}/{max_retries}: Gemini menebak '{auto_code}'. Sedang login...", chat_id=chatid, message_id=status_msg.message_id)
            
            driver.find_element(By.ID, "captcha_answer").clear()
            driver.find_element(By.ID, "captcha_answer").send_keys(auto_code)
            
            driver.find_element(By.XPATH, "//button[contains(., 'Login')]").click()
            time.sleep(3)
            
            if "login" not in driver.current_url.lower():
                bot.edit_message_text(f"✅ Login Berhasil (Percobaan {attempt+1})!", chat_id=chatid, message_id=status_msg.message_id)
                sukses = True
                break
            else:
                alasan_gagal = "Captcha ditebak salah."
                driver.refresh()
                time.sleep(2)
                
        if sukses:
            # Lanjut ke proses Absen Portal
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
            if os.path.exists('captcha.png'): os.remove('captcha.png')
        else:
            bot.edit_message_text(f"❌ Auto-Login Gagal ({alasan_gagal})", chat_id=chatid, message_id=status_msg.message_id)
            msg = bot.send_photo(chatid, photo=open('captcha.png', 'rb'), 
                                 caption="Anda punya waktu 3 MENIT untuk membalas pesan ini dengan kode Captcha secara manual:")
            if os.path.exists('captcha.png'): os.remove('captcha.png')
            
            def process_captcha_manual(message):
                try:
                    manual_code = message.text
                    
                    try:
                        driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").clear()
                        driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").send_keys(nim)
                        driver.find_element(By.XPATH, "//input[@placeholder='Password']").clear()
                        driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(passw)
                    except: pass
                    
                    driver.find_element(By.ID, "captcha_answer").clear()
                    driver.find_element(By.ID, "captcha_answer").send_keys(manual_code)
                    driver.save_screenshot('before_login.png')
                    bot.send_photo(chatid, photo=open('before_login.png', 'rb'), caption="Screenshot sebelum klik Login (Manual)")
                    if os.path.exists('before_login.png'): os.remove('before_login.png')
                    
                    driver.find_element(By.XPATH, "//button[contains(., 'Login')]").click()
                    time.sleep(3)
                    
                    if "login" in driver.current_url.lower():
                         bot.send_message(chatid, "❌ Validasi Manual Gagal: Captcha manual salah. Browser akan dimatikan.")
                    else:
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
                            bot.send_photo(chatid, photo=open('creen.png', 'rb'), caption="Berhasil Absen Otomatis (Manual Input)!")
                        except NoSuchElementException:
                            bot.send_message(chatid, "Belum masuk waktu absen atau sudah absen.")
                            driver.get_screenshot_as_file('creen.png')
                            bot.send_photo(chatid, photo=open('creen.png', 'rb'))
                finally:
                    bot.stop_polling()

            bot.register_next_step_handler(msg, process_captcha_manual)
            
            import threading
            def timeout_polling():
                try:
                    bot.send_message(chatid, "⏳ Waktu tunggu manual (3 menit) habis. GitHub Actions dihentikan.")
                except: pass
                bot.stop_polling()
                
            timer = threading.Timer(180.0, timeout_polling)
            timer.start()
            
            # Abaikan tumpukan pesan lama di Telegram sebelum memulai polling!
            bot.polling(none_stop=True, skip_pending=True)
            timer.cancel()
                             
    except Exception as e:
        bot.send_message(chatid, f"Gagal memulai login: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    main_absen()
