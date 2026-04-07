import smtplib


def send_email(recipient: str, body: str) -> None:
    client = smtplib.SMTP("localhost")
    client.sendmail("noreply@example.com", [recipient], body)
