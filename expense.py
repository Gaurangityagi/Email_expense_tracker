import streamlit as st
import pandas as pd
from email_processing import EmailParser, EmailMonitor
from datetime import datetime, timedelta
import plotly.express as px
import time
from typing import Optional, Dict, List
import hashlib
import logging 
# Configuration
st.set_page_config(
    page_title="OrderInbox",
    page_icon="📧",
    layout="wide"
)

# Constants
SOURCE_MAP = {
    "Swiggy": "noreply@swiggy.in",
    "Zomato": "noreply@zomato.com",
    "Amazon": "auto-confirm@amazon.in",
    "Domino's": "do-not-reply@dominos.co.in",
    "BookMyShow": "tickets@bookmyshow.email"
}

# Session State Management
def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
    if 'monitor' not in st.session_state:
        st.session_state.monitor = None
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'cache' not in st.session_state:
        st.session_state.cache = {}

# Authentication
def check_authenticated() -> bool:
    """Check if user session is still valid"""
    if st.session_state.get('authenticated', False):
        if 'last_auth_time' in st.session_state:
            # Session expires after 8 hours
            if (datetime.now() - st.session_state.last_auth_time).seconds < 28800:
                return True
    return False

def authenticate() -> bool:
    """Handle user authentication with session persistence"""
    if check_authenticated():
        return True
        
    with st.container():
        st.title("📧 Email Order Analysis")
        
        with st.form("email_form"):
            email = st.text_input("Email Address", placeholder="your@email.com")
            password = st.text_input("App Password", type="password", 
                                   placeholder="Enter your app password")
            remember = st.checkbox("Keep me logged in", value=True)
            submitted = st.form_submit_button("Login")
            
            if submitted and email and password:
                parser = EmailParser(email, password)
                if parser.connect():
                    st.session_state.authenticated = True
                    st.session_state.email = email
                    st.session_state.password = password
                    st.session_state.last_auth_time = datetime.now()
                    st.session_state.remember = remember
                    
                    # Initialize email monitor
                    st.session_state.monitor = EmailMonitor(email, password)
                    st.session_state.monitor.start_monitoring()
                    
                    st.success("Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Authentication failed. Please check your credentials.")
    
    return False

# Caching Utilities
def get_cache_key(*args) -> str:
    """Generate consistent cache key from arguments"""
    return hashlib.md5(str(args).encode()).hexdigest()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_email_data(email: str, password: str, search_criteria: str, sender_email: str = None) -> List[Dict]:
    """Cached email data fetching"""
    parser = EmailParser(email, password)
    return parser.parse_emails(
        sender_email=sender_email,
        search_criteria=search_criteria
    )

