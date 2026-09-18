from __future__ import annotations

import sqlite3
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).with_name("budget.db")
INVESTMENT_SUBCATEGORIES = ["Stocks", "ETF", "Mutual funds", "Bonds", "Other"]
DEFAULT_CATEGORIES = [
	("expense", "Food"),
	("expense", "Transport"),
	("expense", "Housing"),
	("expense", "Utilities"),
	("expense", "Health"),
	("expense", "Shopping"),
	("expense", "Entertainment"),
	("income", "Salary"),
	("income", "Freelance"),
	("income", "Gift"),
]


def database_url() -> str:
	url = os.getenv("DATABASE_URL", "")
	if url:
		return url
	try:
		return str(st.secrets.get("DATABASE_URL", ""))
	except FileNotFoundError:
		return ""


def using_postgres() -> bool:
	return bool(database_url())


def connect():
	if using_postgres():
		try:
			import psycopg  # type: ignore[import-not-found]
		except ImportError as error:
			raise RuntimeError("Install psycopg[binary] when using DATABASE_URL.") from error
		return psycopg.connect(database_url())
	connection = sqlite3.connect(DB_PATH)
	connection.row_factory = sqlite3.Row
	return connection


def adapt_sql(sql: str) -> str:
	return sql.replace("?", "%s") if using_postgres() else sql


def init_db() -> None:
	with connect() as connection:
		identity = "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
		statements = [
			f"CREATE TABLE IF NOT EXISTS categories (id {identity}, kind TEXT NOT NULL, name TEXT NOT NULL, UNIQUE(kind, name))",
			f"CREATE TABLE IF NOT EXISTS transactions (id {identity}, transaction_date TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('expense', 'income', 'investment')), category TEXT NOT NULL, subcategory TEXT, amount REAL NOT NULL CHECK(amount > 0), note TEXT DEFAULT '')",
			f"CREATE TABLE IF NOT EXISTS budgets (id {identity}, scope TEXT NOT NULL, category TEXT, amount REAL NOT NULL CHECK(amount > 0), UNIQUE(scope, category))",
		]
		for statement in statements:
			connection.execute(statement)
		category_insert = (
			"INSERT INTO categories(kind, name) VALUES (?, ?) ON CONFLICT(kind, name) DO NOTHING"
			if using_postgres()
			else "INSERT OR IGNORE INTO categories(kind, name) VALUES (?, ?)"
		)
		if using_postgres():
			with connection.cursor() as cursor:
				cursor.executemany(
					adapt_sql(category_insert),
					DEFAULT_CATEGORIES,
				)
		else:
			connection.executemany(
				category_insert,
				DEFAULT_CATEGORIES,
			)


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
	with connect() as connection:
		if using_postgres():
			with connection.cursor() as cursor:
				cursor.execute(adapt_sql(sql), params)
				rows = cursor.fetchall()
				columns = [column.name for column in cursor.description]
				return pd.DataFrame(rows, columns=columns)
		return pd.read_sql_query(adapt_sql(sql), connection, params=params)


def categories_for(kind: str) -> list[str]:
	return query_df(
		"SELECT name FROM categories WHERE kind = ? ORDER BY name", (kind,)
	)["name"].tolist()


def add_transaction(transaction_date: date, kind: str, category: str, subcategory: str, amount: float, note: str) -> None:
	with connect() as connection:
		connection.execute(
			adapt_sql("""
			INSERT INTO transactions(transaction_date, kind, category, subcategory, amount, note)
			VALUES (?, ?, ?, ?, ?, ?)
			"""),
			(transaction_date.isoformat(), kind, category, subcategory, amount, note.strip()),
		)


def period_bounds(period: str, months: int) -> tuple[date, date]:
	end = date.today()
	if period == "This week":
		start = end - timedelta(days=end.weekday())
	elif period == "This month":
		start = end.replace(day=1)
	else:
		start = end - timedelta(days=max(months, 1) * 31 - 1)
	return start, end


def format_money(value: float) -> str:
	return f"${value:,.2f}"


