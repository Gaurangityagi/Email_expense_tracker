import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';

function BudgetTracker({ credentials }) {
  const [budget, setBudget] = useState(() => localStorage.getItem('budget') || '');
  const [sources, setSources] = useState(() => {
    const saved = localStorage.getItem('sources');
    return saved ? JSON.parse(saved) : [];
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isMonitoring, setIsMonitoring] = useState(false);

  const API = process.env.REACT_APP_BACKEND_URL;

  const sourceOptions = [
    { value: 'Swiggy', label: 'Swiggy' },
    { value: 'Zomato', label: 'Zomato' },
    { value: 'Amazon Auto', label: 'Amazon Auto' },
    { value: 'Domino\'s', label: 'Domino\'s' },
    { value: 'BookMyShow', label: 'BookMyShow' }
  ];

  useEffect(() => {
    localStorage.setItem('budget', budget);
  }, [budget]);

  useEffect(() => {
    localStorage.setItem('sources', JSON.stringify(sources));
  }, [sources]);

  // fetch monthly expenses from backend
  useEffect(() => {
    const fetchExpenses = async () => {
      if (!credentials.email) return;

      try {
        const response = await axios.post(`${API}/get_monthly_expenses`, {
          email: credentials.email
        });

        if (response.data.success) {
          setData(response.data.data);
          setIsMonitoring(true);
        }
      } catch (err) {
        console.log("No expense data available");
      }
    };

    fetchExpenses();
    const interval = setInterval(fetchExpenses, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [credentials.email, API]);

  const handleSetBudget = async () => {
    if (!budget || sources.length === 0) {
      setError('Enter budget and select sources');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/set_budget`, {
        email: credentials.email,
        password: credentials.password,
        sources,
        budget: parseFloat(budget)
      });

      if (response.data.success) {
        setIsMonitoring(true);

        const expenseResponse = await axios.post(`${API}/get_monthly_expenses`, {
          email: credentials.email
        });

        if (expenseResponse.data.success) {
          setData(expenseResponse.data.data);
        }
      } else {
        setError(response.data.message);
      }
    } catch (err) {
      setError('Backend connection failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendAlert = async () => {
    if (!isMonitoring) {
      setError('Set budget first');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/send_budget_alert`, {
        email: credentials.email,
        password: credentials.password
      });

      if (response.data.success) {
        setError('Alert sent!');
      } else {
        setError(response.data.message);
      }
    } catch (err) {
      setError('Failed to send alert');
    } finally {
      setLoading(false);
    }
  };

  const getBudgetStatus = () => {
    if (!data) return null;

    const percentage = data.percentage_spent;
    if (percentage >= 100)
      return { status: 'exceeded', message: `❌ You exceeded your budget!` };
    if (percentage >= 80)
      return { status: 'warning', message: `⚠️ You used ${percentage.toFixed(1)}%` };
    return { status: 'good', message: `✅ You're within budget` };
  };

  const budgetStatus = getBudgetStatus();

  return (
    <div className="budget-tracker">
      <h2>Monthly Budget Tracker</h2>

      <div className="controls">
        <div className="control-group">
          <label>Monthly Budget (₹):</label>
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </div>

        <div className="control-group">
          <label>Sources:</label>
          <div className="source-checkboxes">
            {sourceOptions.map(option => (
              <label key={option.value}>
                <input
                  type="checkbox"
                  checked={sources.includes(option.value)}
                  onChange={() => {
                    setSources(prev =>
                      prev.includes(option.value)
                        ? prev.filter(s => s !== option.value)
                        : [...prev, option.value]
                    );
                  }}
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        <button onClick={handleSetBudget} disabled={loading}>
          {loading ? 'Setting...' : 'Set Budget'}
        </button>

        {isMonitoring && (
          <button onClick={handleSendAlert} disabled={loading}>
            {loading ? 'Sending...' : 'Send Budget Alert'}
          </button>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {data && (
        <div>
          <div className={`budget-alert ${budgetStatus.status}`}>
            {budgetStatus.message}
          </div>
        </div>
      )}
    </div>
  );
}

export default BudgetTracker;
