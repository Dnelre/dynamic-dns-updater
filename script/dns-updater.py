import os
import time
import logging
import sys
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
# Helpers
# ======================

def write_heartbeat():
    """Update heartbeat timestamp for Docker healthcheck."""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception:
        logger.warning("Failed to write heartbeat", exc_info=True)


def get_public_ip():
    """Fetch current public IP address."""
    try:
        response = requests.get(PUBLIC_IP_RETURNER_URL, timeout=10)
        response.raise_for_status()
        ip = response.text.strip()
        logger.info(f"Public IP detected: {ip}")
        return ip
    except Exception:
        logger.exception("Failed to fetch public IP")
        return None


def update_dns():
    """Ensure DNS A record matches current public IP."""
    ip = get_public_ip()
    if not ip:
        return

    try:
        record = client.get_record(domain=DOMAIN, name=SUBDOMAIN, type="A")

        if record and record["data"] == ip:
            logger.info("DNS record unchanged")
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

    except Exception:
        logger.exception("Failed to update DNS record")


# ======================
# Main loop
# ======================

def main():
    logger.info("DNS updater started")

    while True:
        update_dns()
        write_heartbeat()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("DNS updater stopped (SIGINT)")
    except Exception:
        logger.exception("Fatal error — exiting")
        raise
