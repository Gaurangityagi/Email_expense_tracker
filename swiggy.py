import streamlit as st
import pandas as pd
from Swiggy_data import EmailParser  # assuming your existing code is in email_parser.py
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(
    page_title="Swiggy Expense Tracker",
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

def authenticate():
    """Handle user authentication"""
    with st.container():
        st.title("📧 Swiggy Expense Tracker")
        
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

def analyze_data(data):
    """Analyze the order data and create visualizations"""
    df = pd.DataFrame(data)
    
    # Convert date strings to datetime
    df['date'] = pd.to_datetime(df['date'])
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
        sender_spending = df.groupby('sender')[['amount']].sum().reset_index()
        fig2 = px.pie(sender_spending, values='amount', names='sender',
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
            
        # Email analysis interface
        st.title("Email Order Analysis")
        
        # Date range selector
        st.sidebar.header("Settings")
        date_option = st.sidebar.selectbox(
            "Select Date Range",
            ["Last 30 Days", "Last 90 Days", "Last Year", "Custom Range", "Year 2022"]
        )
        
        if date_option == "Custom Range":
            start_date = st.sidebar.date_input("Start Date")
            end_date = st.sidebar.date_input("End Date")
            search_criteria = f'(SINCE "{start_date.strftime("%d-%b-%Y")}" BEFORE "{end_date.strftime("%d-%b-%Y")}")'
        elif date_option == "Year 2022":
            search_criteria = '(SINCE "01-Jan-2022" BEFORE "01-Jan-2023")'
        else:
            days = {"Last 30 Days": 30, "Last 90 Days": 90, "Last Year": 365}
            date_ago = (datetime.now() - timedelta(days=days[date_option])).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{date_ago}")'
        
        # Email source selector
        sources = st.sidebar.multiselect(
            "Select Email Sources",
            ["noreply@swiggy.in", "order-update@amazon.in", "orders@zomato.com"],
            default=["noreply@swiggy.in"]
        )
        
        # Analysis button
        if st.sidebar.button("Analyze Emails"):
            with st.spinner("Analyzing emails..."):
                parser = EmailParser(st.session_state.email, st.session_state.password)
                all_data = []
                
                for sender in sources:
                    data = parser.parse_emails(
                        sender_email=sender,
                        search_criteria=search_criteria
                    )
                    all_data.extend(data)
                
                if all_data:
                    analyze_data(all_data)
                else:
                    st.warning("No order information found for the selected criteria.")

if __name__ == "__main__":
    main()
