import os
import sqlite3
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from email_analyzer import EmailAnalyzer

# Load environment variables from .env file
load_dotenv()

class SlackNotifier:
    """Class to send email notifications to Slack."""

    def __init__(self, db_path='emails.db', channel='#general'):
        """initialize the database and Slack client"""
        print("Initializing SlackNotifier...")
        self.conn = sqlite3.connect(db_path)
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not self.slack_token:
            raise ValueError("Slack Bot Token must be set in environment variables.")
        self.client = WebClient(token=self.slack_token)
        self.channel = channel
        self.email_analyzer = EmailAnalyzer(db_path=db_path)

    def get_email_details(self, email_id):
        """retrieve email details from the database"""
        c = self.conn.cursor()
        c.execute("SELECT sender, subject, body FROM emails WHERE id= ?", (email_id,))
        result = c.fetchone()
        if result:
            return {
                'sender': result[0],
                'subject': result[1],
                'body': result[2]
            }
        print(f"Email with ID {email_id} not found in the database.")
        return None
    
    def is_important(self, email):
        """check if the email is important"""
        important_senders = ['@indeed.com', '@linkedin.com']
        important_keywords = ['urgent', 'important', 'meeting', 'deadline', 'action required']
        
        sender = email['sender'].lower()
        subject = email['subject'].lower()

        return any(s in sender for s in important_senders) or any(k in subject for k in important_keywords)
    
    def send_slack_message(self, email_id):
        """send a slack message with email details"""
        email = self.get_email_details(email_id)
        if not email:
            return False
        
        # check if the email is important
        if not self.is_important(email):
            print(f"Email {email_id} not deemed important. skipping slack notification.")
            return False
        
        # get summary and intent from emailanalyzer
        summary = self.analyzer.summarize_thread(email_id)
        intent = self.analyzer.infer_intent(email_id)

        # construct the message
        message = (
            f"New Important Email Received!\n"
            f"From: {email['sender']}\n"
            f"Subject: {email['subject']}\n"
            f"Summary: {summary}\n"
            f"Intent: {intent}\n"
            f"Body: {email['body'][:200]}..."
        )

        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message
            )
            print(f"Message sent to Slack channel {self.channel} for email {email_id}")
            return True
        except SlackApiError as e:
            print(f"Error sending message to Slack: {e.response['error']}")
            return False
        
    def close(self):
        """close the database connection"""
        self.conn.close()
        print("SlackNotifier closed.")

if __name__ == "__main__":
    notifier = SlackNotifier(channel='#general')
    email_id = '195fafee3c89c982'  
    notifier.send_slack_message(email_id)
    notifier.close()
        