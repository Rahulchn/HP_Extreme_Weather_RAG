import requests
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()

class HostHeaderSSLAdapter(HTTPAdapter):
    def resolve(self, host):
        return '14.139.127.84'
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

s = requests.Session()
s.mount('https://', HostHeaderSSLAdapter())

url = 'https://imdpune.gov.in/cmpg/Griddata/rainfall.php'
headers = {'User-Agent': 'Mozilla/5.0'}

print("Attempting POST with custom SSL...")
try:
    r = s.post(url, data={'rain': 2018}, headers=headers, verify=False, timeout=10)
    print(f"Status: {r.status_code}, len={len(r.content)}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    if len(r.content) > 1000:
        print(f"Received {len(r.content):,} bytes successfully!")
except Exception as e:
    print(f"Failed: {e}")
