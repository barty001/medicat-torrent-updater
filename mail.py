#!/usr/bin/env python3

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.message import EmailMessage

from typing import List


def send_notification(
        medicat_version: str,
        medicat_old_version: str,
        medicat_torrents_table: str,
        smtp_server: str,
        smtp_username: str,
        smtp_password: str,
        recipient_addresses: List[str],
        sender_address: str,
        sender_displayname: str = "MediCat Torrent Updater"
):
    # TODO: Move message to config?

    msg = EmailMessage()
    msg.set_content(f"""
<!doctype html>
<html>
<head></head>
<body>
<p><b>Hallo!</b></p>
<p>
Medicat wurde von <code>{medicat_old_version}</code> auf Version <code>{medicat_version}</code> aktualisiert!<br/>
Die neue Version wurde zu qBittorrent hinzugefügt, läd nun herunter und wird in Kürze geseedet.
</p>
<p>
In qBittorrent sind nun folgende Versionen enthalten:
</p>

<div>
{medicat_torrents_table}
</div>

<p>MfG,<br/>
~ {sender_displayname}!</p>
</body>
</html>""", subtype="html")

    msg['Subject'] = f'Medicat Update {medicat_old_version} -> {medicat_version}'
    msg['From'] = f'"{sender_displayname}" <{sender_address}>'
    msg['To'] = ", ".join(recipient_addresses)

    with smtplib.SMTP(smtp_server, 587) as server:
        server.starttls()  # Secure the connection

        server.login(smtp_username, smtp_password)
        server.send_message(msg, sender_address, recipient_addresses)
        print("mail successfully sent")
