

import imaplib
import email
import csv
import re
from email.header import decode_header
from datetime import datetime, timedelta
import smtplib
import time
from threading import Thread

class EmailMonitor:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.last_checked = None
        self.new_emails = []
        self.running = False
        self.thread = None
        self.refresh_interval = 300  # 5 minutes
        
    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._monitor_emails)
            self.thread.daemon = True
            self.thread.start()
            
    def stop_monitoring(self):
        self.running = False
        if self.thread:
            self.thread.join()
            
    def _monitor_emails(self):
        while self.running:
            try:
                parser = EmailParser(self.email, self.password)
                new_data = parser.parse_emails(
                    search_criteria=f'(SINCE "{self.last_checked.strftime("%d-%b-%Y")}")' 
                    if self.last_checked else "ALL"
                )
                
                if new_data:
                    self.new_emails.extend(new_data)
                    self.last_checked = datetime.now()
            except Exception as e:
                print(f"Monitoring error: {e}")
            time.sleep(self.refresh_interval)

class EmailParser:
    def __init__(self, email_address, password, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        
    def connect(self):
        """Connect to the IMAP server"""
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        try:
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

  def get_email_body(self, email_message):
    """Improved email body extraction"""
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
                
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
        """Extract Indian Rupee amounts from email body with enhanced debugging"""
        print("\n=== Amount Extraction Debug ===")
        try:
            if not isinstance(email_body, str):
                print(f"Error: Email body is not a string, type: {type(email_body)}")
                return None
            
            print("\nEmail body preview (first 500 chars):")
            print("-" * 50)
            print(email_body[:500])
            print("-" * 50)
            
            patterns = [
                # Flipkart-specific patterns (more precise)
                (r'Amount Payable on Delivery\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Flipkart Delivery Amount"),
                (r'Payment pending:\s*Rs.\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Amazon"),
                (r'Item\(s\) total\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Flipkart Items Total"),
                (r'(?:Total|Grand Total)\s*:\s*₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', "Flipkart Total"),
                (r'₹\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:on delivery|payable)', "Flipkart Contextual Amount"),
                
                # Existing patterns (maintained for compatibility)
                (r'Order Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Order Total Pattern"),
                (r'Paid Via Cash:\s*₹\s*(\d+(?:\.\d{2})?)', "Paid Via Cash Pattern"),
                (r'Item Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Item Total Pattern"),
                (r'Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Basic Total Pattern"),
                (r'[\r\n]₹\s*(\d+(?:\.\d{2})?)', "Newline Rupee Pattern"),
                (r'(?:^|\s)₹\s*(\d+(?:\.\d{2})?)', "Standalone Rupee Pattern"),
                (r'RS\.\s*(?:RS\.|₹)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)', "Rs. Pattern"),
                (r'(?:Amount|Total|Price):\s*₹\s*(\d+(?:\.\d{2})?)', "Generic Amount Pattern"),
                (r'₹\s*(\d+(?:\.\d{2})?)', "Simple Rupee Pattern"),
                (r'Rs\.?\s*(\d+(?:\.\d{2})?)', "Rs Abbreviation Pattern"),
                (r'INR\s*(\d+(?:\.\d{2})?)', "INR Pattern"),
                (r'TOTAL\s*:\s*(?:RS\.|₹)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)', "Total Pattern")
            ]
            
            
            print("\nTesting patterns...")
            for pattern, pattern_name in patterns:
                print(f"\nTrying pattern: {pattern_name}")
                matches = re.findall(pattern, email_body, re.MULTILINE | re.IGNORECASE)
                if matches:
                    print(f"Found matches: {matches}")
                    # Get the largest amount found
                    amount = max(matches, key=lambda x: float(str(x).replace(',', '')))
                    cleaned_amount = re.sub(r'[^\d.]', '', str(amount))
                    print(f"Selected amount: {cleaned_amount}")
                    return cleaned_amount
                else:
                    print("No matches found for this pattern")
            
            print("\nNo amounts found with any pattern")
            return None
            
        except Exception as e:
            print(f"Error in amount extraction: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def parse_emails(self, sender_email=None, folder="INBOX", search_criteria="ALL"):
        """Parse emails with enhanced debugging"""
        print("\n=== Email Parsing Debug ===")
        if not self.connect():
            return []
        
        try:
            print(f"Selecting folder: {folder}")
            self.mail.select(folder)
            
            if sender_email and search_criteria:
                search_string = f'(FROM "{sender_email}") {search_criteria}'
            elif sender_email:
                search_string = f'(FROM "{sender_email}")'
            else:
                search_string = search_criteria
            print(f"Using search string: {search_string}")
            
            _, message_numbers = self.mail.search(None, search_string)
            print(f"Found {len(message_numbers[0].split())} messages")
            
            order_data = []
            
            for num in message_numbers[0].split():
                print(f"\nProcessing email number: {num}")
                try:
                    _, msg_data = self.mail.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    print(f"Subject: {email_message['subject']}")
                    body = self.get_email_body(email_message)
                    
                    if body:
                        print(f"Successfully extracted body, length: {len(body)}")
                        order_amount = self.extract_order_info(body)
                        
                        if order_amount:
                            print(f"Found order amount: {order_amount}")
                            order_data.append({
                                "date": email_message["date"],
                                "subject": email_message["subject"],
                                "sender": email_message["from"],
                                "amount": order_amount,
                            })
                    else:
                        print("Failed to extract email body")
                        
                except Exception as e:
                    print(f"Error processing email: {e}")
                    continue
            
            return order_data
            
        except Exception as e:
            print(f"Error in parse_emails: {e}")
            return []
            
        finally:
            
            self.mail.close()
          
            self.mail.logout()
            

    def save_to_csv(self, order_data, filename="order_data.csv"):
        """Save extracted data to CSV file"""
        if not order_data:
            print("No data to save")
            return
            
        fieldnames = ["date", "subject", "sender", "amount"]
        
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(order_data)
            print(f"Data saved to {filename}")

def makefile():
    # Replace with your email credentials
    email_address = "xyz"
    password = "abc"
  # Use App Password for Gmail
    
    # Specify the sender's email address you want to filter
    sender_to_search = "noreply@swiggy.in"
    
    # Create parser instance
    parser = EmailParser(email_address, password)
    
    # Example: Get emails from the last 30 days
    start_date = datetime.strptime('01-01-2023', '%d-%m-%Y')
    end_date = start_date + timedelta(days=365)
    search_criteria = f'(SINCE "01-Jan-2024" BEFORE "01-Jan-2025")'
    
    print(f"Searching emails from {sender_to_search}...")
    order_data = parser.parse_emails(
        sender_email=sender_to_search,
        search_criteria=search_criteria
    )
    
    if order_data:
        print(f"Found {len(order_data)} emails with order information")
        parser.save_to_csv(order_data)
    else:
        print("No order information found")

makefile()
