#!/usr/bin/env python3
import time
from core.logger import logger
from core.ups_client import UPSClient
from core.monitor import UPSMonitor

# 1. Initialize Monitor
monitor = UPSMonitor()

def set_mock_ups(status: str, charge: int, runtime: int):
    """Helper to override UPSClient data on the fly."""
    UPSClient.get_status = lambda: status
    UPSClient.get_charge = lambda: charge
    UPSClient.get_runtime = lambda: runtime

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