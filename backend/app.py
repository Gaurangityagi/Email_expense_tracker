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
import threading
import json

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Global storage for user data
user_data = {}  # {email: {'budget': float, 'sources': list, 'monthly_expenses': dict, 'last_alert': datetime}}

USER_DATA_FILE = 'user_data.json'

def load_user_data():
    """Load user data from JSON file"""
    global user_data
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                data = json.load(f)
                # Convert last_alert strings back to datetime objects
                for email, user in data.items():
                    if user.get('last_alert'):
                        user['last_alert'] = datetime.fromisoformat(user['last_alert'])
                user_data = data
                print(f"Loaded user data for {len(user_data)} users")
    except Exception as e:
        print(f"Error loading user data: {e}")
        user_data = {}

def save_user_data():
    """Save user data to JSON file"""
    try:
        # Convert datetime objects to strings for JSON serialization
        data_to_save = {}
        for email, user in user_data.items():
            user_copy = user.copy()
            if user_copy.get('last_alert') and isinstance(user_copy['last_alert'], datetime):
                user_copy['last_alert'] = user_copy['last_alert'].isoformat()
            data_to_save[email] = user_copy

        with open(USER_DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        print(f"Saved user data for {len(user_data)} users")
    except Exception as e:
        print(f"Error saving user data: {e}")

# Load user data on startup
load_user_data()

# Scheduler for real-time updates
scheduler = BackgroundScheduler()
scheduler.start()

# Email sources mapping
SOURCE_MAP = {
    "Swiggy": "noreply@swiggy.in",
    "Zomato": "noreply@zomato.com",
    "Amazon Auto": "auto-confirm@amazon.in",
    "Domino's": "do-not-reply@dominos.co.in",
    "BookMyShow": "tickets@bookmyshow.email"
}

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

    # Build search criteria
    if date_option == "Custom Range":
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        search_criteria = f'(SINCE "{start_date}" BEFORE "{end_date}")'
    elif date_option == "Year 2024":
        search_criteria = '(SINCE "01-Jan-2024" BEFORE "01-Jan-2025")'
    else:
        days = {"Last 30 Days": 30, "Last 90 Days": 90, "Last Year": 365}
        date_ago = (datetime.now() - timedelta(days=days[date_option])).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{date_ago}")'

    parser = EmailParser(email, password)
    all_data = []

    for name in sources:
        if name in SOURCE_MAP:
            data_list = parser.parse_emails(
                sender_email=SOURCE_MAP[name],
                search_criteria=search_criteria
            )
            for item in data_list:
                item["company"] = name
            all_data.extend(data_list)

    # Process data for frontend
    if all_data:
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df.dropna()

        # Monthly spending trend
        monthly_spending = df.groupby(df['date'].dt.strftime('%Y-%m'))[['amount']].sum().reset_index()

        # Spending by sender
        sender_spending = df.groupby('company')[['amount']].sum().reset_index()

        return jsonify({
            'success': True,
            'data': all_data,
            'monthly_spending': monthly_spending.to_dict('records'),
            'sender_spending': sender_spending.to_dict('records'),
            'total_spent': df['amount'].sum(),
            'average_order': df['amount'].mean(),
            'total_orders': len(df)
        })
    else:
        return jsonify({'success': False, 'message': 'No data found'}), 404

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
        if name in SOURCE_MAP:
            data_list = parser.parse_emails(
                sender_email=SOURCE_MAP[name],
                search_criteria=search_criteria
            )
            for item in data_list:
                item["company"] = name
            all_data.extend(data_list)

    if all_data:
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df.dropna()

        # Filter current month
        df = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]

        total_spent = df['amount'].sum()
        remaining = max(budget - total_spent, 0)
        percentage_spent = (total_spent / budget) * 100 if budget > 0 else 0

        return jsonify({
            'success': True,
            'data': df.to_dict('records'),
            'total_spent': total_spent,
            'remaining': remaining,
            'percentage_spent': percentage_spent,
            'budget': budget
        })
    else:
        return jsonify({
            'success': True,
            'data': [],
            'total_spent': 0,
            'remaining': budget,
            'percentage_spent': 0,
            'budget': budget
        })

