# Conversational AI Calendar Assistant

This project is a full-stack conversational AI assistant that helps users book appointments in a Google Calendar through a natural chat interface.

## Features

-   **Web-Based Chat:** A simple and intuitive chat interface built with Streamlit.
-   **Natural Language Understanding:** Powered by Google's Gemini Pro model via Langchain.
-   **Function Calling:** The AI agent can interact with a Google Calendar to:
    -   Check for availability.
    -   Suggest alternative time slots.
    -   Book confirmed appointments.
-   **Google Calendar Integration:** Uses a Service Account for secure, server-to-server interaction with the Google Calendar API (no user OAuth required).
-   **Robust Backend:** Built with FastAPI to handle API requests efficiently.

## Project Structure
```
.
├── backend/
│ └── main.py # FastAPI backend server
├── frontend/
│ └── streamlit_app.py # Streamlit chat frontend
├── agent/
│ └── agent.py # Langchain agent logic and tool definitions
├── calendar_utils/
│ └── google_calendar.py # Google Calendar API integration functions
├── .env.example # Example environment variables file
├── credentials.json # Placeholder for your Google Service Account key
├── requirements.txt # Python dependencies
└── README.md # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- A Google Cloud Platform (GCP) project with Google Calendar API enabled
- A Google Calendar that is shared with the provided service account

### 2. Google Calendar Configuration

1. **Enable the Google Calendar API:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Select your project.
    - Navigate to **APIs & Services** > **Library**.
    - Search for **Google Calendar API** and enable it.

2. **Share Your Google Calendar:**
    - Go to [Google Calendar](https://calendar.google.com/).
    - Open settings for the calendar you want to connect.
    - Under **"Share with specific people or groups"**, add the **client email** from the provided `credentials.json`.
    - Grant **"Make changes to events"** permission.

> ✅ The `credentials.json` file should already be placed in the root directory.

### 3. Project Installation

1. **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3. **Set up environment variables:**
    - Create a `.env` file in the root directory.
    - Use the `.env.example` as a starting point.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to your Service Account credentials JSON (e.g. `credentials.json`) |
| `GOOGLE_CALENDAR_ID` | ID of the calendar to manage (found under “Integrate calendar” in calendar settings) |
| `BACKEND_URL` | URL where the FastAPI backend is hosted (e.g. `http://localhost:8000/chat`) |

> 💡 Example `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
GOOGLE_CALENDAR_ID=your_calendar_id@group.calendar.google.com
BACKEND_URL=http://localhost:8000/chat
```
### 4. Running the Application

You need to run the backend and frontend servers in separate terminal windows.

1.  **Start the Backend Server:**
    ```bash
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The backend will be available at `http://localhost:8000`.

2.  **Start the Frontend Application:**
    (In a new terminal, with the virtual environment activated)
    ```bash
    streamlit run frontend/streamlit_app.py
    ```
    The frontend will open in your browser, usually at `http://localhost:8501`.