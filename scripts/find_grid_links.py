import requests
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Host': 'www.imdpune.gov.in'
}

r = requests.get('http://14.139.127.84/', headers=headers, timeout=5)
matches = re.findall(r'href=[\'"]([^\'"]*grid[^\'"]*)[\'"]', r.text, re.I)
print("Grid links from homepage:", matches)

matches_all = re.findall(r'href=[\'"]([^\'"]*rain[^\'"]*)[\'"]', r.text, re.I)
print("Rain links from homepage:", matches_all)
