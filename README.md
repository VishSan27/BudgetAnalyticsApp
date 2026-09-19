# BAAR Budget Monitor

BAAR is a local-first budget analytics app built with Streamlit. It supports expenses, income, investments, custom categories, forecasts, reports, and budget alerts.

## Run locally

```powershell
cd "C:\Users\Vish\OneDrive\Desktop\BAAR"
pip install -r requirements.txt
streamlit run main.py
```

Open `http://localhost:8501`.

Without `DATABASE_URL`, records are stored in the local `budget.db` SQLite file.

## Enable phone access from anywhere

1. Create a Supabase project.
2. Open Supabase SQL Editor and run `schema.sql`.
3. Copy the Supabase PostgreSQL connection string.
4. Create a GitHub repository and push this folder.
5. Create a Streamlit Community Cloud app using `main.py`.
6. In the app settings, add this secret:

```toml
DATABASE_URL = "your Supabase connection string"
```

The app will then use Supabase for records and can be opened from your phone using the Streamlit Cloud URL.

## Migrate existing local records

Set the same connection string locally, then run:

```powershell
$env:DATABASE_URL = "your Supabase connection string"
python migrate_to_postgres.py
```

The migration copies categories, transactions, and budgets from `budget.db`. Do not commit your connection string or `.streamlit/secrets.toml`.

## Phone app (installable PWA)

The `mobile/` folder is a phone-first installable app for quick transaction entry. It uses the same Supabase `categories` and `transactions` tables as the Streamlit dashboard.

To publish it with GitHub Pages:

1. In the GitHub repository, open **Settings → Pages**.
2. Choose **Deploy from a branch**, select `main`, and choose `/ (root)`.
3. Open `https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPOSITORY/mobile/` on your phone.
4. Tap the settings button and enter your Supabase **Project URL** and public **anon key**. Never use the service-role key.
5. Install it:
	- Android Chrome: menu → **Add to Home screen**
	- iPhone Safari: Share → **Add to Home Screen**

The app stores the public connection details on the device and records data in Supabase. Configure Supabase Row Level Security and authentication before sharing the URL publicly; the current V1 database schema is intended for personal testing.
