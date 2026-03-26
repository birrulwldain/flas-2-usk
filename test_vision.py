import os
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables (API Key)
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("❌ Tolong masukkan GEMINI_API_KEY terlebih dahulu di file .env!")
    exit(1)

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

def create_dummy_captcha():
    """Membuat gambar dummy sederhana berisi tulisan Captcha untuk di test."""
    img = Image.new('RGB', (200, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 20), "A8 Z3K", fill=(0, 0, 0))
    img.save('dummy_captcha.png')
    print("✅ Gambar dummy 'dummy_captcha.png' berhasil dibuat.")

def test_gemini_vision():
    """Meguji model Gemini 2.5 Flash yang membaca Captcha."""
    try:
        print(f"Menggunakan API Key: {GEMINI_API_KEY[:8]}*****...")
        print("Sedang mengirim ke Gemini 2.5 Flash...")
        
        with open('dummy_captcha.png', "rb") as f:
            image_bytes = f.read()

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                "Tolong bacakan tulisan pada gambar ini. Hanya berikan kodenya."
            ]
        )
        print("\n✅ BERHASIL! Gemini merespons dengan:")
        print(f"Hasil Tebakan: {response.text.strip()}")
        
    except Exception as e:
        print("\n❌ GAGAL!")
        print(f"Pesan Error: {e}")
        if '429' in str(e):
             print("Penyebab Umum: Limit/Kuota Gratis dari Google Account ini sudah habis.")

if __name__ == '__main__':
    create_dummy_captcha()
    test_gemini_vision()
    
    # Hapus file dummy setelah test selesai
    if os.path.exists('dummy_captcha.png'):
        os.remove('dummy_captcha.png')
