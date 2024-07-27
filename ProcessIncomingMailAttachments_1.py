"""
File: ProcessIncomingMailAttachments.py

Operation:  Scans the incoming mail in /home/uhi/MailDir and finds the mail with  attachments 
            
            changes the name of the .zip attachment to include the UUID of the sender.  
            This makes unique attachment names  

            moves the .zip file to /home/uhi/email_attachments

            deletes the processed  mail from MailDir so the attachments will not be processed again

Frequency:  The program runs every 5 minutes with cron
"""
import os
import email
import mailbox
from email.policy import default
import uuid
import logging

# Configure logging for flexibility and control
logging.basicConfig(
    filename='/home/uhi/logs/ProcessIncomingMailAttachments_1.log',
    level=logging.INFO,  # Adjust logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional timestamp format
)

# Define the path to the Maildir
maildir_path = "/home/uhi/Maildir" 

# Ensure the attachments directory exists
if not os.path.exists("/home/uhi/email_attachments"):
    os.makedirs("/home/uhi/email_attachments")

# Function to process attachments
def process_attachment(part, email_number):
    filename = part.get_filename()
    if filename:
        # Generate a unique filename using UUID
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join("/home/uhi/email_attachments", unique_filename)
        with open(filepath, 'wb') as f:
            f.write(part.get_payload(decode=True))
        print(f"Saved attachment: {unique_filename}")
        logging.info(f"Saved attachment: {unique_filename}")


# Function to process and print/save email body
def process_body(part, email_number):
    content_type = part.get_content_type()
    charset = part.get_content_charset() or 'utf-8'
    if content_type == 'text/plain':
        body = part.get_payload(decode=True).decode(charset, errors='ignore')
        with open(f"/home/uhi/email_attachments/{email_number}_body.txt", 'w') as f:
            f.write(body)
        print(f"Saved plain text body for email {email_number}")
    elif content_type == 'text/html':
        body = part.get_payload(decode=True).decode(charset, errors='ignore')
        with open(f"/home/uhi/email_attachments/{email_number}_body.html", 'w') as f:
            f.write(body)
        print(f"Saved HTML body for email {email_number}")

# Read emails from Maildir
maildir = mailbox.Maildir(maildir_path, factory=None, create=False)

for i, key in enumerate(maildir.keys(), start=1):
    msg = maildir[key]
    print('Processing file: ' + key)
    logging.info('Processing file: ' + key)   
    email_msg = email.message_from_bytes(msg.as_bytes(), policy=default)
    for part in email_msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            process_body(part, i)
        else:
            process_attachment(part, i)
    maildir.discard(key)  # Remove the email after processing
