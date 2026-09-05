#!/usr/bin/env python3
import time
import signal
import sys
from config.settings import Config
from core.logger import logger
from core.monitor import UPSMonitor

# Global flag for clean exit
running = True

def signal_handler(signum, frame):
    """Intercepts systemctl stop commands for a graceful exit."""
    global running
    logger.info(f"Signal {signum} received. Stopping UPS Monitor service gracefully...")
    running = False

def main():
    logger.info(f"Starting UPS Monitor Daemon (Poll interval: {Config.POLL_INTERVAL}s)")

    # Register systemd stop signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    monitor = UPSMonitor()

    while running:
        try:
            monitor.evaluate_state()
        except Exception as e:
            logger.error(f"Unhandled exception in evaluate loop: {e}", exc_info=True)

        # Tick in 1-second increments so the daemon can stop instantly on SIGTERM
        for _ in range(Config.POLL_INTERVAL):
            if not running:
                break
            time.sleep(1)

    logger.info("UPS Monitor Daemon stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()
