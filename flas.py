from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime

import time
import json
import requests
import schedule
import os
import telebot
from threading import Thread
from datetime import date
from dotenv import load_dotenv

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# SEJAK SEPTEMBER HAHAHAHA
# Menggunakan os.getenv untuk kemudahan konfigurasi lokal & keamanan
nim = os.getenv('BIRRUL_NIM')
passw = os.getenv('BIRRUL_PASS')
chatid = os.getenv('BIRRUL_CHAT_ID')
api = os.getenv('TELEGRAM_BOT_TOKEN')
# Konfigurasi Headless mode
HEADLESS = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'

# Konfigurasi Gemini API (gunakan API Key dari .env)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=GEMINI_API_KEY)

def solve_captcha_gemini(image_path):
    """Gunakan Gemini 2.5 Flash untuk membaca Captcha (Terbukti Berfungsi)"""
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

bot = telebot.TeleBot(api)
#//*[@id="mCSB_1_container"]/ul/li[4]/a/span[2]
def start_login(usnim, passwk, chatk, nama, mode='absen'):
    """Tahap 1: Inisialisasi driver dan kirim Captcha ke user"""
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        chrome_options.add_argument("--incognito")
        if HEADLESS:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get("https://simkuliah.usk.ac.id/index.php/login")
        
        # Isi NIM dan Password
        driver.find_element(By.XPATH, "//input[@placeholder='NIP/NPM']").send_keys(usnim)
        driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(passwk)
        
        # Ambil screenshot Captcha
        captcha_img = driver.find_element(By.XPATH, "//img[contains(@src, 'captcha_image')]")
        captcha_img.screenshot('captcha.png')
        
        # Coba selesaikan dengan Gemini
        bot.send_message(chatk, f"Mencoba menyelesaikan Captcha otomatis untuk {nama}...")
        auto_code = solve_captcha_gemini('captcha.png')
        
        if auto_code:
            bot.send_photo(chatk, photo=open('captcha.png', 'rb'), 
                           caption=f"Gemini menebak kode: {auto_code}. Mencoba login otomatis...")
            # Panggil fungsi tahap 2 secara langsung (mocking message object)
            class MockMessage:
                def __init__(self, text):
                    self.text = text
            process_captcha_step(MockMessage(auto_code), driver, usnim, passwk, chatk, nama, mode)
        else:
            msg = bot.send_photo(chatk, photo=open('captcha.png', 'rb'), 
                                 caption=f"Gemini gagal absen otomatis untuk {nama}.\nMasukkan kode Captcha secara manual:")
            bot.register_next_step_handler(msg, process_captcha_step, driver, usnim, passwk, chatk, nama, mode)
        
        if os.path.exists('captcha.png'):
            os.remove('captcha.png')
        
    except Exception as e:
        bot.send_message(chatk, f"Gagal memulai login untuk {nama}: {e}")
        if 'driver' in locals():
            driver.quit()

def process_captcha_step(message, driver, usnim, passwk, chatk, nama, mode):
    """Tahap 2: Masukkan captcha dan selesaikan login"""
    try:
        captcha_code = message.text
        driver.find_element(By.ID, "captcha_answer").send_keys(captcha_code)
        
        # Ambil screenshot untuk bukti
        driver.save_screenshot('before_login.png')
        bot.send_photo(chatk, photo=open('before_login.png', 'rb'), caption="Screenshot sebelum klik Login")
        if os.path.exists('before_login.png'):
            os.remove('before_login.png')
            
        driver.find_element(By.XPATH, "//button[contains(., 'Login')]").click()
        
        time.sleep(2)
        # Cek apakah login berhasil (misal cek apakah masih di halaman login)
        if "login" in driver.current_url.lower():
             bot.send_message(chatk, f"Login gagal untuk {nama}. Mungkin captcha salah. Silakan coba lagi dengan command.")
             driver.quit()
             return

        if mode == 'cekkuliah':
            finish_cekkuliah(driver, chatk, nama)
        else:
            finish_absen(driver, usnim, passwk, chatk, nama)
            
    except Exception as e:
        bot.send_message(chatk, f"Error saat memproses captcha {nama}: {e}")
        driver.quit()

def finish_cekkuliah(driver, chatk, nama):
    try:
        # Klik menu jadwal atau langsung ke dashboard
        # Berdasarkan kode lama: mCSB_1_container > ul > li[4] > a
        but = driver.find_element(By.XPATH, '//*[@id="mCSB_1_container"]/ul/li[4]/a')
        but.click()
        time.sleep(4)
        driver.get_screenshot_as_file('creen.png')
        bot.send_photo(chatk, photo=open('creen.png', 'rb'), caption=f"Jadwal Kuliah {nama}")
        os.remove('creen.png')
    except Exception as e:
        bot.send_message(chatk, f"Gagal mengambil jadwal {nama}: {e}")
    finally:
        driver.quit()

