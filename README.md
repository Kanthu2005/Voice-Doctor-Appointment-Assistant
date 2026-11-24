# Voice Doctor Appointment Assistant

A real-time voice-based doctor appointment booking system built with Pipecat (Python) for the voice pipeline and React + Vite + Tailwind CSS for the frontend dashboard.

## Features

### Voice Pipeline (Pipecat)
- Real-time voice interaction with STT → LLM → TTS pipeline
- Function calling for:
  - Check doctor availability
  - Book appointments
  - Cancel appointments
- Caller identified only by phone number spoken during the call
- Natural language conversation flow

### Frontend Dashboard
- Clean, professional interface
- Doctor availability listing with specialties and time slots
- Real-time appointments list with status updates
- Interactive call interface with:
  - Phone-style call screen (ringing/connecting/connected/ended states)
  - Live transcript display
  - Call timer
  - Mute/End call buttons
- Responsive design (mobile-friendly)

## Tech Stack

### Backend
- **Framework**: Pipecat + FastAPI
- **STT**: ElevenLabs (or OpenAI Whisper)
- **LLM**: Google Gemini (with function calling)
- **TTS**: ElevenLabs
- **VAD**: Silero VAD (bonus)
- **Data**: JSON file storage (can be swapped for SQLite)

### Frontend
- **Framework**: React + Vite + TypeScript
- **Styling**: Tailwind CSS
- **State**: React Context API

## Project Structure

```
voice-doctor-assistant/
├── backend/
│   ├── main.py              # FastAPI REST API
│   ├── bot.py               # Pipecat voice pipeline
│   ├── database.py          # Data layer (JSON file)
│   ├── data/
│   │   └── db.json          # Mock data (doctors, slots, appointments)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main app component
│   │   ├── AppContext.tsx   # Global state management
│   │   ├── main.tsx         # Entry point
│   │   ├── components/
│   │   │   ├── CallModal.tsx      # Phone-style call interface
│   │   │   ├── DoctorsList.tsx    # Doctors availability display
│   │   │   └── AppointmentsList.tsx # Appointments display
│   │   └── index.css        # Tailwind imports
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── .env.example
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- ElevenLabs API key (for STT/TTS)
- Google Gemini API key (for LLM)

### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file from example:
   ```bash
   cp ../.env.example .env
   # Edit .env and add your API keys
   ```

5. Start the FastAPI server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

6. (Optional) Start the Pipecat voice pipeline:
   ```bash
   python bot.py
   ```

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:5175 in your browser

## Environment Variables

Create a `.env` file in the backend directory with:

```env
ELEVENLABS_API_KEY=your_elevenlabs_api_key
GEMINI_API_KEY=your_gemini_api_key
# OPENAI_API_KEY=your_openai_api_key  # Alternative LLM
```

## API Endpoints

### GET `/api/doctors`
Returns list of all doctors with their available slots.

### GET `/api/availability?doctor_name=...&date=...`
Returns available slots for a specific doctor and/or date.

### GET `/api/appointments`
Returns all appointments (active and cancelled).

### POST `/api/book`
Books an appointment.
```json
{
  "phone_number": "+15551234567",
  "doctor_name": "Dr. Sarah Smith",
  "slot": "2026-11-25 10:00 AM"
}
```

### POST `/api/cancel`
Cancels an appointment by phone number.
```json
{
  "phone_number": "+15551234567"
}
```

## Voice Pipeline Architecture

The Pipecat pipeline follows this flow:

```
Caller Audio → VAD → STT (ElevenLabs) → LLM (Gemini) → TTS (ElevenLabs) → Caller Audio
```

The LLM has three registered functions:
1. `check_doctor_availability(doctor_name, date?)` - Returns available slots
2. `book_appointment(phone_number, doctor_name, slot)` - Books appointment after confirming phone number
3. `cancel_appointment(phone_number)` - Cancels existing appointment

### System Prompt
The LLM is instructed to:
- Identify callers ONLY by phone number spoken during the call
- Read back the phone number to confirm before booking/cancelling
- Speak naturally and handle all three actions end-to-end

## Mock Data

The system comes with pre-configured mock data:
- **Dr. Sarah Smith** - General Practitioner
- **Dr. Michael Chen** - Cardiologist  
- **Dr. Emily Rodriguez** - Pediatrician

Each doctor has 3 available time slots across Nov 25-26, 2026.

## Development

### Running Tests
```bash
# Backend
cd backend && python -m pytest

# Frontend
cd frontend && npm test
```

### Building for Production
```bash
# Frontend
cd frontend && npm run build
```

## Submission Requirements

This project fulfills the SDE Intern Round 1 Assignment requirements:

1. ✅ GitHub repository with complete code
2. ✅ README with run instructions
3. ✅ `.env.example` file (no API keys committed)
3. ✅ Voice pipeline with Pipecat, ElevenLabs STT/TTS, Gemini LLM
4. ✅ Frontend dashboard with call interface, transcript, doctors list, appointments
5. ✅ Phone-style call screen with states, timer, mute, end-call
6. ✅ Live transcript, audio waveform (visual)
7. ✅ Doctor availability and appointment management

## Pipeline Description

The voice pipeline uses Pipecat to orchestrate real-time audio processing:
1. **VAD (Voice Activity Detection)**: Detects when the caller is speaking
2. **STT (Speech-to-Text)**: ElevenLabs converts audio to text
3. **LLM (Language Model)**: Google Gemini processes the text with function calling
4. **TTS (Text-to-Speech)**: ElevenLabs converts LLM response to audio
5. **Transport**: WebSocket for browser integration

The LLM has three function-calling tools that interact with the FastAPI backend to check availability, book, and cancel appointments. The system identifies callers solely by the phone number they speak during the conversation.

## License

MIT