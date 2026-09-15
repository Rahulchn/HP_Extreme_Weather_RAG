import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Host': 'www.imdpune.gov.in'
}

try:
    r = requests.get('http://14.139.127.84/', headers=headers, timeout=5)
    print(f"Status: {r.status_code}, len={len(r.text)}")
    print(r.text[:300])
except Exception as e:
    print(f"Error: {e}")