# Analysis Components
class OrderAnalyzer:
    def __init__(self, data: List[Dict]):
        """Initialize with order data and set up logger"""
        self.logger = logging.getLogger(__name__)
        try:
            self.df = pd.DataFrame(data)
            self._clean_data()
        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            raise

    def _clean_data(self) -> None:
        """Clean and prepare data for analysis with robust error handling"""
        try:
            # Convert and validate dates
            self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
            invalid_dates = self.df['date'].isna()
            if invalid_dates.any():
                self.logger.warning(f"Dropped {invalid_dates.sum()} rows with invalid dates")
            
            # Clean and validate amounts
            self.df['amount'] = (
                pd.to_numeric(self.df['amount'], errors='coerce')
                .replace([np.inf, -np.inf], np.nan)
            )
            invalid_amounts = self.df['amount'].isna()
            if invalid_amounts.any():
                self.logger.warning(f"Dropped {invalid_amounts.sum()} rows with invalid amounts")
            
            # Final cleanup
            self.df = self.df.dropna(subset=['date', 'amount'])
            self.df['year_month'] = self.df['date'].dt.to_period('M').astype(str)
            self.df['day_of_week'] = self.df['date'].dt.day_name()
            
        except Exception as e:
            self.logger.error(f"Data cleaning failed: {str(e)}")
            raise

    def generate_report(self, budget: Optional[float] = None) -> Dict:
        """Generate complete analysis report with error handling"""
        try:
            report = {
                'summary': self._get_summary_stats(),
                'monthly': self._monthly_analysis(budget),
                'vendors': self._vendor_analysis(),
                'time_series': self._time_series_analysis(),
                'raw_data': self._get_safe_dataframe()
            }
            return report
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {'error': str(e)}

    def _get_summary_stats(self) -> Dict:
        """Calculate key summary statistics with validation"""
        try:
            stats = {
                'total_spent': float(self.df['amount'].sum()),
                'average_order': float(self.df['amount'].mean()),
                'median_order': float(self.df['amount'].median()),
                'order_count': int(len(self.df)),
                'date_range': {
                    'start': self.df['date'].min().isoformat(),
                    'end': self.df['date'].max().isoformat()
                }
            }
            return stats
        except Exception as e:
            self.logger.error(f"Summary stats calculation failed: {str(e)}")
            raise

    def _monthly_analysis(self, budget: Optional[float]) -> Dict:
        """Enhanced monthly analysis with budget tracking"""
        try:
            monthly = self.df.groupby('year_month').agg(
                total_spent=('amount', 'sum'),
                order_count=('amount', 'count')
            ).reset_index()
            
            fig = px.line(
                monthly,
                x='year_month',
                y='total_spent',
                title='Monthly Spending Trend',
                labels={'total_spent': 'Amount (₹)', 'year_month': 'Month'},
                template='plotly_white'
            ).update_layout(
                xaxis_title='Month',
                yaxis_title='Amount Spent (₹)',
                hovermode='x unified'
            )
            
            result = {'monthly_fig': fig}
            
            if budget and not monthly.empty:
                current_month = datetime.now().strftime('%Y-%m')
                current = monthly[monthly['year_month'] == current_month]
                
                if not current.empty:
                    spent = float(current['total_spent'].iloc[0])
                    remaining = max(float(budget) - spent, 0.0)
                    percentage = (spent / float(budget)) * 100
                    
                    budget_fig = px.pie(
                        names=['Spent', 'Remaining'],
                        values=[spent, remaining],
                        title=f'Budget Usage ({percentage:.1f}%)',
                        color_discrete_sequence=['#FF6961', '#77DD77']
                    ).update_traces(
                        textinfo='percent+label',
                        hoverinfo='label+value'
                    )
                    
                    result.update({
                        'budget_fig': budget_fig,
                        'budget_metrics': {
                            'spent': spent,
                            'remaining': remaining,
                            'percentage': percentage
                        }
                    })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Monthly analysis failed: {str(e)}")
            return {'error': str(e)}

    def _vendor_analysis(self) -> Dict:
        """Vendor analysis with improved visualization"""
        try:
            if 'company' not in self.df.columns:
                return {}
                
            vendors = self.df.groupby('company').agg(
                total_spent=('amount', 'sum'),
                order_count=('amount', 'count'),
                avg_order=('amount', 'mean')
            ).sort_values('total_spent', ascending=False)
            
            fig = px.bar(
                vendors.reset_index(),
                x='company',
                y='total_spent',
                title='Spending by Vendor',
                color='total_spent',
                color_continuous_scale='Bluered',
                labels={'total_spent': 'Total Amount (₹)', 'company': 'Vendor'},
                hover_data=['avg_order', 'order_count']
            ).update_layout(
                xaxis_title='Vendor',
                yaxis_title='Total Amount Spent (₹)',
                coloraxis_showscale=False
            )
            
            return {
                'vendor_fig': fig,
                'vendor_data': vendors
            }
            
        except Exception as e:
            self.logger.error(f"Vendor analysis failed: {str(e)}")
            return {'error': str(e)}

    def _time_series_analysis(self) -> Dict:
        """Enhanced time series analysis"""
        try:
            weekly = self.df.groupby('day_of_week').agg(
                total_spent=('amount', 'sum'),
                order_count=('amount', 'count')
            ).reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                     'Friday', 'Saturday', 'Sunday'])
            
            fig = px.bar(
                weekly.reset_index(),
                x='day_of_week',
                y='total_spent',
                title='Spending by Day of Week',
                color='total_spent',
                color_continuous_scale='Viridis',
                labels={'total_spent': 'Amount (₹)', 'day_of_week': 'Day'}
            ).update_layout(
                xaxis_title='Day of Week',
                yaxis_title='Total Amount Spent (₹)',
                coloraxis_showscale=False
            )
            
            return {
                'weekly_fig': fig,
                'weekly_data': weekly
            }
            
        except Exception as e:
            self.logger.error(f"Time series analysis failed: {str(e)}")
            return {'error': str(e)}

    def _get_safe_dataframe(self) -> pd.DataFrame:
        """Return a display-safe version of the dataframe"""
        try:
            display_df = self.df.sort_values('date', ascending=False).copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].round(2)
            return display_df
        except Exception as e:
            self.logger.error(f"Dataframe preparation failed: {str(e)}")
            return pd.DataFrame()

