import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Host': 'imdpune.gov.in'
}
url = "http://14.139.127.84/cmpg/Griddata/rainfall.php"
r = requests.get(url, headers=headers, allow_redirects=False, timeout=5)
print(f"Status: {r.status_code}")
print("Headers:", r.headers)
