import imaplib
import email
import re
from datetime import datetime

class EmailParser:
    def __init__(self, email_address, password, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail = None

    def connect(self):
        """Connect to the IMAP server"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def get_email_body(self, email_message):
        """Extract email body"""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type in ["text/plain", "text/html"]:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset)
                    except Exception as e:
                        continue
        else:
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or 'utf-8'
                body = payload.decode(charset)
            except Exception as e:
                pass
        return body

    def extract_order_info(self, email_body):
        """Extract order amounts from email body"""
        try:
            patterns = [
                (r'Amount Payable on Delivery\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Delivery Amount"),
                (r'Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Total Amount")
            ]
            
            for pattern, _ in patterns:
                matches = re.findall(pattern, email_body)
                if matches:
                    return float(matches[0].replace(',', ''))
            return None
        except Exception as e:
            print(f"Extraction error: {e}")
            return None

    def get_emails(self, sender_email=None, folder="INBOX", search_criteria="ALL"):
        """Get and parse emails"""
        if not self.connect():
            return []

        try:
            self.mail.select(folder)
            search_query = f'(FROM "{sender_email}") {search_criteria}' if sender_email else search_criteria
            _, message_numbers = self.mail.search(None, search_query)
            
            order_data = []
            for num in message_numbers[0].split():
                _, msg_data = self.mail.fetch(num, "(RFC822)")
                email_message = email.message_from_bytes(msg_data[0][1])
                body = self.get_email_body(email_message)
                amount = self.extract_order_info(body)
                
                if amount:
                    order_data.append({
                        "date": email_message["date"],
                        "subject": email_message["subject"],
                        "sender": email_message["from"],
                        "amount": amount
                    })
            
            return order_data
        except Exception as e:
            print(f"Email processing error: {e}")
            return []
        finally:
            if self.mail:
                try:
                    self.mail.close()
                    self.mail.logout()
                except:
                    pass
