import React, { useState } from "react";
import axios from "axios";
import Plot from "react-plotly.js";

function OrderAnalysis({ credentials }) {
  const [sources, setSources] = useState([]);
  const [dateOption, setDateOption] = useState("Last 30 Days");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API = process.env.REACT_APP_BACKEND_URL;

  const sourceOptions = [
    "Swiggy",
    "Zomato",
    "Amazon Auto",
    "Domino's",
    "BookMyShow",
  ];

  const toggleSource = (src) => {
    setSources((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };

  const handleAnalyze = async () => {
    if (sources.length === 0) {
      setError("Select at least 1 source");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await axios.post(`${API}/analyze_emails`, {
        email: credentials.email,
        password: credentials.password,
        sources,
        date_option: dateOption,
      });

      if (response.data.success) {
        setData(response.data);
      } else {
        setError(response.data.message);
      }
    } catch {
      setError("Backend connection failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis">
      <h2>Email Order Analysis</h2>

      <select value={dateOption} onChange={(e) => setDateOption(e.target.value)}>
        <option>Last 30 Days</option>
        <option>Last 90 Days</option>
        <option>Last Year</option>
        <option>Year 2024</option>
      </select>

      <div className="sources">
        {sourceOptions.map((s) => (
          <label key={s}>
            <input
              type="checkbox"
              checked={sources.includes(s)}
              onChange={() => toggleSource(s)}
            />
            {s}
          </label>
        ))}
      </div>

      <button disabled={loading} onClick={handleAnalyze}>
        {loading ? "Analyzing..." : "Analyze"}
      </button>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <Plot
            data={[
              {
                x: data.monthly_spending?.map((v) => v.date),
                y: data.monthly_spending?.map((v) => v.amount),
                type: "scatter",
                mode: "lines+markers",
              },
            ]}
            layout={{ title: "Monthly Spending Trend" }}
          />

          <Plot
            data={[
              {
                values: data.sender_spending?.map((v) => v.amount),
                labels: data.sender_spending?.map((v) => v.company),
                type: "pie",
              },
            ]}
            layout={{ title: "Spending by Source" }}
          />
        </>
      )}
    </div>
  );
}

export default OrderAnalysis;
