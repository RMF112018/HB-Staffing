import React, { useState } from 'react';

const Forecasts = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('next-month');

  const forecastData = [
    { period: 'Next Week', required: 15, available: 12, gap: -3 },
    { period: 'Next Month', required: 25, available: 20, gap: -5 },
    { period: 'Next Quarter', required: 35, available: 28, gap: -7 },
    { period: 'Next 6 Months', required: 45, available: 38, gap: -7 },
  ];

  return (
    <div className="forecasts">
      <h1>Staffing Forecasts</h1>

      <div className="forecast-controls">
        <label htmlFor="period">Forecast Period:</label>
        <select
          id="period"
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
        >
          <option value="next-week">Next Week</option>
          <option value="next-month">Next Month</option>
          <option value="next-quarter">Next Quarter</option>
          <option value="next-6-months">Next 6 Months</option>
        </select>

        <button className="btn-primary">Generate New Forecast</button>
      </div>

      <div className="forecast-chart">
        <h2>Staffing Requirements vs Availability</h2>
        <div className="chart-placeholder">
          <p>Chart visualization would go here</p>
          <p>Integration with Chart.js for forecasting charts</p>
        </div>
      </div>

      <div className="forecast-table">
        <h2>Detailed Forecast Data</h2>
        <table>
          <thead>
            <tr>
              <th>Period</th>
              <th>Staff Required</th>
              <th>Staff Available</th>
              <th>Gap</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {forecastData.map((item, index) => (
              <tr key={index}>
                <td>{item.period}</td>
                <td>{item.required}</td>
                <td>{item.available}</td>
                <td className={item.gap < 0 ? 'negative' : 'positive'}>
                  {item.gap > 0 ? '+' : ''}{item.gap}
                </td>
                <td>
                  <span className={`status ${item.gap < 0 ? 'warning' : 'good'}`}>
                    {item.gap < 0 ? 'Shortage' : 'Adequate'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="forecast-recommendations">
        <h2>Recommendations</h2>
        <ul>
          <li>Hire 5 additional construction workers for the next month</li>
          <li>Consider overtime for existing staff during peak periods</li>
          <li>Review project timelines to optimize resource allocation</li>
          <li>Cross-train staff for multiple roles to increase flexibility</li>
        </ul>
      </div>
    </div>
  );
};

export default Forecasts;