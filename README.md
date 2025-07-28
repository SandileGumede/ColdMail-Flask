# PitchAI

PitchAI is a Flask web app that analyzes cold emails and DMs for spamminess, personalization, and optimization opportunities. It uses AI (OpenAI API) and rule-based logic to provide actionable feedback and improvements.

## Features
- Spam detection and scoring
- Personalization checker
- Subject line grading
- AI-powered suggestions and rewriting
- PayPal integration for unlimited analyses
- User authentication (sign up, login, logout)

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/your-repo.git
   cd PitchAI
   ```

2. **Create a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   Create a `.env` file in the `PitchAI/` directory with the following:
   ```env
   FLASK_SECRET_KEY=your-secret-key
   OPENAI_API_KEY=your-openai-key
   PAYPAL_CLIENT_ID=your-paypal-client-id
   PAYPAL_CLIENT_SECRET=your-paypal-client-secret
   ```

5. **Run the app locally:**
   ```sh
   python app.py
   ```
   The app will be available at `http://localhost:5000`.

## Deployment

- **Procfile** is included for platforms like Render, Railway, or Heroku.
- Set all environment variables in your deployment platform's dashboard.
- For production, ensure `debug=False` in `app.py`.

## Folder Structure
```
PitchAI/
  app.py
  requirements.txt
  Procfile
  static/
  templates/
  models.py
  ...
```

## License
MIT License (add a LICENSE file if you want to open source) 