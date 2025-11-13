import React, { useState } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';

function OrderAnalysis({ credentials }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dateOption, setDateOption] = useState('Last 30 Days');
  const [sources, setSources] = useState([]);

  const sourceOptions = [
    { value: 'Swiggy', label: 'Swiggy' },
    { value: 'Zomato', label: 'Zomato' },
    { value: 'Amazon Auto', label: 'Amazon Auto' },
    { value: 'Domino\'s', label: 'Domino\'s' },
    { value: 'BookMyShow', label: 'BookMyShow' }
  ];

  const handleSourceChange = (source) => {
    setSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  const handleAnalyze = async () => {
    if (sources.length === 0) {
      setError('Please select at least one source');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/analyze_emails', {
        email: credentials.email,
        password: credentials.password,
        sources,
        date_option: dateOption
      });

      if (response.data.success) {
        setData(response.data);
      } else {
        setError(response.data.message || 'Analysis failed');
      }
    } catch (err) {
      setError('Failed to analyze emails. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="order-analysis">
      <h2>Email Order Analysis</h2>

      <div className="controls">
        <div className="control-group">
          <label>Date Range:</label>
          <select value={dateOption} onChange={(e) => setDateOption(e.target.value)}>
            <option>Last 30 Days</option>
            <option>Last 90 Days</option>
            <option>Last Year</option>
            <option>Year 2024</option>
          </select>
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

        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze Emails'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {data && (
        <div className="results">
          <div className="summary-stats">
            <div className="stat-card">
              <h3>Total Spent</h3>
              <p>₹{data.total_spent?.toFixed(2)}</p>
            </div>
            <div className="stat-card">
              <h3>Average Order</h3>
              <p>₹{data.average_order?.toFixed(2)}</p>
            </div>
            <div className="stat-card">
              <h3>Total Orders</h3>
              <p>{data.total_orders}</p>
            </div>
          </div>

          <div className="charts">
            <div className="chart">
              <h3>Monthly Spending Trend</h3>
              <Plot
                data={[{
                  x: data.monthly_spending?.map(item => item.date),
                  y: data.monthly_spending?.map(item => item.amount),
                  type: 'line',
                  mode: 'lines+markers'
                }]}
                layout={{
                  title: 'Monthly Spending Trend',
                  xaxis: { title: 'Month' },
                  yaxis: { title: 'Total Amount (₹)' }
                }}
              />
            </div>

            <div className="chart">
              <h3>Spending by Source</h3>
              <Plot
                data={[{
                  values: data.sender_spending?.map(item => item.amount),
                  labels: data.sender_spending?.map(item => item.company),
                  type: 'pie'
                }]}
                layout={{
                  title: 'Spending by Source'
                }}
              />
            </div>
          </div>

          <div className="data-table">
            <h3>Order Details</h3>
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

export default OrderAnalysis;