def current_month_forecast() -> tuple[float, float, float]:
	today = date.today()
	month_start = today.replace(day=1)
	current = query_df(
		"""
		SELECT COALESCE(SUM(amount), 0) AS value FROM transactions
		WHERE kind = 'expense' AND transaction_date BETWEEN ? AND ?
		""",
		(month_start.isoformat(), today.isoformat()),
	).iloc[0]["value"]
	historical = query_df(
		"""
		SELECT SUBSTR(transaction_date, 1, 7) AS month, SUM(amount) AS value
		FROM transactions
		WHERE kind = 'expense' AND transaction_date < ?
		GROUP BY month
		ORDER BY month DESC LIMIT 6
		""",
		(month_start.isoformat(),),
	)
	historical_average = float(historical["value"].mean()) if not historical.empty else float(current)
	elapsed_days = today.day
	days_in_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - month_start
	pace_forecast = float(current) / elapsed_days * days_in_month.days
	forecast = pace_forecast if historical.empty else pace_forecast * 0.6 + historical_average * 0.4
	return float(current), float(forecast), historical_average


def add_category_panel() -> None:
	with st.expander("Add a custom category"):
		with st.form("category_form", clear_on_submit=True):
			category_kind = st.selectbox("Category type", ["expense", "income"])
			category_name = st.text_input("Category name")
			submitted = st.form_submit_button("Add category", type="primary")
			if submitted:
				if not category_name.strip():
					st.error("Enter a category name.")
				else:
					try:
						with connect() as connection:
							category_insert = "INSERT INTO categories(kind, name) VALUES (?, ?)"
							if using_postgres():
								category_insert += " ON CONFLICT(kind, name) DO NOTHING"
							connection.execute(
								adapt_sql(category_insert),
								(category_kind, category_name.strip()),
							)
						st.success("Category added.")
						st.rerun()
					except (sqlite3.IntegrityError, RuntimeError):
						st.warning("That category already exists.")


def transaction_form() -> None:
	st.subheader("Record a transaction")
	with st.form("transaction_form", clear_on_submit=True):
		transaction_kind = st.selectbox("Type", ["expense", "income", "investment"])
		transaction_date = st.date_input("Date", value=date.today())
		available_categories = categories_for(transaction_kind) if transaction_kind != "investment" else ["Investments"]
		category = st.selectbox("Category", available_categories)
		subcategory = ""
		if transaction_kind == "investment":
			subcategory = st.selectbox("Investment type", INVESTMENT_SUBCATEGORIES)
		amount = st.number_input("Amount", min_value=0.01, step=10.0, format="%.2f")
		note = st.text_input("Note", placeholder="Optional context")
		submitted = st.form_submit_button("Save transaction", type="primary")
		if submitted:
			add_transaction(transaction_date, transaction_kind, category, subcategory, amount, note)
			st.success("Transaction saved.")
			st.rerun()


def budget_panel() -> None:
	st.subheader("Limits and alerts")
	with st.form("budget_form", clear_on_submit=True):
		scope = st.selectbox("Limit type", ["Overall expenses", "Category"])
		category = None
		if scope == "Category":
			category_options = sorted(set(categories_for("expense")))
			category = st.selectbox("Expense category", category_options)
		amount = st.number_input("Monthly limit", min_value=1.0, step=50.0, format="%.2f")
		submitted = st.form_submit_button("Save limit", type="primary")
		if submitted:
			with connect() as connection:
				budget_insert = "INSERT INTO budgets(scope, category, amount) VALUES (?, ?, ?)"
				if using_postgres():
					budget_insert += " ON CONFLICT(scope, category) DO UPDATE SET amount = excluded.amount"
				else:
					budget_insert = "INSERT OR REPLACE INTO budgets(scope, category, amount) VALUES (?, ?, ?)"
				connection.execute(
					adapt_sql(budget_insert),
					("overall" if scope == "Overall expenses" else "category", category, amount),
				)
			st.success("Limit saved.")
			st.rerun()