def finish_absen(driver, usnim, passwk, chatk, nama):
    try:
        # Logika absen dari kode lama
        # Halaman dashboard biasanya sudah menampilkan tombol konfirmasi kehadiran jika waktunya tiba
        try:
            # Cari tombol konfirmasi kehadiran
            absen1_button = driver.find_element(By.XPATH, '//*[@id="konfirmasi-kehadiran"]')
            absen1_button.click()
            time.sleep(3)
            # Klik tombol OK/Konfirmasi di popup
            absen2_button = driver.find_element(By.XPATH, '/html/body/div[4]/div[7]/div/button')
            absen2_button.click()
            time.sleep(3)
            
            driver.refresh()
            # Ambil screenshot hasil
            driver.get_screenshot_as_file('creen.png')
            bot.send_photo(chatk, photo=open('creen.png', 'rb'), caption=f"Berhasil Absen untuk {nama}")
            os.remove('creen.png')
        except NoSuchElementException:
            # Jika tidak ada tombol konfirmasi, mungkin belum waktunya
            bot.send_message(chatk, f"Belum masuk waktu absen atau sudah absen untuk {nama}.")
            driver.get_screenshot_as_file('creen.png')
            bot.send_photo(chatk, photo=open('creen.png', 'rb'))
            os.remove('creen.png')
    except Exception as e:
        bot.send_message(chatk, f"Terjadi kesalahan saat proses absen {nama}: {e}")
    finally:
        driver.quit()

# Alias fungsi lama ke alur baru
def cekkuliah(usnim, passwk, chatk, nama='user'):
    start_login(usnim, passwk, chatk, nama, mode='cekkuliah')

def absen1(usnim, passwk, chatk, nama='user'):
    start_login(usnim, passwk, chatk, nama, mode='absen')

def cekkuliahbirul():
    cekkuliah(nim,passw, chatid)

def absenbirul():
    try:
        bot.send_message(chatid, "memulai absen")
        absen1(nim, passw, chatid, 'birul')
        bot.send_message(chatid, 'absen selesai')
    except Exception as e:
        print(f"Gagal kirim pesan ke {chatid}: {e}")

def cek():
    bot.send_message(chatid, 'cek bot')


def ascek():
    while True:
        schedule.run_pending()
        time.sleep(1)







@bot.message_handler(commands=['absen_birul'])
def cmd_absen_birul(message):
    bot.reply_to(message, "Memulai absen untuk Birul...")
    absenbirul()

@bot.message_handler(commands=['absen'])
def cmd_absen_all(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Silakan pilih akun untuk absen:\n/absen_birul")

@bot.message_handler(commands=['cekkuliah'])
def cmd_cekkuliah(message):
    bot.reply_to(message, "Mengecek jadwal kuliah...")
    cekkuliahbirul()
    bot.send_message(message.chat.id, "Pengecekan jadwal selesai.")

@bot.message_handler(content_types=['text',
                     'audio', 'video', 'picture', 'sticker'])
def senso(message):
    chat_id = message.chat.id
    print(f"Pesan diterima dari Chat ID: {chat_id}")
    bot.send_message(chat_id, "Gunakan command /absen atau /cekkuliah untuk berinteraksi dengan bot.")


if __name__ == '__main__':
    try:
        bot.send_message(chatid, 'bot jalan')
    except Exception as e:
        print(f"Peringatan: Gagal mengirim pesan pembuka ke {chatid}. Error: {e}")
        print("Pastikan Chat ID sudah benar dan Anda sudah menekan /start pada bot.")

    # Rabu
    schedule.every().wednesday.at("14:02").do(absenbirul)
    schedule.every().wednesday.at("16:37").do(absenbirul)
    
    # Kamis
    schedule.every().thursday.at("14:02").do(absenbirul)

    # Jumat
    schedule.every().friday.at("08:02").do(absenbirul)
    schedule.every().friday.at("09:52").do(absenbirul)
    schedule.every().friday.at("16:32").do(absenbirul)

    # Sabtu
    schedule.every().saturday.at("08:02").do(absenbirul)
    schedule.every().saturday.at("10:47").do(absenbirul)
    schedule.every().saturday.at("16:37").do(absenbirul)
    Thread(target=ascek).start()
    bot.polling()
# CHROMEDRIVER_PATH = /app/.chromedriver/bin/chromedriver
# https://github.com/heroku/heroku-buildpack-google-chrome
# https://github.com/heroku/heroku-buildpack-chromedriver
# TZ = Asia/Jakarta
