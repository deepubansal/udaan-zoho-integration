import requests
import os


def get_session_cookie():
    cookie_provider_api_url = os.environ['COOKIE_PROVIDER_API_URL']
    return requests.get(cookie_provider_api_url).text


def get_auth_token():
    refresh_token = os.environ['UDAAN_REFRESH_TOKEN']
    cookies = {'rt.0': refresh_token}
    r = requests.post('https://udaan.com/auth/token', cookies=cookies)
    return r.json()['accessToken']
