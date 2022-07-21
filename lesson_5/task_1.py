import os
import re

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

load_dotenv()


class ParseMail:
    def __init__(self, driver, login, password, db_link):
        self.driver = driver
        self.email_login = login
        self.email_password = password
        self.db_link = db_link
        self.links = set()
        self.new_letters_count = 0
        self.letters_collection = None

    def init_mongo_collection(self) -> None:
        client = MongoClient(self.db_link)
        db = client['scrapper']
        self.letters_collection = db['letters']

    def login(self) -> None:
        self.driver.get('https://e.mail.ru/')
        self.driver.implicitly_wait(10)

        login_input = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.NAME, 'username'))
        )
        login_input.send_keys(self.email_login)

        password_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        password_button.click()

        password_input = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.NAME, 'password'))
        )
        password_input.send_keys(self.email_password)
        password_input.submit()

    def parse_links(self) -> None:
        letter_xpath = '//a[contains(@class, "llc llc_normal")]'
        WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.XPATH, letter_xpath))
        )

        while True:
            letters = self.driver.find_elements(By.XPATH, letter_xpath)
            links = {letter.get_attribute('href') for letter in letters}

            if links.issubset(self.links):
                break
            else:
                self.links.update(links)

                actions = ActionChains(self.driver)
                actions.scroll_to_element(letters[-1])
                actions.perform()

    def parse_letter_data(self, link: str) -> None:
        self.driver.get(link)

        max_mongo_integer = 9223372036854775807
        id = int(re.search(':(\d*):', link).group(1)) % max_mongo_integer

        letter = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.XPATH, '//div[contains(@class, "thread")]'))
        )

        letter_subject = letter.find_element(By.CLASS_NAME, 'thread-subject').text
        letter_date = letter.find_element(By.CLASS_NAME, 'letter__date').text
        letter_text = letter.find_element(By.XPATH, '//div[contains(@id, "_BODY")]').text
        letter_contact = letter.find_element(By.CLASS_NAME, 'letter-contact')
        letter_contact_name = letter_contact.text
        letter_contact_email = letter_contact.get_attribute('title')

        data = {
            '_id': id,
            'subject': letter_subject,
            'text': letter_text,
            'contact': {
                'name': letter_contact_name,
                'email': letter_contact_email
            },
            'date': letter_date,
        }

        self.save_letters_data(data)

    def save_letters_data(self, data: dict) -> None:
        try:
            self.letters_collection.insert_one(data)
            self.new_letters_count += 1
        except DuplicateKeyError:
            self.letters_collection.replace_one({'_id': data['_id']}, data)

    def run(self) -> None:
        self.init_mongo_collection()
        print('Trying to authorize...', end='')
        self.login()
        print('\rSuccessfully authorized. Start collecting letters...')
        self.parse_links()
        for link in self.links:
            self.parse_letter_data(link)
        print(f'\nDone!\nNew letters: {self.new_letters_count}')


if __name__ == '__main__':
    service = Service('../chromedriver.exe')
    options = Options()
    options.add_argument('start-maximized')
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)

    db_link = os.getenv('DB_CONNECTION_LINK')
    email_login = os.getenv('EMAIL_LOGIN')
    email_password = os.getenv('EMAIL_PASSWORD')

    parser = ParseMail(driver, email_login, email_password, db_link)
    parser.run()

    driver.close()
