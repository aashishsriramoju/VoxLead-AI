// components/Dashboard.jsx – Modern CRM Analytics Dashboard
import React, { useState, useEffect } from "react";
import { api } from "../services/api";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("leads");
  const [leads, setLeads]           = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [calls, setCalls]           = useState([]);
  const [loading, setLoading]       = useState(false);
  const [kbStatus, setKbStatus]     = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [l, a, c] = await Promise.all([api.getLeads(), api.getAppointments(), api.getCalls()]);
      setLeads(l);
      setAppointments(a);
      setCalls(c);
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleReloadKB = async () => {
    setKbStatus("Reloading knowledge base...");
    try {
      const res = await api.reloadKB();
      setKbStatus(`✅ KB reloaded — ${res.chunks} chunks indexed`);
    } catch (e) {
      setKbStatus(`❌ Error: ${e.message}`);
    }
    setTimeout(() => setKbStatus(""), 4000);
  };

  const formatInsightsText = (rawInsights) => {
    if (!rawInsights || rawInsights === "{}" || rawInsights.trim() === "") return null;
    // If it's already a readable text string (not JSON), display it directly
    if (!rawInsights.trim().startsWith("{")) return rawInsights;
    try {
      const parsed = JSON.parse(rawInsights);
      if (typeof parsed === "object" && parsed !== null) {
        const lines = [];
        const interests = parsed.interests;
        if (interests?.length) lines.push(`🎯 ${Array.isArray(interests) ? interests.join(", ") : interests}`);

        const objections = parsed.objections;
        if (objections?.length) lines.push(`⚠️ ${Array.isArray(objections) ? objections.join(", ") : objections}`);
        else lines.push("⚠️ No objections raised");

        const steps = parsed.next_steps;
        if (steps?.length) lines.push(`➡️ ${Array.isArray(steps) ? steps.join(", ") : steps}`);

        const unanswered = parsed.unanswered_questions;
        if (unanswered?.length) lines.push(`❓ ${Array.isArray(unanswered) ? unanswered.join(", ") : unanswered}`);

        return lines.length ? lines.join("\n") : null;
      }
    } catch { /* fall through */ }
    return rawInsights;
  };

  const scoreColor = (s) =>
    s >= 70 ? "var(--green)" : s >= 40 ? "var(--amber)" : "var(--cyan)";

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h2>📊 VoxLead AI Dashboard</h2>
          <p className="subtitle">Real-time pipeline analytics, booked demos, and call records</p>
        </div>
        <div className="dashboard-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleReloadKB}>
            🔄 Reload KB
          </button>
          <button className="btn btn-primary btn-sm" onClick={fetchData} disabled={loading}>
            {loading ? "Refreshing…" : "↻ Refresh"}
          </button>
        </div>
      </div>

      {kbStatus && <div className="alert-banner">{kbStatus}</div>}

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
        {[
          { label: "Total Leads",   value: leads.length,       icon: "🎯", color: "var(--accent)" },
          { label: "Demos Booked",  value: appointments.length, icon: "📅", color: "var(--green)"  },
          { label: "Calls Logged",  value: calls.length,        icon: "📞", color: "var(--cyan)"   },
        ].map(({ label, value, icon, color }) => (
          <div
            key={label}
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "1.1rem 1.4rem",
              backdropFilter: "blur(12px)",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <span style={{ fontSize: "1.75rem" }}>{icon}</span>
            <div>
              <div style={{ fontSize: "1.75rem", fontWeight: 700, color, lineHeight: 1 }}>
                {value}
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                {label}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs-header">
        {[
          { id: "leads",        label: `🎯 Leads (${leads.length})`       },
          { id: "appointments", label: `📅 Demos (${appointments.length})` },
          { id: "calls",        label: `📞 Calls (${calls.length})`        },
        ].map(({ id, label }) => (
          <button
            key={id}
            className={`tab-btn ${activeTab === id ? "active" : ""}`}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {/* ── Leads Tab ── */}
        {activeTab === "leads" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th><th>Contact</th><th>Company</th>
                  <th>Budget</th><th>Team</th><th>Timeline</th>
                  <th>Score</th><th>Status</th><th>Created</th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 ? (
                  <tr><td colSpan="9" className="text-center" style={{ padding: "2rem" }}>No leads yet.</td></tr>
                ) : leads.map((l) => (
                  <tr key={l.id}>
                    <td style={{ color: "var(--text-muted)" }}>#{l.id}</td>
                    <td>
                      <strong>{l.name || "Unknown"}</strong>
                      <br />
                      <span className="text-muted" style={{ fontSize: "0.78rem" }}>{l.phone || "—"}</span>
                    </td>
                    <td>{l.company || "—"}</td>
                    <td>{l.budget ? `₹${Number(l.budget).toLocaleString("en-IN")}/mo` : "—"}</td>
                    <td>{l.team_size ? `${l.team_size} users` : "—"}</td>
                    <td>{l.timeline_days ? `${l.timeline_days}d` : "—"}</td>
                    <td>
                      <span style={{ fontWeight: 700, color: scoreColor(l.score) }}>
                        {Math.round(l.score)}
                      </span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>/100</span>
                    </td>
                    <td><span className={`status-pill pill-${l.status}`}>{l.status}</span></td>
                    <td className="timestamp-text">{new Date(l.created_at).toLocaleDateString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Appointments Tab ── */}
        {activeTab === "appointments" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th><th>Lead</th><th>Demo Time</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {appointments.length === 0 ? (
                  <tr><td colSpan="4" className="text-center" style={{ padding: "2rem" }}>No demos booked yet.</td></tr>
                ) : appointments.map((a) => (
                  <tr key={a.id}>
                    <td style={{ color: "var(--text-muted)" }}>#{a.id}</td>
                    <td>Lead #{a.lead_id}</td>
                    <td>
                      <span className="timestamp-text">
                        {new Date(a.slot_start).toLocaleString("en-IN", {
                          weekday: "short", month: "short", day: "numeric",
                          hour: "numeric", minute: "2-digit", hour12: true,
                        })}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill pill-${a.status}`}>{a.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Calls Tab ── */}
        {activeTab === "calls" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Call</th><th>Started</th><th>Lang</th>
                  <th>Sentiment</th><th>Executive Summary</th><th>Key Insights</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr><td colSpan="6" className="text-center" style={{ padding: "2rem" }}>No calls logged yet.</td></tr>
                ) : calls.map((c) => {
                  const insightsText = formatInsightsText(c.insights);
                  return (
                    <tr key={c.id}>
                      <td><strong style={{ color: "var(--accent)" }}>#{c.id}</strong></td>
                      <td>
                        <span className="timestamp-text">
                          {new Date(c.started_at).toLocaleString("en-IN", {
                            month: "short", day: "numeric",
                            hour: "numeric", minute: "2-digit", hour12: true,
                          })}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{c.language}</td>
                      <td>
                        <span className={`status-pill pill-${c.overall_sentiment || "neutral"}`}>
                          {c.overall_sentiment || "neutral"}
                        </span>
                      </td>
                      <td className="summary-cell">
                        {c.summary || <span className="text-muted">Pending…</span>}
                      </td>
                      <td className="insights-cell">
                        {insightsText ? (
                          <div className="insights-text-block">{insightsText}</div>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
