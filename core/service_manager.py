import subprocess
import time
from config.settings import Config
from core.logger import logger
from core.notifier import Notifier

class ServiceManager:
    """
    Manages state, shutdown, and restoration of LXCs, VMs, the PBS Server, and the Host itself.
    """
    @staticmethod
    def _run_cmd(cmd: str) -> str:
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    @classmethod
    def _handle_pbs_shutdown(cls) -> str:
        logger.info(f"Initiating remote shutdown for PBS ({Config.PBS_IP})...")

        # Stop active PBS tasks
        active_cmd = f"ssh -o StrictHostKeyChecking=no root@{Config.PBS_IP} 'proxmox-backup-manager task list --active true'"
        if cls._run_cmd(active_cmd):
            stop_cmd = f"ssh root@{Config.PBS_IP} 'proxmox-backup-manager task list --active true | awk \"NR>1 {{print \\$1}}\" | xargs -I {{}} proxmox-backup-manager task stop {{}}'"
            cls._run_cmd(stop_cmd)
            logger.info("PBS active maintenance tasks stopped.")

        # Power off PBS
        cls._run_cmd(f"ssh root@{Config.PBS_IP} 'systemctl poweroff'")

        # Ping loop verification (Max 120s)
        logger.info(f"Waiting for PBS to go offline (Max timeout: {Config.PBS_TIMEOUT}s)...")
        start_time = time.time()
        is_offline = False

        while (time.time() - start_time) < Config.PBS_TIMEOUT:
            # -c 1 (1 ping), -W 1 (1 sec timeout)
            ping_res = subprocess.run(
                ["ping", "-c", "1", "-W", "1", Config.PBS_IP],
                capture_output=True
            )

            if ping_res.returncode != 0:
                is_offline = True
                break

            time.sleep(2)

        if is_offline:
            logger.info("PBS server successfully confirmed offline.")
            return f"""
                <tr>
                    <td>PBS Server</td>
                    <td>{Config.PBS_IP}</td>
                    <td>Shut down (Verified)</td>
                </tr>
            """

        logger.error("PBS shutdown timeout reached! Host still responding to ping.")
        Notifier.send_email(
            "WARNING: PBS Shutdown Timeout", 
            "warning", 
            f"""
                <p>The PBS Server ({Config.PBS_IP}) failed to shut down within {Config.PBS_TIMEOUT} seconds.</p>
                <p>Proceeding with PVE shutdown regardless to save battery.</p>
            """
        )
        return f"""
            <tr>
                <td>PBS Server</td>
                <td>{Config.PBS_IP}</td>
                <td>Timeout / Unknown State</td>
            </tr>
        """

    @classmethod
    def shutdown_services(cls) -> str:
        logger.info("Gracefully shutting down running VMs, LXCs, and PBS...")
        action_log = []
        processes = []

        # 1. Shutdown PBS
        pbs_row = cls._handle_pbs_shutdown()
        action_log.append(pbs_row)

        # 2. Shutdown VMs
        qm_out = cls._run_cmd("qm list | awk 'NR>1 {print $1, $2}'")
        for line in qm_out.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                vmid, vmname = parts
                if "status: running" in cls._run_cmd(f"qm status {vmid}"):
                    logger.info(f"Shutting down VM {vmid} ({vmname})...")
                    (Config.DATA_DIR / f"vm_{vmid}").touch()
                    processes.append(subprocess.Popen(f"qm shutdown {vmid}", shell=True))
                    action_log.append(
                        f"""
                        <tr>
                            <td>VM</td>
                            <td>{vmid} ({vmname})</td>
                            <td>Shut down</td>
                            </tr>
                        """
                    )

        # 3. Shutdown LXCs
        pct_out = cls._run_cmd("pct list | awk 'NR>1 {print $1, $3}'")
        for line in pct_out.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                ctid, ctname = parts
                if "status: running" in cls._run_cmd(f"pct status {ctid}"):
                    logger.info(f"Shutting down LXC {ctid} ({ctname})...")
                    (Config.DATA_DIR / f"lxc_{ctid}").touch()
                    processes.append(subprocess.Popen(f"pct shutdown {ctid}", shell=True))
                    action_log.append(
                        f"""
                        <tr>
                            <td>LXC</td>
                            <td>{ctid} ({ctname})</td>
                            <td>Shut down</td>
                            </tr>
                        """
                    )

        # Wait for all VMs/LXCs to finish stopping
        for p in processes:
            p.wait()

        logger.info("All targeted services shut down.")
        return "\n".join(action_log)

    @classmethod
    def restore_services(cls) -> str:
        logger.info("Restoring previously shut down services...")
        action_log = []

        for state_file in Config.DATA_DIR.glob("vm_*"):
            vmid = state_file.name.split("_")[1]
            logger.info(f"Starting VM {vmid}...")
            cls._run_cmd(f"qm start {vmid}")
            action_log.append(
                f"""
                <tr>
                    <td>VM</td>
                    <td>{vmid}</td>
                    <td>Started</td>
                    </tr>
                """
            )

        for state_file in Config.DATA_DIR.glob("lxc_*"):
            ctid = state_file.name.split("_")[1]
            logger.info(f"Starting LXC {ctid}...")
            cls._run_cmd(f"pct start {ctid}")
            action_log.append(
                f"""
                <tr>
                    <td>LXC</td>
                    <td>{ctid}</td>
                    <td>Started</td>
                    </tr>
                """
            )

        cls.wipe_data()
        return "\n".join(action_log)

    @classmethod
    def wipe_data(cls):
        """Wipes the state tracking files in /data to hand control back to Proxmox auto-boot."""
        logger.info("Wiping state directory...")
        for f in Config.DATA_DIR.glob("*"):
            if f.is_file():
                f.unlink()

    @classmethod
    def shutdown_host(cls):
        """Executes the final wipe and FSD command to halt the system and power off the UPS."""
        logger.warning("CRITICAL: Executing Host Shutdown (FSD)!")
        cls.wipe_data()

        # This tells nut to perform the final power off sequence
        subprocess.run(["/sbin/upsmon", "-c", "fsd"], check=False)
