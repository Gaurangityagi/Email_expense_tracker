# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from email_processing import EmailParser
import os
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Global storage for user data
user_data = {}  # {email: {'budget': float, 'sources': list, 'monthly_expenses': dict, 'last_alert': datetime_iso}}
USER_DATA_FILE = 'user_data.json'

def load_user_data():
    """Load user data from JSON file"""
    global user_data
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                data = json.load(f)
                # Convert last_alert strings remain strings (we store isoformat); handle when reading
                user_data = data
                print(f"Loaded user data for {len(user_data)} users")
        else:
            user_data = {}
    except Exception as e:
        print(f"Error loading user data: {e}")
        user_data = {}

def save_user_data():
    """Save user data to JSON file"""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=2)
        print(f"Saved user data for {len(user_data)} users")
    except Exception as e:
        print(f"Error saving user data: {e}")

# Load user data on startup
load_user_data()

# Scheduler for background updates
scheduler = BackgroundScheduler()
scheduler.start()

# SOURCE_MAP: backend naming (exact values UI will send must match these keys)
# Each value is a list of possible sender-from addresses (some services use multiple senders)
SOURCE_MAP = {
    "Swiggy": ["noreply@swiggy.in", "orders@swiggy.in", "noreply@orders.swiggy.net"],
    "Instamart": ["noreply@instamart.com", "instamart@noreply.instamart.com"],
    "Zomato": ["noreply@zomato.com", "orders@zomato.com"],
    "Amazon": ["auto-confirm@amazon.in", "auto-confirm@amazon.in", "order-update@amazon.in"],
    "Domino's": ["do-not-reply@dominos.co.in", "noreply@dominos.co.in"],
    "BookMyShow": ["tickets@bookmyshow.email", "no-reply@bookmyshow.com"]
}

# ------------------ Helper functions ------------------

def normalize_company(sender_field_or_label):
    """Normalize company label to one of the backend names"""
    s = (sender_field_or_label or "").lower()
    if "instamart" in s:
        return "Instamart"
    if "swiggy" in s:
        return "Swiggy"
    if "amazon" in s:
        return "Amazon"
    if "zomato" in s:
        return "Zomato"
    if "domino" in s or "dominos" in s:
        return "Domino's"
    if "bookmyshow" in s or "book my show" in s:
        return "BookMyShow"
    return sender_field_or_label or "Unknown"

def aggregate_results_to_response(all_data):
    """
    all_data: list of dicts from parser with keys: date, subject, sender, amount, preview, plus 'company' optional.
    Returns dict with monthly_spending, sender_spending, total_spent, average_order, total_orders, expenses (normalized).
    """
    if not all_data:
        return {
            'monthly_spending': [],
            'sender_spending': [],
            'total_spent': 0,
            'average_order': 0,
            'total_orders': 0,
            'expenses': []
        }

    df = pd.DataFrame(all_data)

    # Normalize and clean columns
    # parse date safely
    df['date'] = pd.to_datetime(df.get('date', None), errors='coerce')
    # clean amount column to float
    df['amount'] = pd.to_numeric(df.get('amount', None), errors='coerce')
    df = df.dropna(subset=['amount'])  # drop rows without numeric amounts

    if df.empty:
        return {
            'monthly_spending': [],
            'sender_spending': [],
            'total_spent': 0,
            'average_order': 0,
            'total_orders': 0,
            'expenses': []
        }

    # If company is not present in rows, derive from sender or subject
    if 'company' not in df.columns:
        df['company'] = df['sender'].apply(lambda s: normalize_company(s))

    # Format monthly spending (YYYY-MM)
    df['month'] = df['date'].dt.strftime('%Y-%m').fillna('Unknown')
    monthly_spending = df.groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'amount'})
    monthly_spending = monthly_spending.sort_values('month')

    # Spending by sender/company
    sender_spending = df.groupby('company')['amount'].sum().reset_index().rename(columns={'amount': 'amount'})
    sender_spending = sender_spending.sort_values('amount', ascending=False)

    total_spent = float(round(df['amount'].sum(), 2))
    total_orders = int(len(df))
    average_order = float(round(df['amount'].mean(), 2)) if total_orders > 0 else 0.0

    # Build expenses list for frontend (ensure preview present)
    expenses = []
    for _, row in df.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d') if not pd.isna(row['date']) else ''
        company = normalize_company(row.get('company') or row.get('sender') or '')
        preview = row.get('preview') if 'preview' in row and row.get('preview') else ""
        expenses.append({
            'company': company,
            'date': date_str,
            'amount': float(round(row['amount'], 2)),
            'preview': preview
        })

    return {
        'monthly_spending': monthly_spending.to_dict('records'),
        'sender_spending': sender_spending.to_dict('records'),
        'total_spent': total_spent,
        'average_order': average_order,
        'total_orders': total_orders,
        'expenses': expenses
    }

