
import streamlit as st
import requests
import os
from datetime import datetime, timedelta

# --- Configuration ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/chat")

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Calendar AI Assistant",
    page_icon="📅",
    layout="centered"
)

st.title("📅 Calendar AI Assistant")
st.caption("I can help you book meetings. Try asking: 'Book an appointment on July 8th at 5:00 PM for 1 hour'")

# --- Session State Initialization ---
# 'messages' will store the chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you schedule an event today?"}
    ]

# Initialize prompt state if it doesn't exist
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""

# --- Helper Functions ---
def get_default_datetime():
    """Get a default datetime for tomorrow at 5:00 PM"""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)

def format_datetime_for_prompt(dt):
    """Format datetime for the prompt"""
    return dt.strftime("%B %d at %I:%M %p")

def send_message_to_backend(prompt):
    """Send message to backend and handle response"""
    # Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare request for the backend
    history_for_api = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages[:-1] # Exclude the latest user message
    ]
    
    payload = {
        "message": prompt,
        "history": history_for_api
    }

    # Get response from the backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(BACKEND_URL, json=payload, timeout=120)
                response.raise_for_status()
                
                assistant_response = response.json().get("response")
                st.markdown(assistant_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})

            except requests.exceptions.RequestException as e:
                error_message = f"Sorry, I couldn't connect to the backend. Please make sure it's running. Error: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# --- Quick Action Buttons ---
st.markdown("### Quick Actions")
col1, col2 = st.columns(2)

with col1:
    if st.button("📅 Schedule 1 Hour Meeting", use_container_width=True):
        default_dt = get_default_datetime()
        st.session_state.current_prompt = f"Book an appointment on {format_datetime_for_prompt(default_dt)} for 1 hour"
        st.rerun()

with col2:
    if st.button("⏰ Schedule 30 Min Meeting", use_container_width=True):
        default_dt = get_default_datetime()
        st.session_state.current_prompt = f"Book an appointment on {format_datetime_for_prompt(default_dt)} for 30 minutes"
        st.rerun()

st.markdown("---")

# --- UI Rendering ---

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input Handling ---
# Use a form with text input that supports pre-population
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    
    with col1:
        prompt = st.text_input(
            "What would you like to do?",
            value=st.session_state.current_prompt,
            placeholder="Type your message here...",
            label_visibility="collapsed"
        )
    
    with col2:
        submit_button = st.form_submit_button("Send", use_container_width=True)
    
    if submit_button and prompt:
        # Clear the current prompt after using it
        st.session_state.current_prompt = ""
        send_message_to_backend(prompt)
        st.rerun()