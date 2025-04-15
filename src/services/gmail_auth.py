import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class GmailAuthenticator:
    """Class to handle Gmail API authentication."""

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/calendar.events'
    ]

    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        """Initialize with paths to credentials and token files."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google API and store credentials."""
        creds = None
        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except ValueError as e:
                print(f"Invalid token.json: {e}. Regenerating...")
                os.remove(self.token_path)  # Remove invalid token

        # If no valid credentials, refresh or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                flow.oauth2session.params['access_type'] = 'offline'  # Ensure refresh_token
                flow.oauth2session.params['prompt'] = 'consent'       # Force consent screen
                creds = flow.run_local_server(port=8080)  
                # Save the credentials for future use
                print("Authentication completed, saving token...")
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
        
        # Store the credentials
        self.creds = creds
        # Build and store the default Gmail service
        self.service = build('gmail', 'v1', credentials=self.creds)

    def get_service(self, service_name='gmail', version='v1'):
        """Return a Google API service instance for the specified service and version."""
        return build(service_name, version, credentials=self.creds)

if __name__ == '__main__':
    auth = GmailAuthenticator()
    service = auth.get_service()
    print("Authentication successful!")
