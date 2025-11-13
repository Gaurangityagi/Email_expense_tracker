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
  const [isMonitoring, setIsMonitoring] = useState(false);

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
          setIsMonitoring(true);
        }
      } catch {
        console.log("No data yet");
      }
    };

    fetchExpenses();
  }, [credentials.email, API]);

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

      if (res.data.success) setData(res.data.data);

      setIsMonitoring(true);
    } catch {
      setError("Failed to set budget.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="budget-tracker">
      <h2>Budget Tracker</h2>

      <input
        type="number"
        value={budget}
        placeholder="Enter budget"
        onChange={(e) => setBudget(e.target.value)}
      />

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

      <button onClick={handleSetBudget} disabled={loading}>
        {loading ? "Saving..." : "Set Budget"}
      </button>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <Plot
            data={[
              {
                values: [data.total_spent, data.remaining],
                labels: ["Spent", "Remaining"],
                type: "pie",
              },
            ]}
            layout={{ title: "Budget Usage" }}
          />
        </>
      )}
    </div>
  );
}

export default BudgetTracker;
