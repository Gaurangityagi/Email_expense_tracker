import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Login from './components/Login';
import OrderAnalysis from './components/OrderAnalysis';
import BudgetTracker from './components/BudgetTracker';

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [currentView, setCurrentView] = useState('analysis');
  const [monthlyTotal, setMonthlyTotal] = useState(0);
  const [isLoadingTotal, setIsLoadingTotal] = useState(false);

  const handleLogin = (email, password) => {
    setCredentials({ email, password });
    setAuthenticated(true);
  };

  const handleLogout = () => {
    setAuthenticated(false);
    setCredentials({ email: '', password: '' });
    setMonthlyTotal(0);
  };

  // Fetch monthly total when authenticated
  useEffect(() => {
    if (authenticated && credentials.email) {
      fetchMonthlyTotal();
      // Update every 5 minutes
      const interval = setInterval(fetchMonthlyTotal, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [authenticated, credentials.email]);

  const fetchMonthlyTotal = async () => {
    if (!credentials.email) return;

    setIsLoadingTotal(true);
    try {
      const response = await axios.post('http://localhost:5000/get_monthly_expenses', {
        email: credentials.email
      });

      if (response.data.success) {
        setMonthlyTotal(response.data.data.total_spent || 0);
      }
    } catch (err) {
      console.log('No expense data available yet');
    } finally {
      setIsLoadingTotal(false);
    }
  };

  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>📧 Email Order Analysis</h1>
        <div className="header-info">
          <div className="monthly-total">
            <span className="total-label">This Month:</span>
            <span className="total-amount">
              {isLoadingTotal ? '...' : `₹${monthlyTotal.toFixed(2)}`}
            </span>
          </div>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      <nav className="navigation">
        <button
          onClick={() => setCurrentView('analysis')}
          className={currentView === 'analysis' ? 'active' : ''}
        >
          Order Analysis
        </button>
        <button
          onClick={() => setCurrentView('budget')}
          className={currentView === 'budget' ? 'active' : ''}
        >
          Budget Tracker
        </button>
      </nav>

      <main>
        {currentView === 'analysis' ? (
          <OrderAnalysis credentials={credentials} />
        ) : (
          <BudgetTracker credentials={credentials} />
        )}
      </main>
    </div>
  );
}

export default App;
