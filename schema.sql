CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(kind, name)
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_date TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('expense', 'income', 'investment')),
    category TEXT NOT NULL,
    subcategory TEXT,
    amount REAL NOT NULL CHECK(amount > 0),
    note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS budgets (
    id SERIAL PRIMARY KEY,
    scope TEXT NOT NULL,
    category TEXT,
    amount REAL NOT NULL CHECK(amount > 0),
    UNIQUE(scope, category)
);

INSERT INTO categories(kind, name) VALUES
    ('expense', 'Food'),
    ('expense', 'Transport'),
    ('expense', 'Housing'),
    ('expense', 'Utilities'),
    ('expense', 'Health'),
    ('expense', 'Shopping'),
    ('expense', 'Entertainment'),
    ('income', 'Salary'),
    ('income', 'Freelance'),
    ('income', 'Gift')
ON CONFLICT(kind, name) DO NOTHING;
