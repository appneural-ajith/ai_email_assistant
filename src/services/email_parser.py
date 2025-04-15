import base64
import sqlite3
from datetime import datetime
from services.gmail_auth import GmailAuthenticator
import html2text

class EmailManager:
    def __init__(self, db_path='emails.db'):
        self.conn = sqlite3.connect(db_path)
        self.setup_database()

    def setup_database(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS emails (
                     id TEXT PRIMARY KEY,
                     thread_id TEXT,
                     sender TEXT,
                     recipient TEXT,
                     subject TEXT,
                     timestamp INTEGER,
                     body TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS attachments (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     message_id TEXT,
                     filename TEXT,
                     mime_type TEXT,
                     size INTEGER,
                     FOREIGN KEY (message_id) REFERENCES emails(id))''')
        self.conn.commit()

    def parse_email(self, service, message):
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        headers = msg['payload']['headers']

        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        recipient = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        timestamp = int(msg.get('internalDate', 0)) // 1000
        thread_id = msg.get('threadId', message['id'])

        # Parse body with recursive part traversal
        def extract_body(payload):
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                    elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                        html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        body = html2text.html2text(html_content)
                        break
                    elif 'parts' in part:  # Nested parts (e.g., multipart/alternative)
                        body = extract_body(part)
                        if body:
                            break
            elif 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
            return body

        body = extract_body(msg['payload'])

        attachments = []
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if 'filename' in part and part['filename']:
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': int(part['body'].get('size', 0))
                    })

        return {
            'id': message['id'],
            'thread_id': thread_id,
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'timestamp': timestamp,
            'body': body,
            'attachments': attachments
        }

    def store_email(self, email):
        c = self.conn.cursor()
        c.execute('''INSERT OR REPLACE INTO emails (id, thread_id, sender, recipient, subject, timestamp, body)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (email['id'], email['thread_id'], email['sender'], email['recipient'],
                   email['subject'], email['timestamp'], email['body']))
        for attachment in email['attachments']:
            c.execute('''INSERT INTO attachments (message_id, filename, mime_type, size)
                         VALUES (?, ?, ?, ?)''',
                      (email['id'], attachment['filename'], attachment['mime_type'], attachment['size']))
        self.conn.commit()

    def fetch_and_store_emails(self, service, max_results=10):
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        for message in messages:
            email = self.parse_email(service, message)
            self.store_email(email)
            self.print_email(email)

    def print_email(self, email):
        print(f"ID: {email['id']}")
        print(f"Thread ID: {email['thread_id']}")
        print(f"From: {email['sender']}")
        print(f"To: {email['recipient']}")
        print(f"Subject: {email['subject']}")
        print(f"Timestamp: {datetime.fromtimestamp(email['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Body: {email['body'][:100]}...")
        if email['attachments']:
            print("Attachments:")
            for att in email['attachments']:
                print(f" - {att['filename']} ({att['mime_type']}, {att['size']} bytes)")
        print()

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    auth = GmailAuthenticator()
    service = auth.get_service()
    email_manager = EmailManager()
    email_manager.fetch_and_store_emails(service)
    email_manager.close()