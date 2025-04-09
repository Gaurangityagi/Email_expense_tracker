#!/usr/bin/env python
# coding: utf-8

# In[16]:


import imaplib
import email
import csv
import re
from email.header import decode_header
from datetime import datetime, timedelta
import streamlit as st

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
        """Extract email body with detailed debugging"""
        body = ""
        print("\n=== Email Content Debug ===")
        
        if email_message.is_multipart():
            print("Processing multipart email...")
            for part in email_message.walk():
                content_type = part.get_content_type()
                print(f"Found part with content type: {content_type}")
                
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        print(f"Attempting to decode with charset: {charset}")
                        
                        decoded_body = payload.decode(charset)
                        print(f"Successfully decoded part, length: {len(decoded_body)}")
                        print("Preview of decoded content:")
                        print(decoded_body[:200])
                        
                        if content_type == "text/html":
                            # Simple HTML to text conversion
                            decoded_body = re.sub('<[^<]+?>', ' ', decoded_body)
                        
                        body += decoded_body + "\n"
                        
                    except Exception as e:
                        print(f"Error decoding part: {e}")
                        continue
        else:
            print("Processing non-multipart email...")
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or 'utf-8'
                body = payload.decode(charset)
                print(f"Decoded single part email, length: {len(body)}")
            except Exception as e:
                print(f"Error decoding single part email: {e}")
        
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
                (r'Order Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Order Total Pattern"),
                (r'Paid Via Cash:\s*₹\s*(\d+(?:\.\d{2})?)', "Paid Via Cash Pattern"),
                (r'Item Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Item Total Pattern"),
                (r'Total:\s*₹\s*(\d+(?:\.\d{2})?)', "Basic Total Pattern"),
                (r'[\r\n]₹\s*(\d+(?:\.\d{2})?)', "Newline Rupee Pattern"),
                (r'(?:^|\s)₹\s*(\d+(?:\.\d{2})?)', "Standalone Rupee Pattern"),
                (r'RS\.\s*(?:RS\.|₹)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)', "Rs. Pattern"),
                # Flipkart-specific patterns
                (r'Amount Payable on Delivery\s*₹\.\s*(\d+(?:\.\d{2})?)', "Flipkart Delivery Amount"),
                (r'Amount Payable\s*₹\.\s*(\d+(?:\.\d{2})?)', "Flipkart Payable Amount"),
                (r'Item\(s\) total\s*₹\.\s*(\d+(?:\.\d{2})?)', "Flipkart Items Total"),
            
                    r'(?:Amount|Total|Price):\s*₹\s*(\d+(?:\.\d{2})?)',
                    r'Item(s) total\s*Rs.\s*(\d+(?:\.\d{1})?)',
                    r'₹\s*(\d+(?:\.\d{2})?)',
                    r'Rs\.?\s*(\d+(?:\.\d{2})?)',
                    r'INR\s*(\d+(?:\.\d{2})?)',
                    r'TOTAL\s*:\s*(?:RS\.|₹)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)'
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
    email_address = "nanadaime.harshit@gmail.com"
    password = "wxvxlkcmzeevxjuq"
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


# In[17]:


import pandas as pd 
df=pd.read_csv("order_data.csv")


# In[18]:


df.head()


# In[19]:


total=df['amount'].sum()


# In[20]:


total


# In[ ]:




