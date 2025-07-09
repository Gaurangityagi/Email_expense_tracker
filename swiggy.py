import email
import streamlit as st
import pandas as pd
from Swiggy_data import EmailParser  # assuming your existing code is in email_parser.py
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
import socket

# Set page config
st.set_page_config(
    page_title="Email Order Analysis",
    page_icon="📧",
    layout="wide"
)

# Add CSS for styling
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        padding: 0.5rem;
    }
    .stPassword > div > div > input {
        padding: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Email sources mapping
SOURCE_MAP = {
    "Swiggy": "noreply@swiggy.in",
    "Zomato":"noreply@zomato.com",
    "Amazon Auto": "auto-confirm@amazon.in",
    "Domino's": "do-not-reply@dominos.co.in",
    "BookMyShow": "tickets@bookmyshow.email"
}


def authenticate():
    """Handle user authentication"""
    with st.container():
        st.title("📧 Email Order Analysis")
        
        with st.form("email_form"):
            email = st.text_input("Email Address", placeholder="Enter your email")
            password = st.text_input("App Password", type="password", 
                                   placeholder="Enter your Google App Password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if email and password:
                    # Test connection
                    parser = EmailParser(email, password)
                    if parser.connect():
                        st.success("Successfully connected to email!")
                        return True, email, password
                    else:
                        st.error("Failed to connect. Please check your credentials.")
                else:
                    st.warning("Please enter both email and password.")
                    
            if not submitted:
                st.info("Note: For Gmail, please use an App Password. [Learn how to create one](https://support.google.com/accounts/answer/185833?hl=en)")
    
    return False, None, None
def analyze_with_limit(data, budget):
    """Analyze current month data and compare with limit"""
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df = df.dropna(subset=['amount'])

    # Filter for current month
    now = datetime.now()
    df = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]

    st.subheader(f"Monthly Spending – {now.strftime('%B %Y')}")
    
    # Total spent
    total_spent = df['amount'].sum()
    
    # Main pie chart: Limit vs Spent
    pie_df = pd.DataFrame({
        'Category': ['Spent', 'Remaining'],
        'Amount': [total_spent, max(budget - total_spent, 0)]
    })
    fig = px.pie(pie_df, names='Category', values='Amount', title='Monthly Budget Usage')
    st.plotly_chart(fig)

    # Show metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Budget Limit", f"₹{budget:.2f}")
    col2.metric("Total Spent", f"₹{total_spent:.2f}")
    col3.metric("Remaining", f"₹{max(budget - total_spent, 0):.2f}")

    # Optional: Show raw data
    st.subheader("Order Details This Month")
    st.dataframe(df.sort_values(by='date', ascending=False))

def analyze_data(data):
    """Analyze the order data and create visualizations"""
    df = pd.DataFrame(data)
    
    # Convert date strings to datetime
    df['date'] = pd.to_datetime(df['date'],errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'])
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Monthly spending trend
        monthly_spending = df.groupby(df['date'].dt.strftime('%Y-%m'))[['amount']].sum().reset_index()
        fig1 = px.line(monthly_spending, x='date', y='amount',
                      title='Monthly Spending Trend',
                      labels={'date': 'Month', 'amount': 'Total Amount (₹)'})
        st.plotly_chart(fig1)
        
    with col2:
        # Spending by sender
        sender_spending = df.groupby('company')[['amount']].sum().reset_index()
        fig2 = px.pie(sender_spending, values='amount', names='company',
                     title='Spending by Source')
        st.plotly_chart(fig2)
    
    # Display summary statistics
    st.subheader("Summary Statistics")
    col3, col4, col5 = st.columns(3)
    
    with col3:
        st.metric("Total Spent", f"₹{df['amount'].sum():.2f}")
    with col4:
        st.metric("Average Order", f"₹{df['amount'].mean():.2f}")
    with col5:
        st.metric("Total Orders", len(df))
    
    # Display the raw data
    st.subheader("Order Details")
    st.dataframe(df.sort_values(by='date', ascending=False))
    
    # Allow CSV download
    st.download_button(
        label="Download Data as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='order_analysis.csv',
        mime='text/csv'
    )

def main():
    

    
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        authenticated, email, password = authenticate()
        if authenticated:
            st.session_state.authenticated = True
            st.session_state.email = email
            st.session_state.password = password
            st.rerun()
    
    else:
        # Show logout button
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        #Navigation 
        st.sidebar.title("Navigation")  
        page=st.sidebar.radio("Go to:",["Order Analysis","Track and set limit"])
        if page=="Order Analysis":
            order_analysis_view()
        else:
            budget_tracker_view()
def order_analysis_view():
        # Email analysis interface
        st.title("Email Order Analysis")
        
        # Date range selector
        st.sidebar.header("Settings")
        date_option = st.sidebar.selectbox(
            "Select Date Range",
            ["Last 30 Days", "Last 90 Days", "Last Year", "Custom Range"]
        )
        
        if date_option == "Custom Range":
            start_date = st.sidebar.date_input("Start Date")
            end_date = st.sidebar.date_input("End Date")
            search_criteria = f'(SINCE "{start_date.strftime("%d-%b-%Y")}" BEFORE "{end_date.strftime("%d-%b-%Y")}")'
        elif date_option == "Year 2024":
            search_criteria = '(SINCE "01-Jan-2024" BEFORE "01-Jan-2025")'
        else:
            days = {"Last 30 Days": 30, "Last 90 Days": 90, "Last Year": 365}
            date_ago = (datetime.now() - timedelta(days=days[date_option])).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{date_ago}")'
        
        # Email source selector
        sources = st.sidebar.multiselect(
            "Select Sources",
           options=list(SOURCE_MAP.keys())
        )
        
        # Analysis button
        if st.sidebar.button("Analyze Emails"):
            with st.spinner("Analyzing emails..."):
                parser = EmailParser(st.session_state.email, st.session_state.password)
                all_data = []
                selected_emails=[SOURCE_MAP[name] for name in sources]
                for name,sender in SOURCE_MAP.items():
                    if sender in selected_emails:
                        data = parser.parse_emails(
                            sender_email=sender,
                            search_criteria=search_criteria
                        )
                        for item in data:
                            item["company"]=name
                        all_data.extend(data)
                
                if all_data:
                      analyze_data(all_data)

                else:
                    st.warning("No order information found for the selected criteria.")
def budget_tracker_view():
    st.title("Monthly budget tracker")
    st.sidebar.header("tracking settings")
    budget=st.sidebar.number_input("Enter your Monthly limit in Rs.")
    selected_names = st.sidebar.multiselect("Select Sources", list(SOURCE_MAP.keys()))
    
    if st.sidebar.button("Analyze Budget Usage") and budget:
        with st.spinner("Analyzing current month usage..."):
            parser = EmailParser(st.session_state.email, st.session_state.password)
            all_data = []
            for name in selected_names:
                data = parser.parse_emails(sender_email=SOURCE_MAP[name], search_criteria='(SINCE "01-Apr-2025")')
                for d in data:
                    d["company"] = name
                all_data.extend(data)

            if all_data:
                analyze_with_limit(all_data, budget)
            else:
                st.warning("No data found for this month.")
def create_spending_timeline(df):
    """Create interactive spending timeline"""
    fig = px.scatter(df, x='date', y='amount', 
                    color='company',
                    hover_data=['subject', 'amount'],
                    title='Order Timeline')
    
    fig.update_traces(marker=dict(size=12, line=dict(width=2)),
                     selector=dict(mode='markers'))
    
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Amount (₹)',
        hovermode='closest'
    )
    
    return fig
def analyze_with_limit(data, budget):
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df = df.dropna(subset=['amount'])

    # Filter only current month data
    now = datetime.now()
    df = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]

    total_spent = df['amount'].sum()
    remaining = max(budget - total_spent, 0)
    percentage_spent = (total_spent / budget) * 100

    # 🔔 Alert if budget exceeds 80%
   
    if percentage_spent >= 80 and percentage_spent < 100:
        st.warning(f"⚠️ You have used {percentage_spent:.1f}% of your monthly budget!")
        
        # Try to send email alert
        try:
            message = MIMEText(f"⚠️ You have used {percentage_spent:.1f}% of your monthly budget!")
            message['Subject'] = 'Budget Alert-High Spending'
            message['From'] = st.session_state.email
            message['To'] = st.session_state.email
            
            st.info(f"Attempting to send alert to {st.session_state.email}...")
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                # Add debug info
                server.set_debuglevel(1)
                
                # Login
                server.login(st.session_state.email, st.session_state.password)
                
                # Send mail
                server.sendmail(st.session_state.email, st.session_state.email, message.as_string())
                
            st.success("✅ Alert email sent successfully!")
        except smtplib.SMTPAuthenticationError:
            st.error("❌ Authentication failed. For Gmail, ensure you're using an app password if 2FA is enabled.")
        except smtplib.SMTPException as e:
            st.error(f"❌ SMTP error: {e}")
        except socket.timeout:
            st.error("❌ Connection timed out while sending email")
        except Exception as e:
            st.error(f"❌ Failed to send email alert: {str(e)}")


    elif percentage_spent >= 100:
        st.error(f"❌ You have exceeded your monthly budget by ₹{total_spent - budget:.2f}!")
    # Pie Chart - Limit vs Spent
    pie_df = pd.DataFrame({
        'Category': ['Spent', 'Remaining'],
        'Amount': [total_spent, remaining]
    })
    fig = px.pie(pie_df, names='Category', values='Amount', title='Monthly Budget Usage')
    st.plotly_chart(fig)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Budget Limit", f"₹{budget:.2f}")
    col2.metric("Total Spent", f"₹{total_spent:.2f}")
    col3.metric("Remaining", f"₹{remaining:.2f}")

    # Raw data
    st.subheader("This Month's Orders")
    st.dataframe(df.sort_values(by='date', ascending=False))








if __name__ == "__main__":
    main()