def send_budget_alert(email, password, budget, total_spent, percentage):
    """Send budget alert email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))

        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = email
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
        server.login(email, password)
        text = msg.as_string()
        server.sendmail(email, email, text)
        server.quit()

        print(f"Budget alert sent to {email}")
        return True
    except Exception as e:
        print(f"Failed to send budget alert: {e}")
        return False

def update_monthly_expenses(email, password):
    """Update monthly expenses for a user"""
    if email not in user_data:
        return

    user = user_data[email]
    sources = user.get('sources', [])
    budget = user.get('budget', 0)

    if not sources or budget <= 0:
        return

    parser = EmailParser(email, password)
    all_data = []

    # Get current month data
    now = datetime.now()
    search_criteria = f'(SINCE "01-{now.strftime("%b-%Y")}")'

    for name in sources:
        if name in SOURCE_MAP:
            data_list = parser.parse_emails(
                sender_email=SOURCE_MAP[name],
                search_criteria=search_criteria
            )
            for item in data_list:
                item["company"] = name
            all_data.extend(data_list)

    if all_data:
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df.dropna()

        # Filter current month
        df = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]

        total_spent = df['amount'].sum()
        remaining = max(budget - total_spent, 0)
        percentage_spent = (total_spent / budget) * 100 if budget > 0 else 0

        user['monthly_expenses'] = {
            'data': df.to_dict('records'),
            'total_spent': total_spent,
            'remaining': remaining,
            'percentage_spent': percentage_spent,
            'budget': budget,
            'last_updated': datetime.now().isoformat()
        }

        # Check for budget alert (80% threshold)
        last_alert = user.get('last_alert')
        if percentage_spent >= 80 and (not last_alert or (datetime.now() - datetime.fromisoformat(last_alert)).days >= 1):
            if send_budget_alert(email, password, budget, total_spent, percentage_spent):
                user['last_alert'] = datetime.now().isoformat()

@app.route('/set_budget', methods=['POST'])
def set_budget():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    budget = data.get('budget', 0)
    sources = data.get('sources', [])

    if not email or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    if budget <= 0 or not sources:
        return jsonify({'success': False, 'message': 'Valid budget and sources required'}), 400

    # Initialize user data
    user_data[email] = {
        'budget': budget,
        'sources': sources,
        'monthly_expenses': {},
        'last_alert': None
    }

    # Start periodic updates for this user
    scheduler.add_job(
        func=update_monthly_expenses,
        args=[email, password],
        trigger="interval",
        minutes=5,
        id=f"{email}_update",
        replace_existing=True
    )

    # Save user data to file
    save_user_data()

    # Initial update
    update_monthly_expenses(email, password)

    return jsonify({'success': True, 'message': 'Budget set and monitoring started'})

@app.route('/get_monthly_expenses', methods=['POST'])
def get_monthly_expenses():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': 'Email required'}), 400

    if email not in user_data:
        return jsonify({'success': False, 'message': 'Budget not set for this user'}), 404

    expenses = user_data[email].get('monthly_expenses', {})
    if not expenses:
        return jsonify({'success': False, 'message': 'No expense data available'}), 404

    return jsonify({
        'success': True,
        'data': expenses
    })

@app.route('/send_budget_alert', methods=['POST'])
def manual_budget_alert():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    if email not in user_data:
        return jsonify({'success': False, 'message': 'Budget not set for this user'}), 404

    user = user_data[email]
    expenses = user.get('monthly_expenses', {})
    if not expenses:
        return jsonify({'success': False, 'message': 'No expense data available'}), 404

    budget = expenses.get('budget', 0)
    total_spent = expenses.get('total_spent', 0)
    percentage = expenses.get('percentage_spent', 0)

    if send_budget_alert(email, password, budget, total_spent, percentage):
        user['last_alert'] = datetime.now().isoformat()
        return jsonify({'success': True, 'message': 'Budget alert sent'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send alert'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
