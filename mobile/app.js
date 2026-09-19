const state = { kind: 'expense', records: [] };
const categories = { expense: [], income: [], investment: ['Investments'] };
const defaultCategories = { expense: ['Food', 'Transport', 'Housing', 'Utilities', 'Health', 'Shopping', 'Entertainment'], income: ['Salary', 'Freelance', 'Gift'], investment: ['Investments'] };
const configKey = 'baar-supabase-config';

const $ = (id) => document.getElementById(id);
const today = new Date().toISOString().slice(0, 10);
$('transactionDate').value = today;

function config() { try { return JSON.parse(localStorage.getItem(configKey) || '{}'); } catch { return {}; } }
function apiUrl(table, query = '') { return `${config().url}/rest/v1/${table}${query}`; }
function headers() { return { apikey: config().key, Authorization: `Bearer ${config().key}`, 'Content-Type': 'application/json', Prefer: 'return=minimal' }; }
function connected() { return Boolean(config().url && config().key); }

async function request(table, options = {}, query = '') {
  if (!connected()) throw new Error('Add your Supabase connection in settings.');
  const response = await fetch(apiUrl(table, query), { ...options, headers: { ...headers(), ...(options.headers || {}) } });
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
}

function setKind(kind) {
  state.kind = kind;
  document.querySelectorAll('.type-tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.kind === kind));
  $('investmentTypeRow').classList.toggle('hidden', kind !== 'investment');
  renderCategories();
}
function renderCategories() {
  const list = categories[state.kind].length ? categories[state.kind] : defaultCategories[state.kind];
  $('category').innerHTML = list.map((category) => `<option>${escapeHtml(category)}</option>`).join('');
}
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[char])); }
function money(value) { return `₹${Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
function showMessage(message, error = false) { $('formMessage').textContent = message; $('formMessage').style.color = error ? '#c45642' : '#458264'; }

async function loadCategories() {
  if (!connected()) { renderCategories(); return; }
  try {
    const rows = await request('categories', {}, '?select=kind,name&order=name');
    categories.expense = rows.filter((row) => row.kind === 'expense').map((row) => row.name);
    categories.income = rows.filter((row) => row.kind === 'income').map((row) => row.name);
    renderCategories();
  } catch (error) { showMessage('Could not load categories.', true); renderCategories(); }
}

async function loadRecords() {
  if (!connected()) { renderRecords([]); return; }
  try {
    state.records = await request('transactions', {}, '?select=transaction_date,kind,category,subcategory,amount,note&order=transaction_date.desc&limit=12');
    renderRecords(state.records);
    updateBalance();
  } catch (error) { renderRecords([]); showMessage('Connect to Supabase in settings.', true); }
}
function renderRecords(records) {
  if (!records.length) { $('recentList').innerHTML = '<p class="empty-state">No transactions recorded yet.</p>'; return; }
  $('recentList').innerHTML = records.map((record) => `<article class="recent-item"><div><p><b>${escapeHtml(record.category)}</b>${record.subcategory ? ` · ${escapeHtml(record.subcategory)}` : ''}</p><small>${escapeHtml(record.transaction_date)}${record.note ? ` · ${escapeHtml(record.note)}` : ''}</small></div><strong class="${record.kind}-amount">${record.kind === 'income' ? '+' : '-'}${money(record.amount)}</strong></article>`).join('');
}
function updateBalance() {
  const income = state.records.filter((row) => row.kind === 'income').reduce((sum, row) => sum + Number(row.amount), 0);
  const spent = state.records.filter((row) => row.kind === 'expense' || row.kind === 'investment').reduce((sum, row) => sum + Number(row.amount), 0);
  $('income').textContent = money(income); $('spent').textContent = money(spent); $('balance').textContent = money(income - spent);
}

$('transactionForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!connected()) { $('settingsDialog').showModal(); return; }
  const record = { transaction_date: $('transactionDate').value, kind: state.kind, category: $('category').value, subcategory: state.kind === 'investment' ? $('investmentType').value : '', amount: Number($('amount').value), note: $('note').value.trim() };
  try {
    await request('transactions', { method: 'POST', body: JSON.stringify(record) });
    $('amount').value = ''; $('note').value = ''; showMessage('Saved.'); await loadRecords();
  } catch (error) { showMessage('Could not save this transaction.', true); }
});
document.querySelectorAll('.type-tab').forEach((tab) => tab.addEventListener('click', () => setKind(tab.dataset.kind)));
$('refreshButton').addEventListener('click', loadRecords);
$('settingsButton').addEventListener('click', () => { const saved = config(); $('supabaseUrl').value = saved.url || ''; $('supabaseKey').value = saved.key || ''; $('settingsDialog').showModal(); });
$('settingsForm').addEventListener('submit', (event) => { if (event.submitter?.value === 'cancel') return; localStorage.setItem(configKey, JSON.stringify({ url: $('supabaseUrl').value.trim().replace(/\/$/, ''), key: $('supabaseKey').value.trim() })); loadCategories(); loadRecords(); });
$('clearSettings').addEventListener('click', () => { localStorage.removeItem(configKey); $('settingsDialog').close(); renderRecords([]); updateBalance(); });

renderCategories(); loadCategories(); loadRecords();
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js'));
