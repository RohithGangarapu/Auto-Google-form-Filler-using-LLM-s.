# Backend

FastAPI and Selenium backend for the human-in-the-loop form automation flow.

## Run

```bash
python3 -m pip install -r requirements.txt
uvicorn main:app --reload
```

OpenAPI is available at `http://localhost:8000/docs`.

The backend opens a Selenium browser, waits for the user to complete login and CAPTCHA manually, scrapes fields, asks Ollama models for answers, fills the form, and stops before submission.
