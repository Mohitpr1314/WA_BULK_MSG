# Packages
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote
import time
import logging
import schedule
import datetime
import csv

# Config
login_time = 30     # Time for login (in seconds)
new_msg_time = 10    # Time for a new message (in seconds)
send_msg_time = 5   # Time for sending a message (in seconds)
country_code = 91   # Set your country code

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_driver():
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()))

def encode_message(file_path):
    with open(file_path, 'r') as file:
        return quote(file.read())

def open_whatsapp_web(driver, link):
    driver.get(link)
    logging.info("Opened WhatsApp Web. Please scan the QR code.")
    time.sleep(login_time)

def send_message(driver, number, encoded_message):
    full_number = f"{country_code}{number}"
    link = f'https://web.whatsapp.com/send/?phone={full_number}&text={encoded_message}'
    driver.get(link)
    try:
        # Wait for the message input box to be present
        WebDriverWait(driver, new_msg_time).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][1]'))
        )
        # Additional wait to ensure the page is fully loaded
        time.sleep(2)

        # Check if the contact is invalid or not found
        invalid_contact_xpath = '//div[contains(text(), "Phone number shared via url is invalid.")]'
        if driver.find_elements(By.XPATH, invalid_contact_xpath):
            logging.error(f"Invalid phone number: {full_number}")
            return

        # Send the message
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        logging.info(f"Message sent to {full_number}")
        time.sleep(send_msg_time)
    except Exception as e:
        logging.error(f"Failed to send message to {full_number}: {e}")

def schedule_messages(driver, encoded_message, schedule_file):
    with open(schedule_file, 'r') as file:
        csv_reader = csv.reader(file)
        for line_number, row in enumerate(csv_reader, start=1):
            if line_number == 1:  # Skip the header line
                continue
            if not row:
                logging.warning(f"Empty line at line {line_number} in schedule file.")
                continue
            if len(row) != 3:
                logging.error(f"Invalid schedule format at line {line_number}: {row}")
                continue
            
            # Strip leading and trailing spaces from number, date, and time
            number = row[0].strip()
            date_str = row[1].strip()
            time_str = row[2].strip()

            try:
                # Combine the date and time for scheduling
                schedule_datetime = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                schedule.every().day.at(time_str).do(send_message, driver, number, encoded_message)
                logging.info(f"Scheduled message to {number} at {schedule_datetime}")
            except ValueError as e:
                logging.error(f"Invalid date or time format at line {line_number}: {row} - {e}")

def main():
    driver = create_driver()
    try:
        encoded_message = encode_message('message.txt')
        open_whatsapp_web(driver, 'https://web.whatsapp.com')

        # Schedule messages
        schedule_messages(driver, encoded_message, 'schedule.csv')

        # Keep the script running to execute scheduled tasks
        while True:
            schedule.run_pending()
            time.sleep(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
