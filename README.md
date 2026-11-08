# ZAYYA AI

A Flask-based AI chat website with email/password accounts, saved chat history, and the Yakal OpenAI-compatible API.

## Features
- Email registration and sign-in (passwords are hashed)
- Private chat history per account
- Create and revisit conversations
- Dark/light theme and responsive layout
- Yakal API key stored server-side in environment variables

## Run locally
1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your Yakal API key and a strong `SECRET_KEY`.
5. Load environment variables, then run `python app.py`.
6. Open `http://127.0.0.1:5000`.

## Deploy on Render
The included `render.yaml` defines the web service and PostgreSQL database. Connect the repository to Render as a Blueprint, then set `YAKAL_API_KEY` in Render's environment settings. Never commit `.env` or expose the API key in browser JavaScript.

## Notes
- Yakal API endpoint: `https://api.yakal.et/v1/chat/completions`
- Default model: `glm-5.3-flash`
- API usage is billed from the Yakal wallet according to its current pricing. Check your balance and usage with the account owner before making requests.
- For a public production launch, add email verification, password reset, CSRF protection, rate limiting, and account deletion before inviting users.