def budget_alerts(month_expenses: pd.DataFrame) -> None:
	budgets = query_df("SELECT scope, category, amount FROM budgets ORDER BY scope, category")
	if budgets.empty:
		st.info("Set a limit below to activate budget alerts.")
		return
	total = float(month_expenses["amount"].sum()) if not month_expenses.empty else 0
	for budget in budgets.itertuples():
		actual = total if budget.scope == "overall" else float(
			month_expenses.loc[month_expenses["category"] == budget.category, "amount"].sum()
		)
		ratio = actual / budget.amount
		label = "Overall expenses" if budget.scope == "overall" else budget.category
		if ratio >= 1:
			st.error(f"{label}: {format_money(actual)} of {format_money(budget.amount)} used ({ratio:.0%}).")
		elif ratio >= 0.8:
			st.warning(f"{label}: {format_money(actual)} of {format_money(budget.amount)} used ({ratio:.0%}).")


def dashboard() -> None:
	st.subheader("Analytics dashboard")
	left, right = st.columns([1, 1])
	with left:
		period = st.selectbox("Analysis period", ["This week", "This month", "Last N months"])
	with right:
		months = st.number_input("Number of months", min_value=1, max_value=24, value=3) if period == "Last N months" else 1
	start, end = period_bounds(period, int(months))
	expenses = query_df(
		"""
		SELECT transaction_date, category, amount, note FROM transactions
		WHERE kind = 'expense' AND transaction_date BETWEEN ? AND ?
		ORDER BY transaction_date DESC
		""",
		(start.isoformat(), end.isoformat()),
	)
	all_transactions = query_df(
		"SELECT kind, COALESCE(SUM(amount), 0) AS amount FROM transactions GROUP BY kind"
	)
	totals = {row.kind: float(row.amount) for row in all_transactions.itertuples()}
	income = totals.get("income", 0)
	investments = totals.get("investment", 0)
	expenses_all_time = totals.get("expense", 0)
	monthly_current, monthly_forecast, historical_average = current_month_forecast()

	metric_columns = st.columns(4)
	metric_columns[0].metric("Period expenses", format_money(float(expenses["amount"].sum()) if not expenses.empty else 0))
	metric_columns[1].metric("Total money left", format_money(income - expenses_all_time - investments))
	metric_columns[2].metric("This month forecast", format_money(monthly_forecast), f"{format_money(monthly_current)} so far")
	metric_columns[3].metric("Recorded investments", format_money(investments))

	chart_tab, report_tab, investment_tab = st.tabs(["Spending", "Report", "Investments"])
	with chart_tab:
		if expenses.empty:
			st.info("No expenses in this period yet.")
		else:
			by_category = expenses.groupby("category", as_index=True)["amount"].sum().sort_values(ascending=False)
			st.bar_chart(by_category)
			st.caption(f"Forecast blends the current daily pace with a six-month historical average of {format_money(historical_average)}.")
		st.markdown("#### Budget alerts")
		current_month = date.today().replace(day=1).isoformat()
		budget_alerts(query_df("SELECT category, amount FROM transactions WHERE kind = 'expense' AND transaction_date >= ?", (current_month,)))
	with report_tab:
		st.dataframe(expenses, width="stretch", hide_index=True)
		if not expenses.empty:
			st.download_button("Download expense report", expenses.to_csv(index=False), "expense-report.csv", "text/csv")
	with investment_tab:
		investments_df = query_df(
			"SELECT transaction_date AS date, subcategory AS type, amount, note FROM transactions WHERE kind = 'investment' ORDER BY transaction_date DESC"
		)
		st.dataframe(investments_df, width="stretch", hide_index=True)
		st.caption("Investments are recorded separately and excluded from spending analysis.")


st.set_page_config(page_title="BAAR Budget Monitor", page_icon="$", layout="wide")
init_db()
st.title("BAAR Budget Monitor")
st.caption("A local-first view of where your money is going, what is left, and what is approaching its limit.")

dashboard_tab, add_tab, settings_tab = st.tabs(["Dashboard", "Add transaction", "Categories and limits"])
with dashboard_tab:
	dashboard()
with add_tab:
	transaction_form()
with settings_tab:
	add_category_panel()
	budget_panel()

