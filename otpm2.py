import json
import re
import sqlite3
import threading
import time
import random
import tkinter as tk
from tkinter import messagebox, simpledialog
import winsound  # Windows only, replace with other notification system for Linux/Mac
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium_stealth import stealth
from mitmproxy import http, ctx
from mitmproxy.tools.main import mitmdump

# CONFIGURATIONS
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
OTP_STORAGE_FILE = "captured_otps.db"
OTP_PATTERN = r"\b\d{6}\b"  # Adjust this pattern based on OTP format
ALLOWED_SITES_FILE = "allowed_sites.txt"
PROXY_LIST_FILE = "proxies.txt"

# User-Agent list for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]

# Setup database
def setup_database():
    conn = sqlite3.connect(OTP_STORAGE_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS otps (id INTEGER PRIMARY KEY, otp TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

# Store OTP in database
def store_otp(otp):
    conn = sqlite3.connect(OTP_STORAGE_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO otps (otp) VALUES (?)", (otp,))
    conn.commit()
    conn.close()

# GUI Class for OTP Display
class OTPGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Captured OTP")
        self.master.geometry("350x250")
        self.otp_label = tk.Label(master, text="Waiting for OTP...", font=("Arial", 12))
        self.otp_label.pack(pady=20)

        self.start_button = tk.Button(master, text="Start Interception", command=self.start_capturing)
        self.start_button.pack(pady=5)
        self.stop_button = tk.Button(master, text="Stop Interception", command=self.stop_capturing)
        self.stop_button.pack(pady=5)

        self.capturing = False

    def start_capturing(self):
        self.capturing = True
        self.otp_label.config(text="Capturing OTP...")
        messagebox.showinfo("Started", "OTP interception started.")

    def stop_capturing(self):
        self.capturing = False
        self.otp_label.config(text="Stopped.")
        messagebox.showinfo("Stopped", "OTP interception stopped.")

    def update_otp(self, otp):
        store_otp(otp)
        self.otp_label.config(text=f"Captured OTP: {otp}")
        winsound.Beep(1000, 500)  # Notification sound
        messagebox.showinfo("OTP Captured", f"OTP: {otp}")

# Load allowed sites from a file
def load_allowed_sites():
    try:
        with open(ALLOWED_SITES_FILE, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("Allowed sites file not found. Please create 'allowed_sites.txt'.")
        return []

# Load proxy list and filter out non-working proxies
def load_proxies():
    try:
        with open(PROXY_LIST_FILE, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("Proxy list file not found. Please create 'proxies.txt'.")
        return []

# Launch Chrome with proxy rotation
def launch_chrome(target_url, proxy=None):
    chrome_options = ChromeOptions()
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")

    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    driver.get(target_url)
    return driver

# OTP Interception Logic
def intercept_otp(driver, gui, allowed_sites):
    while True:
        time.sleep(random.uniform(2, 5))  # Random delay to avoid detection
        if gui.capturing:
            current_url = driver.current_url
            if any(site in current_url for site in allowed_sites):
                page_source = driver.page_source
                otp_matches = re.findall(OTP_PATTERN, page_source)
                if otp_matches:
                    otp = otp_matches[0]
                    gui.update_otp(otp)
                    print(f"✅ Captured OTP: {otp}")

# MITMProxy Interceptor
class OTPInterceptor:
    def __init__(self, gui):
        self.gui = gui

    def response(self, flow: http.HTTPFlow):
        if self.gui.capturing and flow.response:
            response_text = flow.response.get_text()
            otp_matches = re.findall(OTP_PATTERN, response_text)
            if otp_matches:
                otp = otp_matches[0]
                self.gui.update_otp(otp)
                ctx.log.info(f"✅ Captured OTP: {otp}")

# Start MITMProxy in a thread
def start_mitmproxy(gui):
    intercept_script = OTPInterceptor(gui)
    mitmdump(['-s', intercept_script])

# Main Function
def main():
    setup_database()
    
    root = tk.Tk()
    gui = OTPGUI(root)

    allowed_sites = load_allowed_sites()
    if not allowed_sites:
        messagebox.showerror("Error", "No allowed sites found. Please add sites to 'allowed_sites.txt'.")
        return
    
    target_url = simpledialog.askstring("Target Website", "Enter the OTP website URL:")
    if target_url not in allowed_sites:
        messagebox.showerror("Error", "The entered URL is not in the allowed sites list.")
        return
    
    proxies = load_proxies()
    selected_proxy = random.choice(proxies) if proxies else None
    driver = launch_chrome(target_url, proxy=selected_proxy)
    
    # Run OTP interception in separate threads
    threading.Thread(target=intercept_otp, args=(driver, gui, allowed_sites), daemon=True).start()
    threading.Thread(target=start_mitmproxy, args=(gui,), daemon=True).start()
    
    root.mainloop()
    driver.quit()

if __name__ == "__main__":
    main()
