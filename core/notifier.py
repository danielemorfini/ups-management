import subprocess
from string import Template
from config.settings import Config
from core.logger import logger

class Notifier:
    """
    Handles dynamic HTML template substitution and mail dispatch.
    """
    @staticmethod
    def send_email(subject: str, header_class: str, body: str, table_rows: str = ""):
        table_html = ""
        if table_rows:
            table_html = (
                f"""
                <table>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>ID</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                """
            )

        if Config.TEMPLATE_FILE.exists():
            template_str = Config.TEMPLATE_FILE.read_text()
            mapping = {
                "CLASS": header_class,
                "SUBJECT": subject,
                "BODY": body,
                "TABLE": table_html,
            }

            # String Template requires $VAR syntax natively. We'll map {{VAR}} to $VAR
            safe_template = template_str.replace("$", "$$")
            for key in mapping.keys():
                safe_template = safe_template.replace(f"{{{{{key}}}}}", f"${key}")

            message = Template(safe_template).safe_substitute(mapping)
        else:
            logger.warning("Email template not found. Sending raw text.")
            message = f"Subject: {subject}\n\n{body}\n{table_html}"

        try:
            mail_proc = subprocess.Popen(
                [
                    "/usr/bin/mail",
                    "-a",
                    "Content-Type: text/html; charset=UTF-8",
                    "-s",
                    subject,
                    Config.TARGET_EMAIL
                ],
                stdin=subprocess.PIPE,
                text=True
            )
            mail_proc.communicate(input=message)
            logger.info(f"Email sent: '{subject}'")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
