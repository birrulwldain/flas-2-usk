# Gunakan pondasi Linux + Python 3.10 versi Slim (Ringan)
FROM python:3.10-slim

# Matikan mode dialog peringatan saat instalasi aplikasi Linux
ENV DEBIAN_FRONTEND=noninteractive
# Sesuaikan zona waktu dengan WIB (Penting untuk jadwal Cron!)
ENV TZ=Asia/Jakarta

# Update server Linux dan install aplikasi pengunduh dasar
RUN apt-get update && apt-get install -y wget gnupg unzip curl \
    # Tambahkan kunci verifikasi resmi Google
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    # Daftarkan server gudang paket Google Chrome
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    # Install Google Chrome Versi Stabil (Stable) terbaru
    && apt-get update && apt-get install -y google-chrome-stable \
    # Bersihkan file sampah instalasi agar Docker irit penyimpanan
    && rm -rf /var/lib/apt/lists/*

# Atur folder operasi kontainer ke /app
WORKDIR /app

# Pindahkan daftar perpustakaan (library python)
COPY requirements.txt .

# Install Selenium, Telebot, Gemini, Schedule dkk di lingkungan Docker
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua sisa dokumen proyek (termasuk flas.py, absen_cron.py)
COPY . .

# Beri titah agar kontainer ini menjalankan bot Python secara permanen 24/7!
# -u : Memaksa Log Python langsung dikirim ke Dashboard Render segera (Unbuffered).
CMD ["python", "-u", "flas.py"]
