# Render Deployment Setup for Supabase

## Quick Fix for Login Issues

The error `"ValueError: SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"` means your Supabase credentials aren't configured in Render.

## Step-by-Step Fix

### 1. Get Your Supabase Credentials

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project
3. Get these values:
   - **SUPABASE_URL**: Settings → API → Project URL
   - **SUPABASE_ANON_KEY**: Settings → API → Project API keys → anon public
   - **SUPABASE_SERVICE_KEY**: Settings → API → Project API keys → service_role secret
   - **SUPABASE_DATABASE_URL**: Settings → Database → Connection string → URI

### 2. Add Environment Variables to Render

1. Go to [render.com](https://render.com)
2. Select your PitchAI service
3. Click on **"Environment"** tab
4. Add these variables:

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key
SUPABASE_DATABASE_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres
```

### 3. Redeploy Your App

After adding the environment variables:
1. Click **"Save Changes"** in Render
2. Your app will automatically redeploy
3. Check the logs to confirm no more errors

### 4. Test Your Login

1. Visit your deployed app
2. Try to sign up with a new account
3. Check `/debug-login` to see if Supabase is working

## Alternative: Use Local Authentication Only

If you don't want to use Supabase right now, the app will fall back to local authentication for existing users. New signups won't work until Supabase is configured.

## Troubleshooting

- **Still getting errors?** Check your Render logs for the exact error message
- **Can't find Supabase credentials?** Make sure your Supabase project is active
- **Database connection issues?** Verify your `SUPABASE_DATABASE_URL` format is correct

## Example Environment Variables

```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DATABASE_URL=postgresql://postgres:yourpassword@db.abcdefghijklmnop.supabase.co:5432/postgres
```

Replace the example values with your actual Supabase credentials.

