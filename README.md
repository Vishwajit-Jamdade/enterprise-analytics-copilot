# Enterprise Data Assistant

React frontend in [`frontend/`](frontend) and Python backend in [`backend/`](backend) wired to the agent in [`my_agent/`](my_agent).

## Layout

- `backend/` - FastAPI bridge that runs the ADK agent and serves chart artifacts
- `frontend/` - Vite + React UI
- `my_agent/` - Gemini agent and Databricks tools
- `charts/` - generated chart outputs

## Setup

1. Create a Python virtual environment.
2. Install backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

3. Install frontend dependencies:

```powershell
cd frontend
npm install
```

4. Create a root `.env` file from `.env.example` and fill in:

- `GEMINI_API_KEY` for the Gemini API path
- `DATABRICKS_HOST`
- `DATABRICKS_HTTP_PATH`
- `DATABRICKS_TOKEN`

Optional Vertex AI mode:

- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`

The backend now reads only the root `.env`. Move any values from `my_agent/.env` into the root file and stop using the legacy file.

## Run

Start the backend:

```powershell
python -m uvicorn backend.app:app --reload --port 8001
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

The frontend runs on `http://127.0.0.1:5173` and proxies API calls to the backend on `http://127.0.0.1:8001`.
