import json
import re

import requests
from bs4 import BeautifulSoup, Tag


def get_content(session: requests.Session, job_name: str, next_page: int) -> Tag:
    url = 'https://hh.ru/search/vacancy'
    params = {
        'text': job_name,
        'page': next_page,
    }
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.160 '
            'YaBrowser/22.5.4.904 Yowser/2.5 Safari/537.36'
    }

    response = session.get(url, params=params, headers=headers)
    return BeautifulSoup(response.text, 'html.parser').select('div.vacancy-serp-content')[0]


def get_jobs_data(data: Tag) -> list[Tag]:
    jobs = data.select('div.vacancy-serp-item')
    output = []

    for job in jobs:
        output.append(get_job_data(job))
    return output


def get_job_data(job: Tag) -> dict:
    salary = get_salary(job)

    title = job.select('a[data-qa="vacancy-serp__vacancy-title"]')
    employer = job.select('a[data-qa="vacancy-serp__vacancy-employer"]')
    city = job.select('div[data-qa="vacancy-serp__vacancy-address"]')

    data = {
        'name': title[0].text if title else None,
        'link': title[0].get('href') if title else None,
        'employer': employer[0].text if employer else None,
        'city': city[0].text if city else None,
        'salary_min': salary[0],
        'salary_max': salary[1],
        'currency': salary[2],
        'service': 'hh.ru',
    }
    return data


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


def check_next_page(dom: Tag) -> bool:
    return bool(dom.select('div.pager>a[data-qa="pager-next"]'))


def write_data(data: list[dict], job_name: str) -> None:
    with open(f'{job_name.replace(" ", "_")}.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False))


def main() -> None:
    job_name = input('Enter the desired vacancy: ')
    page_number = 0
    session = requests.Session()
    jobs_data = []

    while True:
        content = get_content(session, job_name, page_number)
        jobs_data += get_jobs_data(content)
        if check_next_page(content):
            page_number += 1
        else:
            break
        print(f'\rPages scrapped: {page_number}', end='')

    write_data(jobs_data, job_name)
    print('\nDone!')


if __name__ == '__main__':
    main()
