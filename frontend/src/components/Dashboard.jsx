// components/Dashboard.jsx – CRM Analytics & Past Records with Interactive JSON Insights Viewer
import React, { useState, useEffect } from "react";
import { api } from "../services/api";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("leads");
  const [leads, setLeads] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [kbStatus, setKbStatus] = useState("");

  // Insights Viewer State
  const [expandedCallId, setExpandedCallId] = useState(null);
  const [modalCall, setModalCall] = useState(null); // { id, data, raw }
  const [copiedState, setCopiedState] = useState(false);
  const [jsonViewMode, setJsonViewMode] = useState("pretty"); // 'pretty' | 'structured'

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

  // Parse insights string safely
  const parseInsights = (rawInsights) => {
    if (!rawInsights || rawInsights === "{}" || rawInsights.trim() === "") {
      return null;
    }
    try {
      const parsed = JSON.parse(rawInsights);
      if (typeof parsed === "object" && parsed !== null) {
        return parsed;
      }
      return null;
    } catch {
      return null;
    }
  };

  const handleCopyJSON = (jsonData) => {
    const formatted = JSON.stringify(jsonData, null, 2);
    navigator.clipboard.writeText(formatted);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 2000);
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
          📞 Call History & JSON Insights ({calls.length})
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
                  <th>AI Insights (JSON)</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center">No calls logged yet.</td>
                  </tr>
                ) : (
                  calls.map((c) => {
                    const parsedInsights = parseInsights(c.insights);
                    const isExpanded = expandedCallId === c.id;

                    return (
                      <React.Fragment key={c.id}>
                        <tr>
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
                          <td className="insights-actions-cell">
                            {parsedInsights ? (
                              <div className="insights-button-group">
                                <button
                                  className="btn-json-badge"
                                  onClick={() => setModalCall({ id: c.id, data: parsedInsights })}
                                  title="View full JSON modal"
                                >
                                  <span className="json-icon">{`{ }`}</span>
                                  <span>Inspect JSON</span>
                                </button>
                                <button
                                  className="btn-toggle-inline"
                                  onClick={() => setExpandedCallId(isExpanded ? null : c.id)}
                                  title="Toggle inline JSON row"
                                >
                                  {isExpanded ? "▲ Hide" : "▼ Expand"}
                                </button>
                              </div>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                        </tr>

                        {/* Inline Expandable JSON Viewer Row */}
                        {isExpanded && parsedInsights && (
                          <tr className="expanded-json-row">
                            <td colSpan="6">
                              <div className="inline-json-card">
                                <div className="json-card-header">
                                  <div className="header-meta">
                                    <span className="json-badge-tag">JSON Schema Valid</span>
                                    <span className="call-ref">Call #{c.id} Post-Call Insights</span>
                                  </div>
                                  <div className="json-card-actions">
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => handleCopyJSON(parsedInsights)}
                                    >
                                      {copiedState ? "✓ Copied!" : "📋 Copy JSON"}
                                    </button>
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => setModalCall({ id: c.id, data: parsedInsights })}
                                    >
                                      ⤢ Fullscreen
                                    </button>
                                  </div>
                                </div>

                                <div className="json-code-container">
                                  <pre className="json-code-block">
                                    <code>{JSON.stringify(parsedInsights, null, 2)}</code>
                                  </pre>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL: Fullscreen Rich JSON Inspector */}
      {modalCall && (
        <div className="json-modal-backdrop" onClick={() => setModalCall(null)}>
          <div className="json-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="json-modal-header">
              <div className="modal-title-area">
                <span className="modal-logo">{`{ }`}</span>
                <div>
                  <h3>Call #{modalCall.id} – Structured AI Insights (JSON)</h3>
                  <span className="modal-subtitle">Extracted by Google Gemini Post-Call Analysis</span>
                </div>
              </div>
              <div className="modal-header-actions">
                <div className="view-mode-toggle">
                  <button
                    className={`mode-btn ${jsonViewMode === "pretty" ? "active" : ""}`}
                    onClick={() => setJsonViewMode("pretty")}
                  >
                    Raw JSON
                  </button>
                  <button
                    className={`mode-btn ${jsonViewMode === "structured" ? "active" : ""}`}
                    onClick={() => setJsonViewMode("structured")}
                  >
                    Visual Cards
                  </button>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleCopyJSON(modalCall.data)}
                >
                  {copiedState ? "✓ Copied!" : "📋 Copy JSON"}
                </button>
                <button className="btn-close-modal" onClick={() => setModalCall(null)}>
                  ✕
                </button>
              </div>
            </div>

            <div className="json-modal-body">
              {jsonViewMode === "pretty" ? (
                <div className="json-viewer-pane">
                  <div className="viewer-toolbar">
                    <span className="viewer-format">format: application/json</span>
                    <span className="viewer-lines">
                      {JSON.stringify(modalCall.data, null, 2).split("\n").length} lines
                    </span>
                  </div>
                  <pre className="modal-code-block">
                    <code>{JSON.stringify(modalCall.data, null, 2)}</code>
                  </pre>
                </div>
              ) : (
                <div className="structured-insights-grid">
                  {/* Interests */}
                  <div className="insight-card card-interests">
                    <div className="card-header">
                      <span className="card-icon">🎯</span>
                      <h4>Customer Interests ({modalCall.data?.interests?.length || 0})</h4>
                    </div>
                    <ul>
                      {modalCall.data?.interests?.length > 0 ? (
                        modalCall.data.interests.map((item, i) => <li key={i}>{item}</li>)
                      ) : (
                        <li className="text-muted">None detected</li>
                      )}
                    </ul>
                  </div>

                  {/* Objections */}
                  <div className="insight-card card-objections">
                    <div className="card-header">
                      <span className="card-icon">⚠️</span>
                      <h4>Objections / Hesitations ({modalCall.data?.objections?.length || 0})</h4>
                    </div>
                    <ul>
                      {modalCall.data?.objections?.length > 0 ? (
                        modalCall.data.objections.map((item, i) => <li key={i}>{item}</li>)
                      ) : (
                        <li className="text-muted">No objections raised</li>
                      )}
                    </ul>
                  </div>

                  {/* Unanswered Questions */}
                  <div className="insight-card card-unanswered">
                    <div className="card-header">
                      <span className="card-icon">❓</span>
                      <h4>Unanswered Questions ({modalCall.data?.unanswered_questions?.length || 0})</h4>
                    </div>
                    <ul>
                      {modalCall.data?.unanswered_questions?.length > 0 ? (
                        modalCall.data.unanswered_questions.map((item, i) => (
                          <li key={i} className="highlight-unanswered">{item}</li>
                        ))
                      ) : (
                        <li className="text-muted">All customer questions answered</li>
                      )}
                    </ul>
                  </div>

                  {/* Next Steps */}
                  <div className="insight-card card-next-steps">
                    <div className="card-header">
                      <span className="card-icon">➡️</span>
                      <h4>Recommended Next Steps ({modalCall.data?.next_steps?.length || 0})</h4>
                    </div>
                    <ul>
                      {modalCall.data?.next_steps?.length > 0 ? (
                        modalCall.data.next_steps.map((item, i) => <li key={i}>{item}</li>)
                      ) : (
                        <li className="text-muted">No explicit next steps logged</li>
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </div>

            <div className="json-modal-footer">
              <span className="modal-footer-hint">
                💡 Tip: Use this structured JSON to power automated CRM workflows or webhook payloads.
              </span>
              <button className="btn btn-primary btn-sm" onClick={() => setModalCall(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
