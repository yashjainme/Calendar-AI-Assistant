
import os
import datetime
import pytz
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from calendar_utils.google_calendar import check_availability, suggest_time_slots, book_event
from dotenv import load_dotenv

load_dotenv()

# Helper function to add timezone
def add_timezone(time_str):
    if not time_str.endswith('Z') and '+' not in time_str and '-' not in time_str[-6:]:
        return time_str + '+05:30'
    return time_str

# Tool Definitions
@tool
def check_calendar_availability(start_time: str, end_time: str) -> str:
    """Check if a time slot is available in Google Calendar."""
    try:
        start_time, end_time = add_timezone(start_time), add_timezone(end_time)
        is_available = check_availability(start_time, end_time)
        status = "available" if is_available else "already booked"
        return f"The time slot from {start_time} to {end_time} is {status}."
    except Exception as e:
        return f"Error checking availability: {str(e)}"

@tool
def suggest_alternative_time_slots(preferred_date: str, duration_minutes: int) -> str:
    """Suggest alternative time slots if initial request is unavailable."""
    try:
        slots = suggest_time_slots(preferred_date, duration_minutes)
        if not slots:
            return f"Sorry, no available {duration_minutes}-minute slots on {preferred_date}."
        
        # Format slots for display
        readable_slots = []
        for slot in slots:
            try:
                dt = datetime.datetime.fromisoformat(slot)
                ist = pytz.timezone("Asia/Kolkata")
                dt_ist = dt.astimezone(ist)
                readable_slots.append(dt_ist.strftime("%I:%M %p"))
            except:
                readable_slots.append(slot)
        
        return f"Available slots on {preferred_date}: {', '.join(readable_slots)} IST. Any of these work?"
    except Exception as e:
        return f"Error suggesting time slots: {str(e)}"

@tool
def book_calendar_event(title: str, start_time: str, end_time: str, description: str) -> str:
    """Book an event in Google Calendar."""
    try:
        start_time, end_time = add_timezone(start_time), add_timezone(end_time)
        return book_event(title, start_time, end_time, description)
    except Exception as e:
        return f"Error booking event: {str(e)}"

class CalendarBookingAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.state = {"pending_booking": None, "waiting_for_confirmation": False, "waiting_for_title": False}
        
        # Month mappings for parsing
        self.months = {
            'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
            'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
            'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
            'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
            'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
    
    def parse_datetime_from_text(self, text):
        """Parse date, time, and duration from natural language."""
        text_lower = text.lower()
        current_year = datetime.datetime.now().year
        
        # Parse date
        date_str = None
        if "tomorrow" in text_lower:
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            date_str = tomorrow.strftime("%Y-%m-%d")
        elif "today" in text_lower:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        else:
            # Try month patterns
            for month_name, month_num in self.months.items():
                patterns = [
                    rf'(\d{{1,2}})\s*(st|nd|rd|th)?\s*{month_name}',
                    rf'{month_name}\s*(\d{{1,2}})',
                    rf'(\d{{1,2}})\s*{month_name}'
                ]
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        day = f"{int(match.group(1)):02d}"
                        date_str = f"{current_year}-{month_num}-{day}"
                        break
                if date_str:
                    break
        
        # Parse time
        time_str = None
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',  # 5:30 PM
            r'(\d{1,2})\s*(am|pm|AM|PM)',          # 5 PM
            r'(\d{1,2}):(\d{2})',                  # 17:30
            r'(\d{1,2})\s*o\'?clock'               # 5 o'clock
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                hour = int(match.group(1))
                minute = 0
                am_pm = None
                
                # Determine minute and am_pm based on pattern
                if ':' in match.group(0):  # Has minutes
                    if len(match.groups()) >= 2 and match.group(2) and match.group(2).isdigit():
                        minute = int(match.group(2))
                        am_pm = match.group(3) if len(match.groups()) > 2 else None
                    else:
                        am_pm = match.group(2) if len(match.groups()) > 1 else None
                else:  # No minutes specified
                    am_pm = match.group(2) if len(match.groups()) > 1 else None
                
                # Handle AM/PM conversion
                if am_pm:
                    am_pm = am_pm.lower()
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                
                time_str = f"{hour:02d}:{minute:02d}:00"
                break
        
        # Parse duration - improved to handle various formats
        duration = 60  # default
        if re.search(r'30[-\s]*(minute|min)', text_lower):
            duration = 30
        elif re.search(r'90[-\s]*(minute|min)', text_lower):
            duration = 90
        elif re.search(r'1\.5[-\s]*hour', text_lower):
            duration = 90
        elif re.search(r'2[-\s]*hour', text_lower):
            duration = 120
        elif re.search(r'(half|0\.5)[-\s]*hour', text_lower):
            duration = 30
        elif re.search(r'1[-\s]*hour', text_lower):
            duration = 60
        
        return date_str, time_str, duration
    
    def create_datetime_strings(self, date_str, time_str, duration_minutes):
        """Create start and end datetime strings."""
        if not date_str or not time_str:
            return None, None
        
        start_datetime = f"{date_str}T{time_str}"
        dt = datetime.datetime.fromisoformat(start_datetime)
        end_dt = dt + datetime.timedelta(minutes=duration_minutes)
        end_datetime = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        return start_datetime, end_datetime
    
    def process_user_request(self, user_input, chat_history):
        """Main request processing logic."""
        user_input_lower = user_input.lower()
        
        # Handle confirmation state
        if self.state["waiting_for_confirmation"]:
            if any(word in user_input_lower for word in ["yes", "confirm", "book"]):
                return self.execute_booking()
            elif any(word in user_input_lower for word in ["no", "cancel"]):
                self.state.update({"waiting_for_confirmation": False, "pending_booking": None})
                return "Booking cancelled. How else can I help you?"
        
        # Handle title input state
        if self.state["waiting_for_title"]:
            self.state["pending_booking"]["title"] = user_input
            self.state["waiting_for_title"] = False
            return self.confirm_booking()
        
        # Route to appropriate handler
        if any(word in user_input_lower for word in ["book", "schedule", "appointment", "meeting"]):
            return self.handle_booking_request(user_input)
        elif any(word in user_input_lower for word in ["available", "free", "check"]):
            return self.handle_availability_check(user_input)
        else:
            return self.handle_general_query(user_input)
    
    def handle_booking_request(self, user_input):
        """Handle booking requests."""
        date_str, time_str, duration = self.parse_datetime_from_text(user_input)
        
        if not date_str or not time_str:
            return "I need the date and time. Example: 'Book an appointment on July 8th at 5:00 PM for 1 hour'"
        
        start_datetime, end_datetime = self.create_datetime_strings(date_str, time_str, duration)
        if not start_datetime or not end_datetime:
            return "Couldn't parse the date and time. Please try: 'July 8th at 5:00 PM'"
        
        try:
            result = check_calendar_availability.invoke({"start_time": start_datetime, "end_time": end_datetime})
            
            if "available" in result.lower():
                self.state["pending_booking"] = {
                    "start_time": start_datetime, "end_time": end_datetime,
                    "duration": duration, "title": None,
                    "description": f"Appointment booked for {duration} minutes"
                }
                self.state["waiting_for_title"] = True
                return "Great! The time slot is available. What would you like to call this appointment?"
            else:
                alternatives = suggest_alternative_time_slots.invoke({
                    "preferred_date": date_str, "duration_minutes": duration
                })
                return f"Sorry, that time slot is not available. {alternatives}"
                
        except Exception as e:
            return f"I'm having trouble checking the calendar. Please try again. Error: {str(e)}"
    
    def handle_availability_check(self, user_input):
        """Handle availability checks."""
        date_str, time_str, duration = self.parse_datetime_from_text(user_input)
        
        if not date_str or not time_str:
            return "Please specify date and time. Example: 'Check if July 8th at 5:00 PM is available'"
        
        start_datetime, end_datetime = self.create_datetime_strings(date_str, time_str, duration)
        
        try:
            return check_calendar_availability.invoke({"start_time": start_datetime, "end_time": end_datetime})
        except Exception as e:
            return f"I'm having trouble checking the calendar: {str(e)}"
    
    def confirm_booking(self):
        """Confirm booking details with user."""
        booking = self.state["pending_booking"]
        start_dt = datetime.datetime.fromisoformat(booking["start_time"])
        end_dt = datetime.datetime.fromisoformat(booking["end_time"])
        
        confirmation = f"""I'm ready to book your appointment:
- Title: {booking['title']}
- Date: {start_dt.strftime("%A, %B %d, %Y")}
- Time: {start_dt.strftime("%I:%M %p")} - {end_dt.strftime("%I:%M %p")}
- Duration: {booking['duration']} minutes

Should I go ahead and book this appointment? (Yes/No)"""
        
        self.state["waiting_for_confirmation"] = True
        return confirmation
    
    def execute_booking(self):
        """Execute the actual booking."""
        booking = self.state["pending_booking"]
        
        try:
            result = book_calendar_event.invoke({
                "title": booking["title"], "start_time": booking["start_time"],
                "end_time": booking["end_time"], "description": booking["description"]
            })
            
            # Reset state
            self.state.update({"pending_booking": None, "waiting_for_confirmation": False})
            
            trimmed_result = result.split("!")[0].strip() + "!"
            return f"Perfect! Your appointment has been booked successfully. {trimmed_result}"
            
        except Exception as e:
            return f"Sorry, there was an error booking your appointment: {str(e)}"
    
    def handle_general_query(self, user_input):
        """Handle general conversation."""
        current_date = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
        system_prompt = f"""You are a helpful AI assistant for booking appointments in Google Calendar.
Current date: {current_date}

You can help with:
- Booking appointments
- Checking availability  
- Suggesting alternative time slots

Be friendly and conversational. If users ask unrelated questions, politely redirect to calendar tasks."""
        
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception:
            return "I'm here to help you with calendar appointments. How can I assist you today?"

def main():
    """Main function to run the booking agent."""
    agent = CalendarBookingAgent()
    history = []
    
    print("Agent: Hello! I'm your calendar booking assistant. I can help you book appointments, check availability, and manage your calendar. How can I help you today?")

    while True:
        try:
            user_message = input("You: ").strip()
            if user_message.lower() in ["exit", "quit", "bye", "goodbye"]:
                print("Agent: Goodbye! Have a great day!")
                break
            
            if not user_message:
                print("Agent: Please enter a message or type 'exit' to quit.")
                continue
                
            agent_response = agent.process_user_request(user_message, history)
            
            # Update history
            history.extend([f"Human: {user_message}", f"AI: {agent_response}"])
            
            print(f"Agent: {agent_response}")
            
        except KeyboardInterrupt:
            print("\nAgent: Goodbye! Have a great day!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Agent: Sorry, something went wrong. Please try again.")

if __name__ == '__main__':
    main()