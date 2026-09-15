import requests
import urllib3

urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    'http://www.imdpune.gov.in/cmpg/Griddata/rainfall.php',
    'http://imdpune.gov.in/cmpg/Griddata/rainfall.php',
    'https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php',
    'https://imdpune.gov.in/cmpg/Griddata/rainfall.php',
    'https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html',
    'https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html',
    'http://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html',
]

for url in urls:
    print(f"Testing {url} ...")
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=6)
        print(f"  GET Status: {r.status_code}, len={len(r.content)}")
    except Exception as e:
        print(f"  GET Failed: {type(e).__name__}")
    try:
        r = requests.post(url, data={'rain': 2018}, headers=headers, verify=False, timeout=6)
        print(f"  POST Status: {r.status_code}, len={len(r.content)}")
    except Exception as e:
        print(f"  POST Failed: {type(e).__name__}")
