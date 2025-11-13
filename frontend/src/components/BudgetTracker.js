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

  const sourceOptions = [
    { value: 'Swiggy', label: 'Swiggy' },
    { value: 'Zomato', label: 'Zomato' },
    { value: 'Amazon Auto', label: 'Amazon Auto' },
    { value: 'Domino\'s', label: 'Domino\'s' },
    { value: 'BookMyShow', label: 'BookMyShow' }
  ];

  // Save to localStorage when budget or sources change
  useEffect(() => {
    localStorage.setItem('budget', budget);
  }, [budget]);

  useEffect(() => {
    localStorage.setItem('sources', JSON.stringify(sources));
  }, [sources]);

  // Fetch real-time data on mount and every 5 minutes
  useEffect(() => {
    const fetchExpenses = async () => {
      if (!credentials.email) return;

      try {
        const response = await axios.post('http://localhost:5000/get_monthly_expenses', {
          email: credentials.email
        });

        if (response.data.success) {
          setData(response.data.data);
          setIsMonitoring(true);
        }
      } catch (err) {
        // If no data available, that's okay for initial load
        console.log('No expense data available yet');
      }
    };

    fetchExpenses();
    const interval = setInterval(fetchExpenses, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(interval);
  }, [credentials.email]);

  const handleSourceChange = (source) => {
    setSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  const handleSetBudget = async () => {
    if (!budget || sources.length === 0) {
      setError('Please enter budget and select at least one source');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/set_budget', {
        email: credentials.email,
        password: credentials.password,
        sources,
        budget: parseFloat(budget)
      });

      if (response.data.success) {
        setIsMonitoring(true);
        // Fetch updated data immediately
        const expenseResponse = await axios.post('http://localhost:5000/get_monthly_expenses', {
          email: credentials.email
        });
        if (expenseResponse.data.success) {
          setData(expenseResponse.data.data);
        }
      } else {
        setError(response.data.message || 'Failed to set budget');
      }
    } catch (err) {
      setError('Failed to set budget. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendAlert = async () => {
    if (!isMonitoring) {
      setError('Please set up budget monitoring first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/send_budget_alert', {
        email: credentials.email,
        password: credentials.password
      });

      if (response.data.success) {
        setError('Budget alert sent successfully!');
      } else {
        setError(response.data.message || 'Failed to send alert');
      }
    } catch (err) {
      setError('Failed to send alert. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const getBudgetStatus = () => {
    if (!data) return null;

    const percentage = data.percentage_spent;
    if (percentage >= 100) {
      return { status: 'exceeded', message: `❌ You have exceeded your monthly budget by ₹${(data.total_spent - data.budget).toFixed(2)}!` };
    } else if (percentage >= 80) {
      return { status: 'warning', message: `⚠️ You have used ${percentage.toFixed(1)}% of your monthly budget!` };
    }
    return { status: 'good', message: `✅ You're within budget (${percentage.toFixed(1)}% used)` };
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
            placeholder="Enter your monthly limit"
          />
        </div>

        <div className="control-group">
          <label>Sources:</label>
          <div className="source-checkboxes">
            {sourceOptions.map(option => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={sources.includes(option.value)}
                  onChange={() => handleSourceChange(option.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        <div className="button-group">
          <button onClick={handleSetBudget} disabled={loading}>
            {loading ? 'Setting Budget...' : 'Set Budget & Start Monitoring'}
          </button>
          {isMonitoring && (
            <button onClick={handleSendAlert} disabled={loading}>
              {loading ? 'Sending...' : 'Send Budget Alert'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {data && (
        <div className="results">
          {budgetStatus && (
            <div className={`budget-alert ${budgetStatus.status}`}>
              {budgetStatus.message}
            </div>
          )}

          <div className="summary-stats">
            <div className="stat-card">
              <h3>Budget Limit</h3>
              <p>₹{data.budget?.toFixed(2)}</p>
            </div>
            <div className="stat-card">
              <h3>Total Spent</h3>
              <p>₹{data.total_spent?.toFixed(2)}</p>
            </div>
            <div className="stat-card">
              <h3>Remaining</h3>
              <p>₹{data.remaining?.toFixed(2)}</p>
            </div>
          </div>

          <div className="charts">
            <div className="chart">
              <h3>Monthly Budget Usage</h3>
              <Plot
                data={[{
                  values: [data.total_spent, data.remaining],
                  labels: ['Spent', 'Remaining'],
                  type: 'pie',
                  marker: {
                    colors: ['#ff6b6b', '#4ecdc4']
                  }
                }]}
                layout={{
                  title: 'Monthly Budget Usage'
                }}
              />
            </div>
          </div>

          <div className="data-table">
            <h3>This Month's Orders</h3>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Subject</th>
                  <th>Sender</th>
                  <th>Company</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {data.data?.map((item, index) => (
                  <tr key={index}>
                    <td>{new Date(item.date).toLocaleDateString()}</td>
                    <td>{item.subject}</td>
                    <td>{item.sender}</td>
                    <td>{item.company}</td>
                    <td>₹{item.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default BudgetTracker;
