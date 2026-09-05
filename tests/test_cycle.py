#!/usr/bin/env python3
import time
from core.logger import logger
from core.ups_client import UPSClient
from core.service_manager import ServiceManager
from core.notifier import Notifier
from core.monitor import UPSMonitor

# 1. Initialize Monitor
monitor = UPSMonitor()

def set_mock_ups(status: str, charge: int, runtime: int):
    """Helper to override UPSClient data on the fly."""
    UPSClient.get_status = lambda: status
    UPSClient.get_charge = lambda: charge
    UPSClient.get_runtime = lambda: runtime

# Never let a test run touch real VMs/LXCs/PBS/host or send real emails.
# ServiceManager/Notifier are replaced with logging no-ops for the duration of this script.
def _mock_shutdown_services():
    logger.info("[DRY-RUN] Would shut down PBS, running VMs, and running LXCs now.")
    return ""

def _mock_restore_services():
    logger.info("[DRY-RUN] Would restore previously shut down VMs/LXCs now.")
    return ""

def _mock_shutdown_host():
    logger.info("[DRY-RUN] Would execute host FSD (power off) now.")

def _mock_send_email(subject, header_class, body, table_rows=""):
    logger.info(f"[DRY-RUN] Would send email: '{subject}'")

ServiceManager.shutdown_services = _mock_shutdown_services
ServiceManager.restore_services = _mock_restore_services
ServiceManager.shutdown_host = _mock_shutdown_host
Notifier.send_email = _mock_send_email

logger.info("-----------------------------------------------------------")
logger.info("TEST MODE: ServiceManager and Notifier are mocked. No real VM/LXC/PBS/host actions will run.")
logger.info("-----------------------------------------------------------")


# STAGE 1: Normal Operation (Online, 100% Charge)
logger.info("### STAGE 1: ONLINE (100% Charge)")
set_mock_ups("OL", 100, 3600)
monitor.evaluate_state()
logger.info("---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----")
time.sleep(5)

# STAGE 2: Power Loss (On Battery, 90% Charge - Safe Level)
logger.info("### STAGE 2: ON-BATT (90% Charge - safe)")
set_mock_ups("OB", 90, 3000)
monitor.evaluate_state()
logger.info("---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----")
time.sleep(5)

# STAGE 3: Service Threshold Breach (On Battery, 70% Charge - Below 75% limit)
logger.info("### STAGE 3: Service threshold breach (VMs and LXCs shutdown)")
set_mock_ups("OB", 70, 2000)
monitor.evaluate_state()
logger.info("---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----")
time.sleep(5)

# STAGE 4: Power Restored (Online, 80% Charge)
logger.info("### STAGE 4: Power restored")
set_mock_ups("OL", 80, 2800)
monitor.evaluate_state()
logger.info("---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----")
time.sleep(45)

# STAGE 5: Host Shutdown Breach (On Battery, 45% Charge - Below 50% limit)
logger.info("### STAGE 5: Host shutdown breach (complete shutdown)")
set_mock_ups("OB", 45, 1200)
monitor.evaluate_state()
time.sleep(5)

logger.info("-----------------------------------------------------------")