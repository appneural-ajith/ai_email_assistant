# AI Personal Email Assistant

## Objective: 
Build an AI-powered personal email assistant capable of reading a user's 
Gmail/IMAP inbox, understanding email context, storing emails in a database, and 
interacting with external tools (web search, Slack, calendar) to assist with email actions. 
The assistant should be able to automatically draft or send replies, forward information, 
and schedule events based on email content.

## Features
- **Day 1-2: Email Parsing & Storage**: Parses Gmail emails and stores them in `emails.db`.
- **Day 3: Context Understanding**: Summarizes email threads and infers intent using BART and DistilBERT.
- **Day 4: Web Search**: Answers email queries with web search results.
- **Day 5: Slack Notifications**: Sends updates to Slack channels.
- **Day 5: Calendar Scheduling**: Detects scheduling intent and creates Google Calendar events.
- **Day 6: Automated Replies**: Drafts and sends email replies, with auto-send for trusted senders and manual confirmation otherwise.

  ## Architecture
### Data Flow
1. **Email Fetching**: `email_parser.py` retrieves emails via Gmail API and stores them in `emails.db`.
2. **Analysis**: `email_analyzer.py` uses LLMs to summarize threads and infer intent.
3. **Actions**: `email_drafter.py` orchestrates:
   - Web searches (`web_search_assistant.py`) for queries.
   - Calendar events (`calendar_scheduler.py`) for scheduling.
   - Slack notifications (`slack_notifier.py`) for updates.
   - Email replies with confirmation or auto-send for safe senders.
4. **External Services**: Managed via `gmail_auth.py` (Gmail/Calendar) and `.env` (Slack).

### Diagram
![diagram](https://github.com/user-attachments/assets/ac28e650-89d5-4f45-b1af-9006156ed699)
- Components: Gmail API → SQLite → LLM (BART/DistilBERT) → Actions (Calendar, Slack, Reply).


#### Components
- **Gmail API**: The entry point, accessed via `services/gmail_auth.py`, fetches emails from the user’s inbox.
- **EmailParser (`services/email_parser.py`)**: Parses email data (sender, subject, body) and stores it in SQLite.
- **SQLite DB (`emails.db`)**: Stores email data for processing and retrieval.
- **EmailAnalyzer (`services/email_analyzer.py`)**: Uses BART for summarization and DistilBERT for intent inference to understand email context.
- **WebSearchAssistant (`services/web_search_assistant.py`)**: Queries the web to answer email questions, invoked by `EmailDrafter`.
- **EmailDrafter (`controllers/email_drafter.py`)**: The central controller, orchestrating analysis and actions (scheduling, notifying, replying).
- **CalendarScheduler (`services/calendar_scheduler.py`)**: Detects scheduling intent and creates events on Google Calendar.
- **SlackNotifier (`services/slack_notifier.py`)**: Sends notifications to Slack channels.
- **Google Calendar**: External service for event scheduling.
- **Slack**: External service for notifications.
- **Gmail Reply**: Sends automated replies via Gmail API.

#### Data Flow
1. **Email Fetching**: The process begins with `EmailParser` fetching emails from the Gmail API and storing them in `emails.db`.
2. **Analysis**: `EmailAnalyzer` retrieves email data from SQLite, summarizes threads, and infers intent (e.g., scheduling request).
3. **Decision & Actions**: `EmailDrafter` processes the analysis:
   - If a query is detected, it invokes `WebSearchAssistant` for answers.
   - If scheduling intent is found, `CalendarScheduler` creates a Google Calendar event.
   - Notifications are sent via `SlackNotifier` to Slack.
   - A reply is drafted and sent via Gmail API, with manual confirmation or auto-send for safe senders.
4. **Output**: Results are reflected in Google Calendar (events), Slack (messages), and Gmail (sent replies).
