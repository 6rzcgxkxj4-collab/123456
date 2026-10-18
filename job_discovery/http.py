import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def session():
    client = requests.Session()
    client.headers['User-Agent'] = 'JobDiscovery/1.0 (public recruitment research)'
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=frozenset(['GET']), respect_retry_after_header=True)
    client.mount('https://', HTTPAdapter(max_retries=retry))
    return client


def get_json(client, url, **kwargs):
    response = client.get(url, timeout=(10, 45), **kwargs)
    response.raise_for_status()
    return response.json()
