import React, { useState, useEffect } from "react";
import axios from "axios";
import Plot from "react-plotly.js";

function BudgetTracker({ credentials }) {
  const [budget, setBudget] = useState(localStorage.getItem("budget") || "");
  const [sources, setSources] = useState(
    JSON.parse(localStorage.getItem("sources") || "[]")
  );
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [alertSent, setAlertSent] = useState(false);

  const API = process.env.REACT_APP_BACKEND_URL;

  const sourceOptions = [
    "Swiggy",
    "Zomato",
    "Amazon Auto",
    "Domino's",
    "BookMyShow",
  ];

  useEffect(() => {
    localStorage.setItem("budget", budget);
  }, [budget]);

  useEffect(() => {
    localStorage.setItem("sources", JSON.stringify(sources));
  }, [sources]);

  useEffect(() => {
    const fetchExpenses = async () => {
      try {
        const response = await axios.post(`${API}/get_monthly_expenses`, {
          email: credentials.email,
        });

        if (response.data.success) {
          setData(response.data.data);
          checkBudgetAlert(response.data.data);
        }
      } catch {
        console.log("No data yet");
      }
    };

    fetchExpenses();
  }, [credentials.email, API]);

  const checkBudgetAlert = (budgetData) => {
    if (!budget || !budgetData) return;

    const percentageSpent = (budgetData.total_spent / parseFloat(budget)) * 100;

    if (percentageSpent >= 80 && percentageSpent < 100 && !alertSent) {
      sendBudgetAlert(percentageSpent);
    } else if (percentageSpent >= 100) {
      setError(`❌ You have exceeded your monthly budget by ₹${(budgetData.total_spent - parseFloat(budget)).toFixed(2)}!`);
    }
  };

  const sendBudgetAlert = async (percentage) => {
    try {
      const response = await axios.post(`${API}/send_budget_alert`, {
        email: credentials.email,
        password: credentials.password,
        percentage: percentage.toFixed(1),
      });

      if (response.data.success) {
        setAlertSent(true);
        setError(`⚠️ You have used ${percentage.toFixed(1)}% of your monthly budget! Alert email sent.`);
      }
    } catch (err) {
      console.error("Failed to send alert:", err);
      setError(`⚠️ You have used ${percentage.toFixed(1)}% of your monthly budget! (Failed to send email alert)`);
    }
  };

  const toggleSource = (src) => {
    setSources((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };

  const handleSetBudget = async () => {
    if (!budget || sources.length === 0) {
      setError("Enter budget and select sources");
      return;
    }

    setLoading(true);
    setError("");
    setAlertSent(false);

    try {
      await axios.post(`${API}/set_budget`, {
        email: credentials.email,
        password: credentials.password,
        sources,
        budget: parseFloat(budget),
      });

      const res = await axios.post(`${API}/get_monthly_expenses`, {
        email: credentials.email,
      });

      if (res.data.success) {
        setData(res.data.data);
        checkBudgetAlert(res.data.data);
      }
    } catch {
      setError("Failed to set budget.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis">
      <h2>💰 Monthly Budget Tracker</h2>

      <div className="controls">
        <div className="form-group">
          <label>Monthly Budget Limit (₹):</label>
          <input
            type="number"
            value={budget}
            placeholder="Enter your monthly limit"
            onChange={(e) => setBudget(e.target.value)}
            className="budget-input"
          />
        </div>

        <div className="form-group">
          <label>Select Sources to Track:</label>
          <div className="source-checkboxes">
            {sourceOptions.map((s) => (
              <label key={s} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={sources.includes(s)}
                  onChange={() => toggleSource(s)}
                />
                <span className="checkmark"></span>
                {s}
              </label>
            ))}
          </div>
        </div>

        <button onClick={handleSetBudget} disabled={loading} className="analyze-btn">
          {loading ? "💾 Saving..." : "💰 Set Budget & Track"}
        </button>
      </div>

      {error && (
        <div className={`budget-alert ${error.includes('exceeded') ? 'exceeded' : 'warning'}`}>
          {error}
        </div>
      )}

      {data && budget && (
        <>
          <div className="charts">
            <div className="chart">
              <h3>📊 Monthly Budget Usage</h3>
              <Plot
                data={[
                  {
                    values: [data.total_spent, Math.max(parseFloat(budget) - data.total_spent, 0)],
                    labels: ["Spent", "Remaining"],
                    type: "pie",
                    marker: {
                      colors: ['#ff6b6b', '#4ecdc4']
                    }
                  },
                ]}
                layout={{
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#333' }
                }}
                style={{ width: '100%', height: '400px' }}
              />
            </div>
          </div>

          <div className="summary-stats">
            <div className="stat-card">
              <h3>Budget Limit</h3>
              <p>₹{parseFloat(budget).toFixed(2)}</p>
            </div>
            <div className="stat-card">
              <h3>Total Spent</h3>
              <p>₹{data.total_spent?.toFixed(2) || 0}</p>
            </div>
            <div className="stat-card">
              <h3>Remaining</h3>
              <p>₹{Math.max(parseFloat(budget) - data.total_spent, 0).toFixed(2)}</p>
            </div>
          </div>

          <div className="expense-list">
            <h3>📋 This Month's Orders</h3>
            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Date</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {data.expenses?.map((expense, index) => (
                    <tr key={index}>
                      <td>{expense.company}</td>
                      <td>{expense.date}</td>
                      <td>₹{expense.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default BudgetTracker;
