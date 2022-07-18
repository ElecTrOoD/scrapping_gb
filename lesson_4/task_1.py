import os
import re
from datetime import datetime

import requests
from dotenv import load_dotenv
from lxml import html
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

load_dotenv()


class ParserMailNews:
    def __init__(self, db_link):
        self.news_collection = None
        self.db_link = db_link
        self.session = requests.Session()
        self.new_news_count = 0
        self.headers = {
            'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/100.0.4896.160 YaBrowser/22.5.4.904 Yowser/2.5 Safari/537.36'
        }

    def init_mongo_collection(self) -> None:
        client = MongoClient(self.db_link)
        db = client['scrapper']
        self.news_collection = db['news']

    def get_links(self) -> list:
        url = 'https://news.mail.ru/'

        response = self.session.get(url, headers=self.headers)
        dom = html.fromstring(response.text)
        return dom.xpath('//div[@data-logger="news__MainTopNews"]//a[@href]/@href')

    def get_news_data(self, url) -> None:
        response = self.session.get(url, headers=self.headers)
        dom = html.fromstring(response.text)

        id = int(re.search('/(\d*)/$', url).group(1))
        title = dom.xpath('//h1[@class="hdr__inner"]/text()')
        source = dom.xpath(
            '//span[@class="breadcrumbs__item"]//span[@class="link__text"]//text() | '
            '//span[@class="breadcrumbs__item"]//span[@class="link__text"]/../@href'
        )
        date = dom.xpath('//span[@datetime]/@datetime')

        data = {
            '_id': id,
            'title': title[0] if title else None,
            'source': {
                'name': source[1] if source[1] else None,
                'link': source[0] if source[0] else None
            },
            'link': url,
            'date': date[0] if date else None,
        }
        self.save_news_data(data)

    def save_news_data(self, data: dict) -> None:
        try:
            self.news_collection.insert_one(data)
            self.new_news_count += 1
        except DuplicateKeyError:
            self.news_collection.replace_one({'_id': data['_id']}, data)

    def run(self) -> None:
        self.init_mongo_collection()

        print('Start collecting information...')

        links = self.get_links()
        for link in links:
            self.get_news_data(link)

        print(f'\nDone!\nNew news: {self.new_news_count}')


if __name__ == '__main__':
    db_link = os.getenv('DB_CONNECTION_LINK')
    parser = ParserMailNews(db_link)

    parser.run()
