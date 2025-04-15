import base64
import logging
from email.mime.text import MIMEText
from services.gmail_auth import GmailAuthenticator
from services.calendar_scheduler import CalendarScheduler
from services.email_analyzer import EmailAnalyzer

# Set up logging
logging.basicConfig(filename='replies.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

class EmailDrafter:
    """Class to draft and send automated email replies."""

    def __init__(self, db_path='emails.db'):
        """Initialize with Gmail service, Calendar scheduler, and LLM analyzer."""
        print("Initializing EmailDrafter...")
        self.authenticator = GmailAuthenticator()
        self.service = self.authenticator.get_service('gmail', 'v1')
        self.scheduler = CalendarScheduler(self.authenticator, db_path=db_path)
        self.analyzer = EmailAnalyzer(self.authenticator ,db_path=db_path)
        self.safe_senders = ['ajithpspk123@gmail.com']  # Whitelist for auto-send

    def get_email_details(self, email_id):
        """Retrieve email details from the database."""
        return self.scheduler.get_email_content(email_id)

    def should_reply(self, email_id):
        """Determine if the email warrants an automated reply."""
        email = self.get_email_details(email_id)
        if not email:
            return False
        intent = self.analyzer.infer_intent(email_id)
        return 'request' in intent.lower() or 'meeting' in email['body'].lower()

    def draft_reply(self, email_id):
        """Draft a reply using LLM based on email content."""
        email = self.get_email_details(email_id)
        if not email:
            return None

        # Check for scheduling request and book event
        event_booked = self.scheduler.create_calendar_event(email_id)
        meeting_details = self.scheduler.detect_scheduling_intent(email_id) if event_booked else None

        # Prepare LLM prompt
        prompt = (
            f"Draft a polite email reply to this email:\n"
            f"From: {email['sender']}\nSubject: {email['subject']}\nBody: {email['body']}\n\n"
            f"Context: "
        )
        if meeting_details:
            prompt += (
                f"A meeting was scheduled for {meeting_details['date']} at {meeting_details['time']} "
                f"(Asia/Kolkata). Propose this time in the reply."
            )
        else:
            prompt += "No specific action detected; provide a general acknowledgment."
        prompt += "\nKeep it concise and professional."

        # Use LLM to generate reply (BART summarizer as placeholder)
        reply_text = self.analyzer.summarizer(prompt, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
        
        return {
            'to': email['sender'],
            'subject': f"Re: {email['subject']}",
            'body': reply_text
        }

    def send_reply(self, email_id, auto_send=False):
        """Send the drafted reply via Gmail API with safeguards."""
        draft = self.draft_reply(email_id)
        if not draft:
            print(f"No draft generated for email {email_id}.")
            return False

        # Log the draft
        log_msg = f"Draft for {email_id}: To: {draft['to']}, Subject: {draft['subject']}, Body: {draft['body']}"
        logging.info(log_msg)
        print(log_msg)

        # Check if auto-send is safe
        email = self.get_email_details(email_id)
        if auto_send and email['sender'] in self.safe_senders:
            message = MIMEText(draft['body'])
            message['to'] = draft['to']
            message['subject'] = draft['subject']
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            try:
                self.service.users().messages().send(
                    userId='me', body={'raw': raw_message}
                ).execute()
                print(f"Reply sent to {draft['to']} for email {email_id}.")
                logging.info(f"Sent reply for {email_id} to {draft['to']}.")
                return True
            except Exception as e:
                print(f"Error sending reply: {e}")
                return False
        else:
            # Require confirmation
            confirmation = input(f"Send this reply? (y/n): {draft['body']}\n> ")
            if confirmation.lower() == 'yes' or confirmation.lower() == 'y':
                message = MIMEText(draft['body'])
                message['to'] = draft['to']
                message['subject'] = draft['subject']
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                
                try:
                    self.service.users().messages().send(
                        userId='me', body={'raw': raw_message}
                    ).execute()
                    print(f"Reply sent to {draft['to']} for email {email_id}.")
                    logging.info(f"Sent reply for {email_id} to {draft['to']} (confirmed).")
                    return True
                except Exception as e:
                    print(f"Error sending reply: {e}")
                    return False
            else:
                print("Reply not sent (user declined).")
                return False

    def close(self):
        """Close resources."""
        self.scheduler.close()
        self.analyzer.close()

if __name__ == '__main__':
    drafter = EmailDrafter()
    email_id = '1960ff6580cb6e25'
    if drafter.should_reply(email_id):
        drafter.send_reply(email_id, auto_send=False)  # Set to True for safe senders
    else:
        print(f"No reply needed for email {email_id}.")
    drafter.close()
