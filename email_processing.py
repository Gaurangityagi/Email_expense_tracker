

import imaplib
import email
import csv
import re
from email.header import decode_header
from datetime import datetime, timedelta
import smtplib
from typing import List, Dict, Optional
import hashlib
import time
from threading import Thread

class EmailMonitor:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.last_checked = None
        self.new_emails = []
        self.running = False
        self.thread = None
        
    def start_monitoring(self, interval: int = 300) -> None:
        """Start background email monitoring"""
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._monitor_emails, args=(interval,))
            self.thread.daemon = True
            self.thread.start()
            
    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def _monitor_emails(self, interval: int) -> None:
        """Background email checking thread"""
        parser = EmailParser(self.email, self.password)
        while self.running:
            try:
                new_data = parser.parse_emails(
                    search_criteria=f'(SINCE "{self.last_checked.strftime("%d-%b-%Y")}")' 
                    if self.last_checked else "ALL"
                )
                
                if new_data:
                    self.new_emails.extend(new_data)
                    self.last_checked = datetime.now()
                    
            except Exception as e:
                print(f"Monitoring error: {e}")
                
            time.sleep(interval)

class EmailParser:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.monitor = None
        
    def connect(self) -> bool:
        """Connect to the IMAP server"""
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        try:
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

    def get_email_body(self, email_message) -> str:
        """Extract email body with detailed processing"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    continue
                    
                if content_type in ["text/plain", "text/html"]:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        decoded_body = payload.decode(charset)
                        
                        if content_type == "text/html":
                            decoded_body = re.sub('<[^<]+?>', ' ', decoded_body)
                        
                        body += decoded_body + "\n"
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

    def extract_order_info(self, email_body: str) -> Optional[float]:
        """Extract Indian Rupee amounts from email body"""
        try:
            if not isinstance(email_body, str):
                return None
            
            patterns = [
                (r'Amount Payable on Delivery\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Flipkart Delivery"),
                (r'Payment pending:\s*Rs.\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Amazon"),
                (r'Item\(s\) total\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Flipkart Items"),
                (r'(?:Total|Grand Total)\s*:\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Generic Total"),
                (r'₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:on delivery|payable)', "Contextual Amount"),
                (r'Order Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Order Total"),
                (r'Paid Via Cash:\s*₹\s*(\d+(?:\.\d{2})?)', "Cash Payment"),
                (r'Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Simple Total"),
                (r'RS\.\s*(?:RS\.|₹)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)', "RS Format"),
                (r'INR\s*(\d+(?:\.\d{2})?)', "INR Format")
            ]
            
            for pattern, _ in patterns:
                matches = re.findall(pattern, email_body, re.MULTILINE | re.IGNORECASE)
                if matches:
                    amount = max(matches, key=lambda x: float(str(x).replace(',', '')))
                    return float(re.sub(r'[^\d.]', '', str(amount)))
            
            return None
            
        except Exception as e:
            print(f"Error in amount extraction: {e}")
            return None

    def parse_emails(self, sender_email: Optional[str] = None, 
                    folder: str = "INBOX", search_criteria: str = "ALL") -> List[Dict]:
        """Parse emails with automatic reconnection"""
        if not self.connect():
            return []
        
        try:
            self.mail.select(folder)
            
            if sender_email and search_criteria:
                search_string = f'(FROM "{sender_email}") {search_criteria}'
            elif sender_email:
                search_string = f'(FROM "{sender_email}")'
            else:
                search_string = search_criteria
            
            _, message_numbers = self.mail.search(None, search_string)
            order_data = []
            
            for num in message_numbers[0].split():
                try:
                    _, msg_data = self.mail.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    body = self.get_email_body(email_message)
                    if not body:
                        continue
                        
                    order_amount = self.extract_order_info(body)
                    if order_amount:
                        order_data.append({
                            "date": email_message["date"],
                            "subject": email_message["subject"],
                            "sender": email_message["from"],
                            "amount": order_amount,
                        })
                        
                except Exception as e:
                    continue
            
            return order_data
            
        except Exception as e:
            print(f"Error in parse_emails: {e}")
            return []
            
        finally:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass

    def start_monitoring(self, interval: int = 300) -> None:
        """Start background email monitoring"""
        if not self.monitor:
            self.monitor = EmailMonitor(self.email_address, self.password)
            self.monitor.start_monitoring(interval)
            
    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        if self.monitor:
            self.monitor.stop_monitoring()

    def get_new_emails(self) -> List[Dict]:
        """Get any new emails detected by monitor"""
        if self.monitor:
            return self.monitor.new_emails
        return []
