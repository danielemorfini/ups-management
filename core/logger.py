import logging
from logging.handlers import RotatingFileHandler
from config import Config

class LoggerSetup:
    """
    Utility class to configure the dual-output logger (Systemd + Rotating File).
    """
    @staticmethod
    def get_logger():
        logger = logging.getLogger("UPSMonitor")
        logger.setLevel(logging.INFO)

        # Prevent adding duplicate handlers if instantiated multiple times
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

            # File Handler: Max 5MB per file, keep 3 historical backups
            file_handler = RotatingFileHandler(Config.LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # Console Handler: Outputs to stdout (captured by journalctl)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

# Global logger instance
logger = LoggerSetup.get_logger()
