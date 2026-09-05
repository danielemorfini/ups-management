from config.settings import Config
from core.logger import logger
from core.ups_client import UPSClient
from core.service_manager import ServiceManager
from core.notifier import Notifier

class UPSMonitor:
    """
    Evaluates UPS state transitions and executes phase routines.
    """
    def __init__(self):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.prev_status = "OL"
        if Config.LAST_STATE_FILE.exists():
            self.prev_status = Config.LAST_STATE_FILE.read_text().strip()

    def evaluate_state(self):
        current_status = UPSClient.get_status()

        if current_status == "n/a":
            return

        charge = UPSClient.get_charge()
        runtime = UPSClient.get_runtime()

        # Update persistent state tracker
        if current_status != self.prev_status:
            Config.LAST_STATE_FILE.write_text(current_status)

        # STAGE: ON LOWBATT (Hardware override)
        if "LB" in current_status:
            self._handle_onlowbatt()
            self.prev_status = current_status
            return

        # STAGE: ON BATTERY
        if "OB" in current_status:
            # Send initial power loss email if just transitioned
            if "OB" not in self.prev_status:
                logger.warning(f"Power lost! Charge: {charge}%, Runtime: {runtime}s")
                body = (
                    "<p>Power failure detected on main server.</p>"
                    f"<ul><li><strong>Battery Charge:</strong> {charge}%</li>"
                    f"<li><strong>Remaining Runtime:</strong> {runtime}s</li></ul>"
                )
                Notifier.send_email("INFO: UPS on battery", "info", body)

            self._handle_onbattery(charge, runtime)

        # STAGE: ONLINE
        if "OL" in current_status and "OB" in self.prev_status:
            self._handle_online()

        self.prev_status = current_status

    def _handle_online(self):
        logger.info("Power restored. Transitioning to ONLINE phase.")
        table_rows = ServiceManager.restore_services()

        body = "<p>UPS power restored. Services returning to normal operational state.</p>"
        if not table_rows:
            body += "<p>No services were previously shut down by the script.</p>"

        Notifier.send_email("UPS Power Restored", "success", body, table_rows)

    def _handle_onbattery(self, charge: int, runtime: int):
        # 1. Host Shutdown Check (50%)
        if charge <= Config.SHUTDOWN_THRESHOLD:
            logger.critical(f"Host Shutdown Threshold breached ({charge}%).")
            # Ensure services are stopped first just in case the battery plummeted
            if not Config.SHUTDOWN_MARKER.exists():
                ServiceManager.shutdown_services()

            body = f"<p>CRITICAL: Host Battery Threshold breached ({charge}%). Forcing Host Shutdown.</p>"
            Notifier.send_email("CRITICAL: Host Shutting Down", "critical", body)

            ServiceManager.shutdown_host()
            return

        # 2. Service Shutdown Check (75% or 2500s)
        if (charge <= Config.MIN_CHARGE or runtime <= Config.MIN_RUNTIME) and not Config.SHUTDOWN_MARKER.exists():
            logger.warning(f"Service Threshold breached. Charge: {charge}%, Runtime: {runtime}s.")
            Config.SHUTDOWN_MARKER.touch()

            body = (
                "<p>UPS service safety thresholds breached!</p>"
                f"<ul><li><strong>Charge:</strong> {charge}% (Min: {Config.MIN_CHARGE}%)</li>"
                f"<li><strong>Runtime:</strong> {runtime}s (Min: {Config.MIN_RUNTIME}s)</li></ul>"
            )
            table_rows = ServiceManager.shutdown_services()
            Notifier.send_email("WARNING: UPS Threshold Breached - Services Shutting Down", "warning", body, table_rows)

    def _handle_onlowbatt(self):
        logger.critical("UPS hardware reported LOWBATT. Bypassing software thresholds.")

        if not Config.SHUTDOWN_MARKER.exists():
            ServiceManager.shutdown_services()

        body = "<p>CRITICAL: UPS hardware reports LOW BATT. Initiating immediate Host Shutdown.</p>"
        Notifier.send_email("CRITICAL: UPS Low Battery - Host Shutting Down", "critical", body)

        ServiceManager.shutdown_host()