# Main App Views
def order_analysis_view():
    """View for order analysis dashboard"""
    st.title("Order Analysis Dashboard")
    
    # Date range selector
    date_option = st.sidebar.selectbox(
        "Date Range",
        ["Last 30 Days", "Last 90 Days", "Last Year", "Custom Range"]
    )
    
    if date_option == "Custom Range":
        start_date = st.sidebar.date_input("Start Date")
        end_date = st.sidebar.date_input("End Date")
        search_criteria = f'(SINCE "{start_date.strftime("%d-%b-%Y")}" BEFORE "{end_date.strftime("%d-%b-%Y")}")'
    else:
        days = {"Last 30 Days": 30, "Last 90 Days": 90, "Last Year": 365}
        date_ago = (datetime.now() - timedelta(days=days[date_option])).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{date_ago}")'
    
    # Vendor selection
    vendors = st.sidebar.multiselect(
        "Select Vendors",
        options=list(SOURCE_MAP.keys())
    )
    
    # Get cached data or fetch fresh
    cache_key = get_cache_key(
        st.session_state.email,
        search_criteria,
        tuple(sorted(vendors))
    )
    
    if cache_key not in st.session_state.cache:
        with st.spinner("Loading email data..."):
            all_data = []
            for name in vendors:
                data = get_email_data(
                    st.session_state.email,
                    st.session_state.password,
                    search_criteria,
                    SOURCE_MAP[name]
                )
                for item in data:
                    item['company'] = name
                all_data.extend(data)
            
            st.session_state.cache[cache_key] = all_data
    
    # Check for new emails
    if st.session_state.monitor and st.session_state.monitor.new_emails:
        new_data = []
        for email in st.session_state.monitor.new_emails:
            if any(vendor in email['sender'] for vendor in [SOURCE_MAP[v] for v in vendors]):
                new_data.append(email)
        
        if new_data:
            st.session_state.cache[cache_key].extend(new_data)
            st.session_state.monitor.new_emails = []
            st.session_state.last_update = datetime.now()
            st.toast(f"Added {len(new_data)} new orders", icon="📧")
    
    # Display analysis
    if st.session_state.cache[cache_key]:
        analyzer = OrderAnalyzer(st.session_state.cache[cache_key])
        report = analyzer.generate_report()
        
        # Summary metrics
        cols = st.columns(3)
        cols[0].metric("Total Spent", f"₹{report['summary']['total_spent']:.2f}")
        cols[1].metric("Average Order", f"₹{report['summary']['average_order']:.2f}")
        cols[2].metric("Total Orders", report['summary']['order_count'])
        
        # Visualizations
        st.plotly_chart(report['monthly']['monthly_fig'], use_container_width=True)
        
        col1, col2 = st.columns(2)
        if 'budget_fig' in report['monthly']:
            col1.plotly_chart(report['monthly']['budget_fig'])
        if 'vendor_fig' in report['vendors']:
            col2.plotly_chart(report['vendors']['vendor_fig'])
        
        # Raw data
        st.subheader("Order Details")
        st.dataframe(report['raw_data'])
    else:
        st.warning("No order data found for selected criteria")

