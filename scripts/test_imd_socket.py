import requests
import urllib3
import socket

urllib3.disable_warnings()

print("DNS resolution:")
for host in ['imdpune.gov.in', 'www.imdpune.gov.in', 'mausam.imd.gov.in']:
    try:
        ip = socket.gethostbyname(host)
        print(f"  {host} -> {ip}", flush=True)
    except Exception as e:
        print(f"  {host} -> {e}", flush=True)

headers = {'User-Agent': 'Mozilla/5.0'}

# Test connection to port 80 / 443
for host in ['imdpune.gov.in', 'www.imdpune.gov.in']:
    for port in [80, 443]:
        s = socket.socket()
        s.settimeout(3.0)
        try:
            s.connect((host, port))
            print(f"  Connected to {host}:{port} successfully!", flush=True)
            s.close()
        except Exception as e:
            print(f"  Cannot connect {host}:{port}: {e}", flush=True)
