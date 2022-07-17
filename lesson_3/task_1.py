import os
import re

import requests
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

load_dotenv()


class ParserHH:
    def __init__(self, vacancy_name, db_link):
        self.vacancy_collection = None
        self.vacancy_name = vacancy_name
        self.db_link = db_link
        self.session = requests.Session()
        self.page_number = 0
        self.new_vacancy_count = 0

    def init_mongo_collection(self):
        client = MongoClient(self.db_link)
        db = client['scrapper']
        self.vacancy_collection = db['vacancy']

    def get_content(self) -> Tag:
        url = 'https://hh.ru/search/vacancy'
        params = {
            'text': self.vacancy_name,
            'page': self.page_number,
            'items_on_page': 20
        }
        headers = {
            'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/100.0.4896.160 YaBrowser/22.5.4.904 Yowser/2.5 Safari/537.36'
        }

        response = self.session.get(url, params=params, headers=headers)
        return BeautifulSoup(response.text, 'html.parser').select('div.vacancy-serp-content')[0]

    def get_jobs_data(self, data: Tag):
        jobs = data.select('div.vacancy-serp-item')

        for job in jobs:
            self.get_job_data(job)

    def get_job_data(self, job: Tag) -> dict:
        salary = self.get_salary(job)

        title = job.select('a[data-qa="vacancy-serp__vacancy-title"]')
        name = title[0].text if title else None,
        link = title[0].get('href'),
        id = int(re.search('vacancy/(\d*)?', link[0]).group(1))
        employer = job.select('a[data-qa="vacancy-serp__vacancy-employer"]')
        city = job.select('div[data-qa="vacancyn-serp__vacancy-address"]')

        data = {
            '_id': id,
            'name': name[0],
            'link': link[0],
            'employer': employer[0].text if employer else None,
            'city': city[0].text if city else None,
            'salary_min': salary[0],
            'salary_max': salary[1],
            'currency': salary[2],
            'service': 'hh.ru',
        }
        self.save_job_data(data)

    def save_job_data(self, data: dict):
        try:
            self.vacancy_collection.insert_one(data)
            self.new_vacancy_count += 1
        except DuplicateKeyError:
            self.vacancy_collection.replace_one({'_id': data['_id']}, data)

    @staticmethod
    def get_salary(job: Tag) -> tuple[int or None, int or None, str or None]:
        try:
            salary = job.select('span[data-qa="vacancy-serp__vacancy-compensation"]')[0].text

            if match := re.findall('^(\d*.\d*) – (\d*.\d*) (\w*)', salary, re.U):
                return int(re.sub('\D', '', match[0][0])), int(re.sub('\D', '', match[0][1])), match[0][2]
            elif match := re.findall('^от (\d*.\d*) (\w*)', salary, re.U):
                return int(re.sub('\D', '', match[0][0])), None, match[0][1]
            elif match := re.findall('^до (\d*.\d*) (\w*)', salary, re.U):
                return None, int(re.sub('\D', '', match[0][0])), match[0][1]
            else:
                raise IndexError
        except IndexError:
            return None, None, None

    @staticmethod
    def check_next_page(dom: Tag) -> bool:
        return bool(dom.select('div.pager>a[data-qa="pager-next"]'))

    def run(self):
        self.init_mongo_collection()

        while True:
            content = self.get_content()
            self.get_jobs_data(content)
            if self.check_next_page(content):
                self.page_number += 1
            else:
                break
            print(f'\rPages scrapped: {self.page_number}', end='')

        print(f'\nDone!\nNew vacancies: {self.new_vacancy_count}')


if __name__ == '__main__':
    vacancy_name = input('Enter the desired vacancy: ')
    db_link = os.getenv('DB_CONNECTION_LINK')
    parser = ParserHH(vacancy_name, db_link)

    parser.run()
