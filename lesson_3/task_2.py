import os
from pprint import pprint

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.cursor import Cursor

load_dotenv()

client = MongoClient(os.getenv('DB_CONNECTION_LINK'))
db = client['scrapper']
vacancy_collection = db['vacancy']


def get_vacancies_with_gte_salary(value: int, currency: str) -> Cursor:
    return vacancy_collection.find(
        {
            'currency': currency,
            '$or': [
                {
                    'salary_min': {'$gte': value}
                },
                {
                    'salary_max': {'$gte': value}
                },
            ]
        }
    )


def main():
    while True:
        try:
            currency = input('Select the desired currency. 1 - RUB, 2 - KZT, 3 - USD, 4 - EUR: ')

            match currency.upper():
                case '1' | 'RUB':
                    currency = 'руб'
                case '2' | 'KZT':
                    currency = 'KZT'
                case '3' | 'USD':
                    currency = 'USD'
                case '4' | 'EUR':
                    currency = 'EUR'
                case _:
                    raise ValueError
            break
        except ValueError:
            print('Choose one of the currencies shown\n')
            continue

    while True:
        try:
            value = int(input('Enter the desired salary: '))
        except ValueError:
            print('The input must be a number.\n')
            continue
        break

    vacancies = get_vacancies_with_gte_salary(value, currency)
    if vacancies:
        for vacancy in vacancies:
            pprint(vacancy)
    else:
        print('No vacancies found')


if __name__ == '__main__':
    main()
