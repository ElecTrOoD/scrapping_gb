import json
import os
import sys
import webbrowser
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()


def get_user_code() -> str:
    url = f'https://github.com/login/oauth/authorize?' \
          f'client_id={os.getenv("CLIENT_ID")}&' \
          f'redirect_uri={os.getenv("REDIRECT_URI")}&' \
          f'scope=user&' \
          f'response_type=code'
    webbrowser.open_new_tab(url)

    code_url = input('Insert page URL from browser: ')
    user_code = tuple(parse_qs(code_url).values())[0][0]
    return user_code


def get_access_token(code: str) -> str:
    params = {
        "client_id": os.getenv('CLIENT_ID'),
        "client_secret": os.getenv('CLIENT_SECRET'),
        "redirect_uri": os.getenv('REDIRECT_URI'),
        "code": code,
    }
    headers = {"Accept": "application/vnd.github.v3+json"}

    url = "https://github.com/login/oauth/access_token"
    return requests.post(url, params=params, headers=headers).json()['access_token']


def get_user_github_repositories_data(token: str) -> list[dict]:
    headers = {'Accept': 'application/vnd.github.v3+json',
               'Authorization': f'token {token}'}
    url = f'https://api.github.com/user/repos'
    response = requests.get(url, headers=headers)
    data = response.json()
    return data


def write_data(data: list[dict]) -> None:
    with open(f'auth_repositories.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False))


def main():
    try:
        user_code = get_user_code()
        access_token = get_access_token(user_code)
        repositories_data = get_user_github_repositories_data(access_token)
        write_data(repositories_data)
    except requests.RequestException as e:
        print(e)
        sys.exit(1)
    except (IndexError, KeyError):
        print('You inserted invalid URL, try again')
        sys.exit(1)
    print('User repositories successfully scrapped: ')
    print('\n'.join([repository['name'] for repository in repositories_data]))


if __name__ == '__main__':
    main()
