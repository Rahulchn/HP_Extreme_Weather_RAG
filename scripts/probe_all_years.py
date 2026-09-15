import requests
import urllib3
import ssl
import time
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()

class HostHeaderSSLAdapter(HTTPAdapter):
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

for year in range(2011, 2026):
    t0 = time.time()
    try:
        r = s.post(url, data={'rain': year}, headers=headers, verify=False, timeout=20, stream=True)
        content_type = r.headers.get('Content-Type', '')
        content_len = r.headers.get('Content-Length', '')
        
        # Read first 100 bytes
        chunk = next(r.iter_content(chunk_size=1024), b'')
        elapsed = time.time() - t0
        print(f"Year {year}: status={r.status_code}, content_type={content_type}, len={content_len}, chunk={len(chunk)}, time={elapsed:.1f}s", flush=True)
    except Exception as e:
        print(f"Year {year}: ERROR {e}", flush=True)
