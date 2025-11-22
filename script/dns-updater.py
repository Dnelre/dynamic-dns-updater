import time
import requests
from domeneshop import Client
import os

# Read credentials from environment
TOKEN = os.environ.get("DOMENESHOP_TOKEN")
SECRET = os.environ.get("DOMENESHOP_SECRET")
DOMAIN = os.environ.get("DOMAIN")
SUBDOMAIN = os.environ.get("SUBDOMAIN")
PUBLIC_IP_RETURNER_URL = os.environ.get("PUBLIC_IP_RETURNER_URL") # "https://api.ipify.org"

client = Client(token=TOKEN, secret=SECRET)

CHECK_INTERVAL = 300  # seconds, 5 minutes

def get_public_ip():
    try:
        return requests.get(PUBLIC_IP_RETURNER_URL ).text
    except Exception as e:
        print(f"Failed to get public IP: {e}")
        return None

def update_dns():
    ip = get_public_ip()
    if not ip:
        return

    record = client.get_record(domain=DOMAIN, name=SUBDOMAIN, type="A")
    if record and record['data'] == ip:
        print("IP unchanged.")
        return

    if record:
        client.update_record(domain=DOMAIN, record_id=record['id'], data=ip)
        print(f"Updated DNS record to {ip}")
    else:
        client.create_record(domain=DOMAIN, name=SUBDOMAIN, type="A", data=ip)
        print(f"Created DNS record with {ip}")

if __name__ == "__main__":
    result = get_public_ip()
    print(result)
    #while True:
   #     update_dns()
    #   time.sleep(CHECK_INTERVAL)
