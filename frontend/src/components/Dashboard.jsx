// components/Dashboard.jsx – Fast CRM Analytics & Call Records
import React, { useState, useEffect } from "react";
import { api } from "../services/api";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("leads");
  const [leads, setLeads] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [kbStatus, setKbStatus] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [leadsRes, apptsRes, callsRes] = await Promise.all([
        api.getLeads(),
        api.getAppointments(),
        api.getCalls(),
      ]);
      setLeads(leadsRes);
      setAppointments(apptsRes);
      setCalls(callsRes);
    } catch (e) {
      console.error("Failed to load dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleReloadKB = async () => {
    setKbStatus("Reloading KB index...");
    try {
      const res = await api.reloadKB();
      setKbStatus(`✅ KB Reloaded: ${res.chunks} chunks indexed.`);
    } catch (e) {
      setKbStatus(`❌ Error reloading KB: ${e.message}`);
    }
    setTimeout(() => setKbStatus(""), 4000);
  };

  const formatInsightsText = (rawInsights) => {
    if (!rawInsights || rawInsights === "{}" || rawInsights.trim() === "") {
      return null;
    }
    try {
      const parsed = JSON.parse(rawInsights);
      if (typeof parsed === "object" && parsed !== null) {
        const lines = [];
        if (parsed.interests && (Array.isArray(parsed.interests) ? parsed.interests.length > 0 : parsed.interests)) {
          lines.push(`🎯 Interests: ${Array.isArray(parsed.interests) ? parsed.interests.join(", ") : parsed.interests}`);
        }
        if (parsed.objections && (Array.isArray(parsed.objections) ? parsed.objections.length > 0 : parsed.objections)) {
          lines.push(`⚠️ Objections: ${Array.isArray(parsed.objections) ? parsed.objections.join(", ") : parsed.objections}`);
        } else {
          lines.push("⚠️ Objections: None raised");
        }
        if (parsed.next_steps && (Array.isArray(parsed.next_steps) ? parsed.next_steps.length > 0 : parsed.next_steps)) {
          lines.push(`➡️ Next Steps: ${Array.isArray(parsed.next_steps) ? parsed.next_steps.join(", ") : parsed.next_steps}`);
        }
        if (parsed.unanswered_questions && (Array.isArray(parsed.unanswered_questions) ? parsed.unanswered_questions.length > 0 : parsed.unanswered_questions)) {
          lines.push(`❓ Unanswered: ${Array.isArray(parsed.unanswered_questions) ? parsed.unanswered_questions.join(", ") : parsed.unanswered_questions}`);
        }
        if (lines.length > 0) {
          return lines.join("\n");
        }
      }
      return rawInsights;
    } catch {
      return rawInsights;
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h2>📊 VoxLead AI Management Dashboard</h2>
          <p className="subtitle">Real-time pipeline analytics, booked slots, and call transcripts</p>
        </div>
        <div className="dashboard-actions">
          <button className="btn btn-secondary" onClick={handleReloadKB}>
            🔄 Reload Knowledge Base
          </button>
          <button className="btn btn-primary" onClick={fetchData} disabled={loading}>
            {loading ? "Refreshing..." : "↻ Refresh Data"}
          </button>
        </div>
      </div>

      {kbStatus && <div className="alert-banner">{kbStatus}</div>}

      <div className="tabs-header">
        <button
          className={`tab-btn ${activeTab === "leads" ? "active" : ""}`}
          onClick={() => setActiveTab("leads")}
        >
          🎯 Qualified Leads ({leads.length})
        </button>
        <button
          className={`tab-btn ${activeTab === "appointments" ? "active" : ""}`}
          onClick={() => setActiveTab("appointments")}
        >
          📅 Booked Demos ({appointments.length})
        </button>
        <button
          className={`tab-btn ${activeTab === "calls" ? "active" : ""}`}
          onClick={() => setActiveTab("calls")}
        >
          📞 Call History ({calls.length})
        </button>
      </div>

      <div className="tab-content">
        {/* LEADS TAB */}
        {activeTab === "leads" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lead ID</th>
                  <th>Contact</th>
                  <th>Company</th>
                  <th>Budget</th>
                  <th>Team</th>
                  <th>Timeline</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center">No leads recorded yet.</td>
                  </tr>
                ) : (
                  leads.map((l) => (
                    <tr key={l.id}>
                      <td>#{l.id}</td>
                      <td>
                        <strong>{l.name || "Unknown"}</strong>
                        <br />
                        <span className="text-muted">{l.phone || "No phone"}</span>
                      </td>
                      <td>{l.company || "—"}</td>
                      <td>{l.budget ? `₹${Number(l.budget).toLocaleString('en-IN')}/mo` : "—"}</td>
                      <td>{l.team_size ? `${l.team_size} users` : "—"}</td>
                      <td>{l.timeline_days ? `${l.timeline_days} days` : "—"}</td>
                      <td>
                        <strong>{Math.round(l.score)}</strong> / 100
                      </td>
                      <td>
                        <span className={`status-pill pill-${l.status}`}>
                          {l.status}
                        </span>
                      </td>
                      <td>{new Date(l.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* APPOINTMENTS TAB */}
        {activeTab === "appointments" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Appointment ID</th>
                  <th>Lead ID</th>
                  <th>Scheduled Slot</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {appointments.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="text-center">No demo appointments booked yet.</td>
                  </tr>
                ) : (
                  appointments.map((a) => (
                    <tr key={a.id}>
                      <td>#{a.id}</td>
                      <td>Lead #{a.lead_id}</td>
                      <td>
                        <strong>
                          {new Date(a.slot_start).toLocaleString('en-IN', {
                            weekday: 'long',
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true
                          })}
                        </strong>
                      </td>
                      <td>
                        <span className="status-pill pill-confirmed">
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* CALLS & INSIGHTS TAB */}
        {activeTab === "calls" && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Call</th>
                  <th>Started</th>
                  <th>Language</th>
                  <th>Sentiment</th>
                  <th>Executive Summary</th>
                  <th>Key Insights</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center">No calls logged yet.</td>
                  </tr>
                ) : (
                  calls.map((c) => {
                    const textFormatted = formatInsightsText(c.insights);

                    return (
                      <tr key={c.id}>
                        <td>
                          <strong>#{c.id}</strong>
                        </td>
                        <td>
                          <span className="timestamp-text">
                            {new Date(c.started_at).toLocaleString('en-IN', {
                              month: 'short',
                              day: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit',
                              hour12: true,
                            })}
                          </span>
                        </td>
                        <td>{c.language}</td>
                        <td>
                          <span className={`status-pill pill-${c.overall_sentiment || "neutral"}`}>
                            {c.overall_sentiment || "neutral"}
                          </span>
                        </td>
                        <td className="summary-cell">
                          {c.summary || <span className="text-muted">In progress / pending summary</span>}
                        </td>
                        <td className="insights-cell">
                          {textFormatted ? (
                            <div className="insights-text-block">
                              {textFormatted}
                            </div>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
