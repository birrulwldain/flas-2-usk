import telebot, os, threading, time
from dotenv import load_dotenv
load_dotenv(".env")
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN"))
chatid = os.environ.get("BIRRUL_CHAT_ID")
print("1) Sending msg...")
bot.send_message(chatid, "Tes polling 10 detik.")
print("2) Starting timer...")
def tst():
    print("Timer fired!")
    bot.stop_polling()
timer = threading.Timer(10.0, tst)
timer.start()
print("3) Starting polling...")
bot.polling(none_stop=True)
print("4) Polling ended!")
