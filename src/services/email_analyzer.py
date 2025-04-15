import sqlite3
import base64
from transformers import pipeline
# from gmail_auth import GmailAuthenticator

class EmailAnalyzer:
    """class to analyze email content using Hugging Face Transformers."""

    def __init__(self, authenticator, db_path='emails.db', model_name='distilbert-base-uncased'):
        """Initialize the EmailAnalyzer with a database path and model name."""
        """initalize database connection and llm pipeline"""
        self.conn = sqlite3.connect(db_path)
        self.service = authenticator.get_service()
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn", framework="pt")
        self.classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english", framework="pt")

    def get_thread_context(self, thread_id):
        """retrieve all emails in a thread from the database"""
        c = self.conn.cursor()
        c.execute("SELECT sender, subject, body FROM emails WHERE THREAD_ID = ? ORDER BY timestamp", (thread_id,))
        emails = c.fetchall()
        return [{'sender': e[0], 'subject': e[1], 'body': e[2]} for e in emails]
    
    def summarize_thread(self, thread_id):
        """summarizes the content of an email thread"""
        thread_emails = self.get_thread_context(thread_id)
        if not thread_emails:
            return "No emails found in thread."
        
        # combine email bodies for summarization'
        combined_text = " ".join(email['body'] for email in thread_emails if email['body'])
        if not combined_text:
            return "No content available for summarization."
        
        # summarize the combined text
        max_length = 1024
        truncated_text = combined_text[:max_length]
        summary = self.summarizer(truncated_text, max_length=130, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    
    def infer_intent(self, email_id):
        """infer the sender's intent from an email"""
        c = self.conn.cursor()
        c.execute("SELECT body FROM emails WHERE id=?", (email_id,))
        result = c.fetchone()
        if not result or not result[0]:
            return "No content available for intent inference."
        
        body = result[0][:512] # truncate for model limits
        # simple intent classification (positive/negative)
        intent = self.classifier(body)
        label = intent[0]['label']
        if label == "POSITIVE":
            return "Likely a confirmation or positive response."
        elif label == "NEGATIVE":
            return "Likely a rejection or negative response."
        return "Intent unclear."
    
    def analyze_and_report(self, thread_id, email_id=None):
        """generate a report with summary and intent"""
        summary = self.summarize_thread(thread_id)
        intent = self.infer_intent(email_id) if email_id else "Not specified."
        report = f"Thread Summary (Thread ID: {thread_id}):\n{summary}\n\nIntent (Email ID: {email_id}):\n{intent}"
        print(report)
        return report
    
    def close(self):
        """close the database connection"""
        self.conn.close()


if __name__ == "__main__":
    from gmail_auth import GmailAuthenticator
    authenticator = GmailAuthenticator()
    analyzer = EmailAnalyzer(authenticator)
    thread_id = '195f60b397c7396d'
    email_id = '195f60b397c7396d'
    analyzer.analyze_and_report(thread_id, email_id)
    analyzer.close()
