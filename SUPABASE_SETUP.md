# Supabase Integration Setup Guide

## Environment Variables Required

Add these environment variables to your `.env` file or deployment environment:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key
SUPABASE_DATABASE_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres

# Existing variables (keep these)
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
```

## Supabase Project Setup

1. **Create a Supabase Project:**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note down your project URL and API keys

2. **Get Your Database URL:**
   - Go to Settings > Database
   - Copy the connection string
   - Replace `[password]` with your database password

3. **Configure Authentication:**
   - Go to Authentication > Settings
   - Enable email confirmations if desired
   - Configure redirect URLs for your domain

4. **Database Schema:**
   - The User table will be automatically created
   - Supabase Auth will handle user authentication
   - Your existing data will be preserved

## Migration Steps

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**
   - Copy the example above to your `.env` file
   - Fill in your Supabase credentials

3. **Run Database Migration:**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

4. **Test the Integration:**
   - Start your Flask app
   - Try signing up with a new account
   - Check that users are created in both Supabase and your local database

## Features Added

- **Supabase Authentication:** Secure user signup, login, and logout
- **Email Verification:** Automatic email verification for new users
- **Password Reset:** Password reset functionality via email
- **Database Integration:** Seamless integration with Supabase PostgreSQL
- **Backward Compatibility:** Existing users can still log in with their old credentials

## Troubleshooting

- **Database Connection Issues:** Check your `SUPABASE_DATABASE_URL` format
- **Authentication Errors:** Verify your `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- **Email Issues:** Check your Supabase email settings and SMTP configuration



