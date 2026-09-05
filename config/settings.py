import os
from pathlib import Path


def env_int(name: str, default: int) -> int:
	return int(os.getenv(name, default))

class Config:
	"""
	Central configuration class for the UPS Monitor.
	"""
	UPS_NAME = os.getenv("UPS_NAME", "cyberpower@localhost")
	UPSC_TIMEOUT = env_int("UPSC_TIMEOUT", 10)
	TARGET_EMAIL = os.getenv("TARGET_EMAIL", "root")

	MIN_CHARGE = env_int("MIN_CHARGE", 75)
	MIN_RUNTIME = env_int("MIN_RUNTIME", 2500)
	SHUTDOWN_THRESHOLD = env_int("SHUTDOWN_THRESHOLD", 50)

	PBS_IP = os.getenv("PBS_IP", "192.168.1.251")
	PBS_TIMEOUT = env_int("PBS_TIMEOUT", 120)
	GUEST_SHUTDOWN_TIMEOUT = env_int("GUEST_SHUTDOWN_TIMEOUT", 60)
	POLL_INTERVAL = env_int("POLL_INTERVAL", 5)

	BASE_DIR = Path(os.getenv("BASE_DIR", "/opt/ups-management"))
	DATA_DIR = BASE_DIR / "data"
	TEMPLATE_FILE = BASE_DIR / "templates" / "email.html"
	LOG_FILE = os.getenv("LOG_FILE", "/var/log/ups-monitor.log")

	LAST_STATE_FILE = DATA_DIR / "ups_last_state.txt"
	SHUTDOWN_MARKER = DATA_DIR / "guests_shutdown_done.marker"
