import imaplib
import email
import csv
import re
from email.header import decode_header


class EmailParser:
    def __init__(self, email_address, password, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def connect(self):
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        try:
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

    def get_email_body(self, email_message):
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type in ["text/plain", "text/html"]:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        decoded = payload.decode(charset)

                        if content_type == "text/html":
                            decoded = re.sub("<[^<]+?>", " ", decoded)

                        body += decoded + "\n"
                    except:
                        continue
        else:
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or "utf-8"
                body = payload.decode(charset)
            except:
                pass

        return body

    # -------------------------------------------------------------------

    def extract_order_info(self, email_body, sender_email=None):
        sender = (sender_email or "").lower()

        if "swiggy" in sender:
            return self._extract_swiggy_amount(email_body)

        if "amazon" in sender:
            return self._extract_amazon_amount(email_body)

        return None

    # -------------------- SWIGGY --------------------

    def _extract_swiggy_amount(self, body):
        print("Extracting Swiggy final total...")

        swiggy_patterns = [
            (r"Paid Via Bank\s*:\s*₹\s*([\d,]+(?:\.\d+)?)", "Paid Via Bank"),
            (r"Order Total\s*:\s*₹\s*([\d,]+(?:\.\d+)?)", "Order Total"),
            (r"Amount Payable\s*:\s*₹\s*([\d,]+(?:\.\d+)?)", "Amount Payable"),
        ]

        return self._match_labeled_amount(body, swiggy_patterns, "Swiggy")

    # -------------------- AMAZON MERGED TOTAL --------------------

    def _extract_amazon_amount(self, body):
        print("Extracting merged Amazon totals...")

        matches = re.findall(
            r"Total\s*₹\s*([\d,]+(?:\.\d+)?)",
            body,
            flags=re.IGNORECASE
        )

        if not matches:
            print("No Amazon totals found.")
            return None

        amounts = []
        for amt in matches:
            try:
                amounts.append(float(amt.replace(",", "")))
            except:
                continue

        merged_total = sum(amounts)

        print(f"Amazon totals found: {amounts} → Merged: {merged_total}")
        return str(merged_total)

    # -------------------- Labeled Amount Matcher --------------------

    def _match_labeled_amount(self, body, patterns, source):
        matches = []

        for regex, label in patterns:
            found = re.findall(regex, body, flags=re.IGNORECASE)
            if found:
                for amt in found:
                    cleaned = amt.replace(",", "")
                    try:
                        matches.append((float(cleaned), label))
                    except:
                        continue

        if not matches:
            print(f"No valid {source} totals found.")
            return None

        final_amount = matches[-1][0]
        print(f"Selected {source} amount: {final_amount}")
        return str(final_amount)

    # -------------------------------------------------------------------

    def parse_emails(self, sender_email=None, folder="INBOX", search_criteria="ALL"):
        if not self.connect():
            return []

        try:
            self.mail.select(folder)

            if sender_email:
                search = f'(FROM "{sender_email}")'
            else:
                search = search_criteria

            _, message_numbers = self.mail.search(None, search)

            order_data = []

            for num in message_numbers[0].split():
                _, msg_data = self.mail.fetch(num, "(RFC822)")
                email_message = email.message_from_bytes(msg_data[0][1])

                sender = email_message.get("from")
                subject = email_message.get("subject", "")
                body = self.get_email_body(email_message)

                if not body:
                    continue

                # Skip cancelled/refund
                text = (subject + " " + body).lower()
                if any(w in text for w in ["cancel", "refunded", "returned", "failed", "declined"]):
                    continue

                amount = self.extract_order_info(body, sender)

                if amount:
                    order_data.append({
                        "date": email_message.get("date"),
                        "subject": subject,
                        "sender": sender,
                        "amount": amount
                    })

            return order_data

        finally:
            self.mail.close()
            self.mail.logout()

    # -------------------------------------------------------------------

    def save_to_csv(self, order_data, filename="order_data.csv"):
        if not order_data:
            print("No data to save.")
            return

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "subject", "sender", "amount"])
            writer.writeheader()
            writer.writerows(order_data)

        print(f"Saved to {filename}")
