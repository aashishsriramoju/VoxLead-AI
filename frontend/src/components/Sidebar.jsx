// components/Sidebar.jsx – Live lead qualification card & appointment confirmation
import React from "react";

export default function Sidebar({ lead, appointment }) {
  const score  = lead?.score  || 0;
  const status = (lead?.status || "cold").toLowerCase();

  const statusConfig = {
    hot:  { cls: "badge-hot",  label: "🔥 Hot Lead" },
    warm: { cls: "badge-warm", label: "⚡ Warm Lead" },
    cold: { cls: "badge-cold", label: "❄️ Cold Lead" },
  };
  const { cls, label } = statusConfig[status] || statusConfig.cold;

  const scoreColor =
    score >= 70 ? "var(--green)" :
    score >= 40 ? "var(--amber)" :
    "var(--cyan)";

  const fields = [
    { label: "Name",      value: lead?.name },
    { label: "Phone",     value: lead?.phone },
    { label: "Company",   value: lead?.company },
    { label: "Budget",    value: lead?.budget ? `₹${Number(lead.budget).toLocaleString("en-IN")}/mo` : null },
    { label: "Team Size", value: lead?.team_size ? `${lead.team_size} users` : null },
    { label: "Timeline",  value: lead?.timeline_days ? `${lead.timeline_days} days` : null },
  ];

  return (
    <div className="sidebar-container">
      {/* Lead Qualification Card */}
      <div className="lead-card">
        <div className="lead-header">
          <h3>🎯 Lead Qualification</h3>
          <span className={`status-badge ${cls}`}>{label}</span>
        </div>

        <div className="score-section">
          <div className="score-meta">
            <span className="score-label">Qualification Score</span>
            <span className="score-val" style={{ color: scoreColor }}>
              {Math.round(score)}<span style={{ color: "var(--text-muted)", fontWeight: 400 }}>/100</span>
            </span>
          </div>
          <div className="score-bar-bg">
            <div
              className="score-bar-fill"
              style={{ width: `${Math.min(100, Math.max(0, score))}%`, backgroundColor: scoreColor }}
            />
          </div>
        </div>

        <div className="lead-fields-grid">
          {fields.map(({ label, value }) => (
            <div className="field-item" key={label}>
              <label>{label}</label>
              <span>{value || "—"}</span>
            </div>
          ))}
          <div className="field-item full-width">
            <label>Requirements</label>
            <p className="requirements-text">{lead?.requirements || "Not yet stated"}</p>
          </div>
        </div>
      </div>

      {/* Appointment Banner */}
      {appointment && (
        <div className="appointment-card">
          <div className="appointment-header">
            <h4>📅 Demo Booked!</h4>
            <span className="appointment-status">Confirmed</span>
          </div>
          <p className="appointment-time">
            <strong>When: </strong>
            {new Date(appointment.slot_start).toLocaleString("en-IN", {
              weekday: "long",
              month:   "short",
              day:     "numeric",
              hour:    "numeric",
              minute:  "2-digit",
              hour12:  true,
            })}
          </p>
          <p className="appointment-note">Lead #{appointment.lead_id} · Calendar invite sent</p>
        </div>
      )}
    </div>
  );
}
