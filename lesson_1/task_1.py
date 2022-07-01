import json
import sys

import requests


class EmptyResultingList(Exception):
    pass


def get_user_github_repositories_data(username: str) -> list[dict]:
    url = f'https://api.github.com/users/{username}/repos'
    response = requests.get(url)
    data = response.json()
    if not data or (type(data) == dict and data['message'] == 'Not Found'):
        raise EmptyResultingList
    return data


def write_data(data: list[dict], username: str) -> None:
    with open(f'{username}_repositories.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False))


def main():
    username = input('Enter your github username: ')
    try:
        repositories_data = get_user_github_repositories_data(username)
        write_data(repositories_data, username)
    except EmptyResultingList:
        print('The resulting list of repositories is empty. Check username')
        sys.exit(1)
    except requests.RequestException as e:
        print(e)
        sys.exit(1)
    print('User repositories successfully scrapped: ')
    print('\n'.join([repository['name'] for repository in repositories_data]))


if __name__ == '__main__':
    main()
