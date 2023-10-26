from django.core.mail import send_mail
from django.conf import settings


def send_email_to_client(message,recipient):
    subject="from django server"
    message=message
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [recipient]
    send_mail(subject, message, from_email, recipient_list)