import os
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from pytz import utc


# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# --- Google Calendar API Setup ---
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Initializes and returns the Google Calendar service object."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except FileNotFoundError:
        print(f"Error: The service account key file '{SERVICE_ACCOUNT_FILE}' was not found.")
        print("Please make sure the GOOGLE_SERVICE_ACCOUNT_FILE environment variable is set correctly.")
        return None
    except Exception as e:
        print(f"An error occurred during authentication: {e}")
        return None

# --- Calendar Functions ---

def check_availability(start_time: str, end_time: str) -> bool:
    """
    Checks if a given time range is free in the calendar.

    Args:
        start_time (str): The start time in ISO 8601 format (e.g., '2024-07-28T10:00:00-07:00').
        end_time (str): The end time in ISO 8601 format (e.g., '2024-07-28T11:00:00-07:00').

    Returns:
        bool: True if the time slot is available, False otherwise.
    """
    service = get_calendar_service()
    if not service or not CALENDAR_ID:
        return False

    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return not events
    except HttpError as error:
        print(f'An error occurred: {error}')
        return False

def suggest_time_slots(preferred_date: str, duration_minutes: int) -> list[str]:
    """
    Suggests available time slots on a given day.

    Args:
        preferred_date (str): The preferred date in 'YYYY-MM-DD' format.
        duration_minutes (int): The desired duration of the meeting in minutes.

    Returns:
        list[str]: A list of available start times in ISO 8601 format.
    """
    service = get_calendar_service()
    if not service or not CALENDAR_ID:
        return []

    try:
        # Make timezone-aware start and end of working hours
        day_start = utc.localize(datetime.datetime.fromisoformat(f"{preferred_date}T09:00:00"))
        day_end = utc.localize(datetime.datetime.fromisoformat(f"{preferred_date}T17:00:00"))

        # Get events on that date
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # Process events and collect free time slots
        free_slots = []
        current_time = day_start
        meeting_duration = datetime.timedelta(minutes=duration_minutes)

        for event in events:
            event_start_str = event['start'].get('dateTime')
            event_end_str = event['end'].get('dateTime')
            event_start = datetime.datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
            event_end = datetime.datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))

            if current_time + meeting_duration <= event_start:
                free_slots.append(current_time.isoformat())

            current_time = max(current_time, event_end)

        # After last event
        while current_time + meeting_duration <= day_end:
            free_slots.append(current_time.isoformat())
            current_time += datetime.timedelta(minutes=30)

        return free_slots[:5]  # Limit suggestions

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []
    except Exception as e:
        print(f"An unexpected error occurred in suggest_time_slots: {e}")
        return []


def book_event(title: str, start_time: str, end_time: str, description: str) -> str:
    """
    Books an event in the Google Calendar.

    Args:
        title (str): The title of the event.
        start_time (str): The start time in ISO 8601 format.
        end_time (str): The end time in ISO 8601 format.
        description (str): A description for the event.

    Returns:
        str: A confirmation message with the event link, or an error message.
    """
    service = get_calendar_service()
    if not service or not CALENDAR_ID:
        return "Error: Could not connect to calendar service."

    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
    }

    try:
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return f"Event created successfully! View it here: {created_event.get('htmlLink')}"
    except HttpError as error:
        print(f'An error occurred: {error}')
        return f"Failed to create event. Reason: {error}"

# if __name__ == '__main__':
#     print("--- Testing Calendar Functions ---")

#     # Use July 8, 2025 - 5:00 AM to 6:00 AM UTC
#     test_start = '2025-07-08T05:00:00Z'
#     test_end = '2025-07-08T06:00:00Z'
    
#     # Test availability check
#     is_available = check_availability(test_start, test_end)
#     print(f"Is {test_start} to {test_end} available? {is_available}")

#     # Test time slot suggestions for that day (from 9:00 AM to 5:00 PM local)
#     suggestions = suggest_time_slots('2025-07-08', 60)
#     print(f"Suggested 60-min slots for 2025-07-08: {suggestions}")

#     # Test booking an event at 5:00 AM to 6:00 AM (UTC)
#     confirmation = book_event(
#         title="Test Meeting from Script",
#         start_time=test_start,
#         end_time=test_end,
#         description="This is a test event created by the script for July 8, 2025 at 5AM."
#     )
#     print(confirmation)
