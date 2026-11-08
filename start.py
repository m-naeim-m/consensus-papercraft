import sys
import os
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("================================================================")
    print("      Consensus PaperCraft Studio - استودیو نگارش مقاله علمی      ")
    print("================================================================")
    print("در حال راه‌اندازی سرور محلی و توزیع بار API کانسنسوس...")
    print("آدرس سامانه: http://127.0.0.1:8000")
    print("برای توقف، کلیدهای Ctrl+C را فشار دهید.")
    print("----------------------------------------------------------------")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