def budget_tracker_view():
    """View for budget tracking"""
    st.title("Monthly Budget Tracker")
    
    # Budget input
    budget = st.sidebar.number_input(
        "Monthly Budget (₹)", 
        min_value=0.0, 
        value=5000.0,
        step=100.0
    )
    
    # Vendor selection
    vendors = st.sidebar.multiselect(
        "Track Vendors", 
        options=list(SOURCE_MAP.keys()),
        default=list(SOURCE_MAP.keys())
    )
    
    # Get current month data
    current_month = datetime.now().strftime('%Y-%m')
    search_criteria = f'(SINCE "01-{datetime.now().strftime("%b-%Y")}")'
    
    cache_key = get_cache_key(
        st.session_state.email,
        search_criteria,
        tuple(sorted(vendors))
    )
    
    if cache_key not in st.session_state.cache:
        with st.spinner("Loading current month data..."):
            all_data = []
            for name in vendors:
                data = get_email_data(
                    st.session_state.email,
                    st.session_state.password,
                    search_criteria,
                    SOURCE_MAP[name]
                )
                for item in data:
                    item['company'] = name
                all_data.extend(data)
            
            st.session_state.cache[cache_key] = all_data
    
    # Check for new emails
    if st.session_state.monitor and st.session_state.monitor.new_emails:
        new_data = []
        for email in st.session_state.monitor.new_emails:
            if any(vendor in email['sender'] for vendor in [SOURCE_MAP[v] for v in vendors]):
                new_data.append(email)
        
        if new_data:
            st.session_state.cache[cache_key].extend(new_data)
            st.session_state.monitor.new_emails = []
            st.session_state.last_update = datetime.now()
            st.toast(f"Added {len(new_data)} new orders", icon="📧")
    
    # Display budget analysis
    if st.session_state.cache[cache_key]:
        analyzer = OrderAnalyzer(st.session_state.cache[cache_key])
        report = analyzer.generate_report(budget)
        
        # Budget metrics
        if 'budget_metrics' in report['monthly']:
            spent = report['monthly']['budget_metrics']['spent']
            remaining = report['monthly']['budget_metrics']['remaining']
            percentage = (spent / budget) * 100
            
            cols = st.columns(3)
            cols[0].metric("Budget", f"₹{budget:.2f}")
            cols[1].metric("Spent", f"₹{spent:.2f}", f"{percentage:.1f}%")
            cols[2].metric("Remaining", f"₹{remaining:.2f}")
            
            # Budget alert
            if percentage >= 90:
                st.error("⚠️ You've used 90% or more of your budget!")
            elif percentage >= 80:
                st.warning("⚠️ You've used 80% or more of your budget!")
            
            st.plotly_chart(report['monthly']['budget_fig'])
        
        # Vendor breakdown
        if 'vendor_fig' in report['vendors']:
            st.plotly_chart(report['vendors']['vendor_fig'])
        
        # Recent orders
        st.subheader("Recent Orders This Month")
        st.dataframe(report['raw_data'])
    else:
        st.info("No orders found for current month")

# Main App Function
def main():
    """Main application function"""
    init_session_state()
    
    # Check session timeout
    if st.session_state.get('authenticated', False):
        current_time = time.time()
        if current_time - st.session_state.last_activity > 3600:  # 1 hour
            st.warning("Session expired due to inactivity")
            st.session_state.authenticated = False
            st.rerun()
        st.session_state.last_activity = current_time
    
    # Authentication
    if not authenticate():
        return
    
    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Order Analysis", "Track and set limit"],
        label_visibility="collapsed"
    )
    
    # Last update indicator
    if st.session_state.last_update:
        st.sidebar.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M')}")
    
    # Force refresh button
    if st.sidebar.button("Check for new emails"):
        st.rerun()
    
    # Logout button
    if st.sidebar.button("Logout"):
        if st.session_state.monitor:
            st.session_state.monitor.stop_monitoring()
        st.session_state.clear()
        st.rerun()
    
    # Display selected page
    if page == "Order Analysis":
        order_analysis_view()
    else:
        budget_tracker_view()

if __name__ == "__main__":
    main()
