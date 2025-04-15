import sqlite3
from datetime import datetime, timedelta
from services.email_analyzer import EmailAnalyzer

class CalendarScheduler:
    """Class to schedule events on Google Calendar based on email content."""

    def __init__(self, authenticator, db_path='emails.db'):
        """Initialize with database, Calendar service, and LLM analyzer."""
        print("Initializing CalendarScheduler...")
        self.conn = sqlite3.connect(db_path)
        self.service = authenticator.get_service('calendar', 'v3')  # Use shared authenticator
        self.analyzer = EmailAnalyzer(authenticator, db_path=db_path)  # Pass authenticator

    def get_email_content(self, email_id):
        """Retrieve email content from the database."""
        c = self.conn.cursor()
        c.execute("SELECT sender, subject, body FROM emails WHERE id = ?", (email_id,))
        result = c.fetchone()
        if result:
            return {'sender': result[0], 'subject': result[1], 'body': result[2]}
        print(f"Email {email_id} not found in database.")
        return None

    def detect_scheduling_intent(self, email_id):
        """Use LLM to detect scheduling intent and extract event details."""
        email = self.get_email_content(email_id)
        if not email:
            return None

        body = email['body']
        # Simple heuristic + LLM enhancement
        scheduling_keywords = ['meeting', 'call', 'schedule', 'on', 'at', 'next']
        if not any(kw in body.lower() for kw in scheduling_keywords):
            return None

        # Use LLM to extract structured details
        prompt = (
            f"Analyze this email body and extract meeting details if present:\n"
            f"{body}\n\n"
            f"Return in this format: Title: [title], Date: [YYYY-MM-DD], Time: [HH:MM] (24h). "
            f"If no clear details, suggest defaults."
        )
        summary = self.analyzer.summarizer(body, max_length=100, min_length=30, do_sample=False)[0]['summary_text']
        
        # Dummy parsing (enhance with LLM or regex for production)
        title = email['subject'] if 'meeting' in body.lower() else f"Meeting from {email['sender']}"
        date = datetime.now().strftime('%Y-%m-%d')  # Default to today
        time = '10:00'  # Default morning meeting
        for line in body.split('\n'):
            if 'on' in line.lower():
                if 'friday' in line.lower():
                    date = (datetime.now() + timedelta(days=(4 - datetime.now().weekday()) % 7)).strftime('%Y-%m-%d')
                if 'at' in line.lower():
                    time_str = line.split('at')[-1].strip().lower()
                    if 'pm' in time_str:
                        hour = int(time_str.split('pm')[0].strip()) + 12  # Convert PM to 24h
                        time = f"{hour:02d}:00"
                    elif 'am' in time_str:
                        hour = int(time_str.split('am')[0].strip())
                        time = f"{hour:02d}:00"
                    else:
                        time = time_str[:5]  # Fallback for "HH:MM"

        event_details = {'title': title, 'date': date, 'time': time}
        print(f"Detected scheduling intent: {event_details}")
        return event_details

    def create_calendar_event(self, email_id):
        """Create a Google Calendar event from email details."""
        event_details = self.detect_scheduling_intent(email_id)
        if not event_details:
            print(f"No scheduling intent detected for email {email_id}.")
            return False

        # Format start and end times correctly for Google Calendar API
        start_time = f"{event_details['date']}T{event_details['time']}:00"
        end_time = (datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')

        event = {
            'summary': event_details['title'],
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata'  # Adjust to your timezone
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Kolkata'
            }
        }

        try:
            event_result = self.service.events().insert(calendarId='primary', body=event).execute()
            print(f"Event created: {event_result.get('htmlLink')}")
            return True
        except Exception as e:
            print(f"Error creating event: {e}")
            return False

    def close(self):
        """Close the database connection and analyzer."""
        self.conn.close()
        self.analyzer.close()

if __name__ == '__main__':
    from gmail_auth import GmailAuthenticator  # Import for standalone testing
    authenticator = GmailAuthenticator()  # Create instance for testing
    scheduler = CalendarScheduler(authenticator)  # Pass authenticator
    email_id = '1960ff6580cb6e25'
    scheduler.create_calendar_event(email_id)
    scheduler.close()