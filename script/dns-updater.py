import os
import re
import time
import signal
import logging
import sys
import threading
import requests
from domeneshop import Client

# ======================
# Configuration
# ======================
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))
HEARTBEAT_FILE = "/tmp/heartbeat"
TOKEN = os.environ.get("DOMENESHOP_TOKEN")
SECRET = os.environ.get("DOMENESHOP_SECRET")
DOMAIN = os.environ.get("DOMAIN")
SUBDOMAIN = os.environ.get("SUBDOMAIN")
PUBLIC_IP_RETURNER_URL = os.environ.get("PUBLIC_IP_RETURNER_URL")

# ======================
# Logging
# ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("dns-updater")

# ======================
# Validation
# ======================
REQUIRED_ENV_VARS = {
    "DOMENESHOP_TOKEN": TOKEN,
    "DOMENESHOP_SECRET": SECRET,
    "DOMAIN": DOMAIN,
    "SUBDOMAIN": SUBDOMAIN,
    "PUBLIC_IP_RETURNER_URL": PUBLIC_IP_RETURNER_URL,
}
missing = [k for k, v in REQUIRED_ENV_VARS.items() if not v]
if missing:
    logger.error(f"Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

# ======================
# Client
# ======================
client = Client(token=TOKEN, secret=SECRET)

# ======================
# State
# ======================
last_known_ip: str | None = None
shutdown = threading.Event()

# ======================
# Signal handling
# ======================
def handle_signal(signum, frame):
    logger.info("Shutdown signal received")
    shutdown.set()

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ======================
# Helpers
# ======================
def write_heartbeat():
    """Update heartbeat timestamp for Docker healthcheck."""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception:
        logger.warning("Failed to write heartbeat", exc_info=True)


def is_valid_ipv4(ip: str) -> bool:
    """Validate that a string is a valid IPv4 address."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    return bool(re.match(pattern, ip)) and all(0 <= int(p) <= 255 for p in ip.split("."))


def get_public_ip() -> str | None:
    """Fetch current public IP address."""
    try:
        response = requests.get(PUBLIC_IP_RETURNER_URL, timeout=10)
        response.raise_for_status()
        ip = response.text.strip()
        if not is_valid_ipv4(ip):
            logger.error(f"Invalid IP address received: {ip!r}")
            return None
        logger.info(f"Public IP detected: {ip}")
        return ip
    except Exception:
        logger.exception("Failed to fetch public IP")
        return None


def update_dns():
    """Ensure DNS A record matches current public IP."""
    global last_known_ip

    ip = get_public_ip()
    if not ip:
        return

    if ip == last_known_ip:
        logger.info("IP unchanged, skipping DNS check")
        return

    try:
        record = client.get_record(domain=DOMAIN, name=SUBDOMAIN, type="A")
        if record and record["data"] == ip:
            logger.info("DNS record already up to date")
            last_known_ip = ip
            return

        if record:
            client.update_record(
                domain=DOMAIN,
                record_id=record["id"],
                data=ip,
            )
            logger.info(f"DNS record updated → {ip}")
        else:
            client.create_record(
                domain=DOMAIN,
                name=SUBDOMAIN,
                type="A",
                data=ip,
            )
            logger.info(f"DNS record created → {ip}")

        last_known_ip = ip

    except Exception:
        logger.exception("Failed to update DNS record")


# ======================
# Main loop
# ======================
def main():
    logger.info("DNS updater started")
    while not shutdown.is_set():
        update_dns()
        write_heartbeat()
        shutdown.wait(timeout=CHECK_INTERVAL)
    logger.info("DNS updater stopped")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error — exiting")
        raise
