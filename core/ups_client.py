import subprocess
from config.settings import Config
from core.logger import logger

class UPSClient:
    """
    Handles hardware queries to the NUT upsc client.
    """
    @staticmethod
    def _run_cmd(cmd: str) -> str:
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    @classmethod
    def get_status(cls) -> str:
        status = cls._run_cmd(f"upsc {Config.UPS_NAME} ups.status 2>/dev/null")
        return status if status else "n/a"

    @classmethod
    def get_charge(cls) -> int:
        charge_str = cls._run_cmd(f"upsc {Config.UPS_NAME} battery.charge 2>/dev/null")
        return int(charge_str) if charge_str.isdigit() else 100

    @classmethod
    def get_runtime(cls) -> int:
        runtime_str = cls._run_cmd(f"upsc {Config.UPS_NAME} battery.runtime 2>/dev/null")
        return int(runtime_str) if runtime_str.isdigit() else 9999
