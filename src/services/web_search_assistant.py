import sqlite3
import os
from googleapiclient.discovery import build
from gmail_auth import GmailAuthenticator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class WebSearchAssistant:
    """class to integrate web search for answering email queries."""

    def __init__(self, db_path='emails.db'):
        """initialize the database and google custom search credentials"""
        print("Initializing WebSearchAssistant...")
        self.conn = sqlite3.connect(db_path)
        self.service = GmailAuthenticator().get_service()
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.cx = os.getenv('GOOGLE_CX_ID')

        print(f"API key loaded: {'yes' if self.api_key else 'no'}")
        print(f"Custom Search Engine ID loaded: {'yes' if self.cx else 'no'}")

        if not self.api_key or not self.cx:
            raise ValueError("Google API key and Custom Search Engine ID must be set in environment variables.")
        # initialize the search service
        self.search_service = build("customsearch", "v1", developerKey=self.api_key)   

    def get_email_content(self, email_id):
        """retreive email body from the database"""
        c = self.conn.cursor()
        c.execute("SELECT subject, body FROM emails WHERE ID=?", (email_id,))   
        result = c.fetchone()
        if result:
            return {'subject': result[0], 'body': result[1]}
        print(f"Email with ID {email_id} not found in the database.")
        return None

    def search_web(self, query, num_results=3):
        """perform a web search and return filtered results"""
        print(f"Searching the web for query: {query}")
        response = self.search_service.cse().list(
            q=query,
            cx=self.cx,
            num=num_results
        ).execute()

        results = []
        for item in response.get('items', []):
            results.append({
                'title': item['title'],
                'snippet': item['snippet'],
                'link': item['link']
            })
        return results
    
    def process_email_query(self, email_id):
        """analyze email content and search the web if needed"""
        print(f"Processing email with ID: {email_id}")
        email = self.get_email_content(email_id)
        if not email:
            return "Email not found."
        body = email['body']
        subject = email['subject']
        print(f"Email subject: {subject}")
        print(f"Email body: {body[:100]}")

        # Check if the email body contains a question or query
        if '?' in body or 'what' in body.lower() or 'how' in body.lower():
            query = f"{subject} {body[:100]}"
            search_results = self.search_web(query)

            response = f"email query detected:\nsubject: {subject}\nbody snippet: {body[:100]}...\n\nsearch results:\n"
            for i, result in enumerate(search_results, 1):
                response += f"{i}. {result['title']}\n{result['snippet']}\n {result['link']}\n\n"
            print(response)
            return response
        result =  "No query detected in the email body."
        print(result)
        return result
    
    def close(self):
        """close the database connection"""
        self.conn.close()

if __name__ == "__main__":
    assistant = WebSearchAssistant()
    email_id = "195fafee3c89c982"
    assistant.process_email_query(email_id)
    assistant.close()
      