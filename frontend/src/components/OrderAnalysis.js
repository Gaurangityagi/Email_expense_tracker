import React, { useState } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';

function OrderAnalysis({ credentials }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dateOption, setDateOption] = useState('Last 30 Days');
  const [sources, setSources] = useState([]);

  const API = process.env.REACT_APP_BACKEND_URL;

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
      const response = await axios.post(`${API}/analyze_emails`, {
        email: credentials.email,
        password: credentials.password,
        sources,
        date_option: dateOption
      });

      if (response.data.success) {
        setData(response.data);
      } else {
        setError(response.data.message);
      }
    } catch (err) {
      setError('Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="order-analysis">
      <h2>Email Order Analysis</h2>

      <div className="controls">
        <select value={dateOption} onChange={(e) => setDateOption(e.target.value)}>
          <option>Last 30 Days</option>
          <option>Last 90 Days</option>
          <option>Last Year</option>
          <option>Year 2024</option>
        </select>

        <div>
          {sourceOptions.map(option => (
            <label key={option.value}>
              <input
                type="checkbox"
                checked={sources.includes(option.value)}
                onChange={() => handleSourceChange(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>

        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default OrderAnalysis;
