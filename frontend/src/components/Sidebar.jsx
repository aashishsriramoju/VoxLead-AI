// components/Sidebar.jsx – Live qualification lead card & appointment banner
import React from "react";

export default function Sidebar({ lead, appointment }) {
  const score = lead?.score || 0;
  const status = (lead?.status || "cold").toLowerCase();

  const getStatusBadge = () => {
    if (status === "hot") {
      return <span className="status-badge badge-hot">🔥 Hot Lead</span>;
    } else if (status === "warm") {
      return <span className="status-badge badge-warm">⚡ Warm Lead</span>;
    }
    return <span className="status-badge badge-cold">❄️ Cold Lead</span>;
  };

  const getScoreColor = () => {
    if (score >= 70) return "#10b981"; // green
    if (score >= 40) return "#f59e0b"; // amber
    return "#3b82f6"; // blue
  };

  return (
    <div className="sidebar-container">
      {/* Live Lead Card */}
      <div className="lead-card">
        <div className="lead-header">
          <h3>🎯 Lead Qualification</h3>
          {getStatusBadge()}
        </div>

        {/* Lead Score Progress */}
        <div className="score-section">
          <div className="score-meta">
            <span className="score-label">Qualification Score:</span>
            <span className="score-val" style={{ color: getScoreColor() }}>
              {Math.round(score)} / 100
            </span>
          </div>
          <div className="score-bar-bg">
            <div
              className="score-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, score))}%`,
                backgroundColor: getScoreColor(),
              }}
            ></div>
          </div>
        </div>

        {/* Extracted Fields */}
        <div className="lead-fields-grid">
          <div className="field-item">
            <label>Name:</label>
            <span>{lead?.name || "—"}</span>
          </div>
          <div className="field-item">
            <label>Phone:</label>
            <span>{lead?.phone || "—"}</span>
          </div>
          <div className="field-item">
            <label>Company:</label>
            <span>{lead?.company || "—"}</span>
          </div>
          <div className="field-item">
            <label>Budget:</label>
            <span>{lead?.budget ? `₹${Number(lead.budget).toLocaleString('en-IN')}/mo` : "—"}</span>
          </div>
          <div className="field-item">
            <label>Team Size:</label>
            <span>{lead?.team_size ? `${lead.team_size} users` : "—"}</span>
          </div>
          <div className="field-item">
            <label>Timeline:</label>
            <span>
              {lead?.timeline_days ? `Within ${lead.timeline_days} days` : "—"}
            </span>
          </div>
          <div className="field-item full-width">
            <label>Requirements:</label>
            <p className="requirements-text">
              {lead?.requirements || "Not yet stated"}
            </p>
          </div>
        </div>
      </div>

      {/* Appointment Confirmation Banner */}
      {appointment && (
        <div className="appointment-card">
          <div className="appointment-header">
            <h4>📅 Demo Appointment Booked!</h4>
            <span className="appointment-status">Confirmed</span>
          </div>
          <p className="appointment-time">
            <strong>Time:</strong>{" "}
            {new Date(appointment.slot_start).toLocaleString('en-IN', {
              weekday: 'long',
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
              hour12: true
            })}
          </p>
          <p className="appointment-note">
            Lead #{appointment.lead_id} • Calendar invite sent.
          </p>
        </div>
      )}
    </div>
  );
}
