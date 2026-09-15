import requests

for host in ['imdpune.gov.in', 'www.imdpune.gov.in']:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Host': host
    }
    for path in ['/cmpg/Griddata/rainfall.php', '/cmpg/Griddata/Rainfall_25_Bin.html', '/cmpg/Griddata/']:
        url = f"http://14.139.127.84{path}"
        try:
            r = requests.get(url, headers=headers, timeout=4)
            print(f"Host: {host} | GET {path} -> {r.status_code}, len={len(r.text)}")
            if r.status_code == 200:
                print("  Snippet:", r.text[:150])
        except Exception as e:
            print(f"Host: {host} | GET {path} -> Error: {e}")
