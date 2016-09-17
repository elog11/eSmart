# coding=utf-8

import logging
import os
import smtplib
import socket
from collections import OrderedDict
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email import Encoders


#
# Email notification
#

def send_email(logging, smtp_host, smtp_ssl,
          smtp_port, smtp_user, smtp_pass,
          smtp_email_from, email_to, message,
          attachment_file=False, attachment_type=False):
    """
    Email a specific recipient or recipients a message.

    :return: success (0) or failure (1)
    :rtype: bool

    :param email_to: Who to email
    :type email_to: str or list
    :param message: Message in the body of the email
    :type message: str
    """
    try:
        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            server.ehlo()
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
        server.login(smtp_user, smtp_pass)
        msg = MIMEMultipart()
        msg['Subject'] = "eSmart Notification ({})".format(socket.gethostname())
        msg['From'] = smtp_email_from
        msg['To'] = email_to
        msg_body = MIMEText(message.decode('utf-8'), 'plain', 'utf-8')
        msg.attach(msg_body)

        if attachment_file and attachment_type == 'still':
            img_data = open(attachment_file, 'rb').read()
            image = MIMEImage(img_data, name=os.path.basename(attachment_file))
            msg.attach(image)
        elif attachment_file and attachment_type == 'video':
            out_filename = '{}-compressed.h264'.format(attachment_file)
            cmd_output('avconv -i "{}" -vf scale=-1:768 -c:v libx264 -preset veryfast -crf 22 -c:a copy "{}"'.format(attachment_file, out_filename))
            set_user_grp(out_filename, 'esmart', 'esmart')
            f = open(attachment_file, 'rb').read()
            video = MIMEBase('application', 'octet-stream')
            video.set_payload(f)
            Encoders.encode_base64(video)
            video.add_header('Content-Disposition', 'attachment; filename="{}"'.format(os.path.basename(attachment_file)))
            msg.attach(video)

        server.sendmail(msg['From'], msg['To'].split(","), msg.as_string())
        server.quit()
        return 0
    except Exception as error:
        if logging:
            logging.exception("[Email Notification] Cound not send email to {} "
                            "with message: {}. Error: {}".format(email_to, message, error))
        return 1