# ------------------ Routes ------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    parser = EmailParser(email, password)
    if parser.connect():
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Login failed'}), 401

@app.route('/analyze_emails', methods=['POST'])
def analyze_emails():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    sources = data.get('sources', [])
    date_option = data.get('date_option', 'Last 30 Days')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    parser = EmailParser(email, password)
    all_data = []

    # Determine search criteria based on date option
    now = datetime.now()
    if date_option == 'This Month':
        search_criteria = f'(SINCE "01-{now.strftime("%b-%Y")}")'
    elif date_option == 'Last 30 Days':
        date_ago = (now - timedelta(days=30)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{date_ago}")'
    elif date_option == 'This Year':
        search_criteria = f'(SINCE "01-Jan-{now.year}")'
    else:
        search_criteria = f'(SINCE "01-Jan-{now.year}")'

    # For each selected source call parser for each known sender address for that source
    for name in sources:
        if name not in SOURCE_MAP:
            continue
        sender_list = SOURCE_MAP.get(name, [])
        for sender_addr in sender_list:
            try:
                data_list = parser.parse_emails(sender_email=sender_addr, search_criteria=search_criteria)
            except Exception as e:
                print(f"Error parsing emails for {sender_addr}: {e}")
                data_list = []

            for item in data_list:
                # attach canonical company label
                item['company'] = name
            all_data.extend(data_list)

    result = aggregate_results_to_response(all_data)

    return jsonify({
        'success': True,
        'data': all_data,
        'monthly_spending': result['monthly_spending'],
        'sender_spending': result['sender_spending'],
        'total_spent': result['total_spent'],
        'average_order': result['average_order'],
        'total_orders': result['total_orders'],
        'expenses': result['expenses']
    })

@app.route('/budget_analysis', methods=['POST'])
def budget_analysis():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    sources = data.get('sources', [])
    budget = data.get('budget', 0)

    if not email or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    parser = EmailParser(email, password)
    all_data = []

    # Get current month data
    now = datetime.now()
    search_criteria = f'(SINCE "01-{now.strftime("%b-%Y")}")'

    for name in sources:
        if name not in SOURCE_MAP:
            continue
        for sender_addr in SOURCE_MAP.get(name, []):
            try:
                data_list = parser.parse_emails(sender_email=sender_addr, search_criteria=search_criteria)
            except Exception as e:
                print(f"Error parsing emails for {sender_addr}: {e}")
                data_list = []
            for item in data_list:
                item['company'] = name
            all_data.extend(data_list)

    result = aggregate_results_to_response(all_data)

    # Filter for current month (aggregate_results already uses parsed dates)
    total_spent = result['total_spent']
    remaining = max(budget - total_spent, 0)
    percentage_spent = (total_spent / budget) * 100 if budget > 0 else 0.0

    return jsonify({
        'success': True,
        'data': all_data,
        'total_spent': total_spent,
        'remaining': remaining,
        'percentage_spent': percentage_spent,
        'budget': budget
    })

# ------------------ Budget alert utilities ------------------

def send_budget_alert(email_addr, password, budget, total_spent, percentage):
    """Send budget alert email to user (uses provided email credentials to send to same address)."""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))

        msg = MIMEMultipart()
        msg['From'] = email_addr
        msg['To'] = email_addr
        msg['Subject'] = f'Budget Alert: {percentage:.1f}% of Monthly Budget Used'

        body = f"""
Budget Alert!

Your monthly budget: ₹{budget:.2f}
Amount spent this month: ₹{total_spent:.2f}
Percentage used: {percentage:.1f}%

{'⚠️ You are approaching your budget limit!' if percentage >= 80 else '✅ You are within budget.'}
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_addr, password)
        server.sendmail(email_addr, email_addr, msg.as_string())
        server.quit()

        print(f"Budget alert sent to {email_addr}")
        return True
    except Exception as e:
        print(f"Failed to send budget alert: {e}")
        return False

def update_monthly_expenses(email_addr, password):
    """Update monthly expenses for a user in user_data"""
    if email_addr not in user_data:
        return

    user = user_data[email_addr]
    sources = user.get('sources', [])
    budget = user.get('budget', 0)

    if not sources or budget <= 0:
        return

    parser = EmailParser(email_addr, password)
    all_data = []

    now = datetime.now()
    search_criteria = f'(SINCE "01-{now.strftime("%b-%Y")}")'

    for name in sources:
        if name not in SOURCE_MAP:
            continue
        for sender_addr in SOURCE_MAP.get(name, []):
            try:
                data_list = parser.parse_emails(sender_email=sender_addr, search_criteria=search_criteria)
            except Exception as e:
                print(f"Error parsing emails for {sender_addr}: {e}")
                data_list = []
            for item in data_list:
                item['company'] = name
            all_data.extend(data_list)

    result = aggregate_results_to_response(all_data)

    # Save structured monthly_expenses for the user
    user['monthly_expenses'] = {
        'data': result['monthly_spending'],
        'total_spent': result['total_spent'],
        'remaining': max(budget - result['total_spent'], 0),
        'percentage_spent': (result['total_spent'] / budget) * 100 if budget > 0 else 0,
        'budget': budget,
        'last_updated': datetime.now().isoformat(),
        'expenses': result['expenses']
    }

    # Save user_data persistently
    save_user_data()

    # Budget alert: if >=80% and we haven't alerted today
    percentage = user['monthly_expenses']['percentage_spent']
    last_alert_iso = user.get('last_alert')
    should_alert = False
    if percentage >= 80:
        if not last_alert_iso:
            should_alert = True
        else:
            try:
                last_alert_dt = datetime.fromisoformat(last_alert_iso)
                if (datetime.now() - last_alert_dt).days >= 1:
                    should_alert = True
            except Exception:
                should_alert = True

    if should_alert:
        # send budget alert (best-effort)
        if send_budget_alert(email_addr, password, budget, result['total_spent'], percentage):
            user['last_alert'] = datetime.now().isoformat()
            save_user_data()

# ------------------ Endpoints for budget management ------------------

@app.route('/set_budget', methods=['POST'])
def set_budget():
    data = request.json
    email_addr = data.get('email')
    password = data.get('password')
    budget = data.get('budget', 0)
    sources = data.get('sources', [])

    if not email_addr or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    if budget <= 0 or not sources:
        return jsonify({'success': False, 'message': 'Valid budget and sources required'}), 400

    # Initialize user data
    user_data[email_addr] = {
        'budget': float(budget),
        'sources': sources,
        'monthly_expenses': {},
        'last_alert': None
    }

    # Save immediately
    save_user_data()

    # Schedule periodic updates (every 5 minutes)
    job_id = f"{email_addr}_update"
    try:
        scheduler.add_job(
            func=update_monthly_expenses,
            args=[email_addr, password],
            trigger="interval",
            minutes=5,
            id=job_id,
            replace_existing=True
        )
    except Exception as e:
        print(f"Scheduler add job failed: {e}")

    # Initial immediate update (non-blocking)
    try:
        # run in a thread so request doesn't block too long
        threading.Thread(target=update_monthly_expenses, args=(email_addr, password)).start()
    except Exception as e:
        print(f"Initial update thread error: {e}")

    return jsonify({'success': True, 'message': 'Budget set and monitoring started'})

@app.route('/get_monthly_expenses', methods=['POST'])
def get_monthly_expenses():
    data = request.json
    email_addr = data.get('email')

    if not email_addr:
        return jsonify({'success': False, 'message': 'Email required'}), 400

    if email_addr not in user_data:
        return jsonify({'success': False, 'message': 'Budget not set for this user'}), 404

    expenses = user_data[email_addr].get('monthly_expenses', {})
    if not expenses:
        return jsonify({'success': False, 'message': 'No expense data available'}), 404

    return jsonify({
        'success': True,
        'data': expenses
    })

@app.route('/send_budget_alert', methods=['POST'])
def manual_budget_alert():
    data = request.json
    email_addr = data.get('email')
    password = data.get('password')

    if not email_addr or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    if email_addr not in user_data:
        return jsonify({'success': False, 'message': 'Budget not set for this user'}), 404

    user = user_data[email_addr]
    expenses_data = user.get('monthly_expenses', {})
    if not expenses_data:
        return jsonify({'success': False, 'message': 'No expense data available'}), 404

    budget = user.get('budget', 0)
    total_spent = expenses_data.get('total_spent', 0)
    percentage = expenses_data.get('percentage_spent', 0)

    if send_budget_alert(email_addr, password, budget, total_spent, percentage):
        user['last_alert'] = datetime.now().isoformat()
        save_user_data()
        return jsonify({'success': True, 'message': 'Budget alert sent'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send alert'}), 500

# ------------------ Run ------------------

if __name__ == '__main__':
    # Note: in production use a WSGI server like gunicorn, and do not use debug=True
    app.run(debug=True, port=5000)
