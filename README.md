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
