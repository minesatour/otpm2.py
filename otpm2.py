import time
import os
import platform
import logging
import random
import string
import mitmproxy.http
import mitmproxy.options
from mitmproxy import http
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Proxy Setup (for mitmproxy)
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8080

# Function to generate random User-Agent
def random_user_agent():
    return random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
    ])

# Configure the WebDriver
def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument(f"--proxy-server={PROXY_HOST}:{PROXY_PORT}")
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument(f"user-agent={random_user_agent()}")  # Random User-Agent for stealth

    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver)  # Apply stealth settings for Selenium to avoid detection
    return driver

# Capture OTPs using mitmproxy
def intercept_otp(flow: mitmproxy.http.HTTPFlow):

    # Check for OTP patterns in intercepted traffic
    otp_keywords = ["otp", "verification", "code", "2fa", "token"]
    otp_data = ""
    
    for keyword in otp_keywords:
        if keyword in request.url.lower():
            otp_data = request.url  # Or any logic to extract the OTP data

    if otp_data:
        logging.info(f"Intercepted OTP: {otp_data}")
        # Here you could also store the OTP to a database or notify elsewhere
        return otp_data
    return None

# Function to start the interception and capture OTPs
def start_interception():
    logging.info("Starting mitmproxy to intercept OTP requests...")

    # Run mitmproxy programmatically with options
    opts = mitmproxy.options.Options(listen_host=PROXY_HOST, listen_port=PROXY_PORT)
    mproxy = mitmproxy.controller.MitMProxy(opts)
    mproxy.addons.add(OTPInterceptor())  # Use custom interceptor class for OTP interception
    mproxy.run()

# OTP Interceptor class for mitmproxy
class OTPInterceptor:
    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Extract OTP from the request
        otp = intercept_otp(flow.request)
        if otp:
            logging.info(f"OTP Detected: {otp}")
            # You can perform actions like storing the OTP or sending it to another system

# Function to handle OTP capture and store or display
def capture_otp():
    # Start mitmproxy to intercept OTP traffic
    start_interception()

# Main function to drive the script
def main():
    logging.info("OTP Interception Script started.")
    
    # WebDriver to simulate login flow or navigate for OTP capture (example for demo purposes)
    driver = setup_browser()
    
    # Example login (modify based on your test case)
    logging.info("Navigating to login page...")
    driver.get("https://example.com/login")
    
    # Wait for page to load, then input credentials
    driver.find_element(By.ID, "username").send_keys("your_email@example.com")
    driver.find_element(By.ID, "password").send_keys("your_password")
    driver.find_element(By.ID, "login_button").click()
    
    # Assuming OTP request is triggered after login
    logging.info("Triggering OTP request...")
    time.sleep(5)  # Wait for the OTP request to be triggered
    
    # Start capturing OTP via mitmproxy
    capture_otp()
    
    driver.quit()  # Clean up and close the browser

if __name__ == "__main__":
    main()
