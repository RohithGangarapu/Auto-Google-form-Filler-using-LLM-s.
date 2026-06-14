import { Bot, ClipboardList, Play, RotateCw, Send, SquareMousePointer, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client.js";
import { QuestionList } from "../components/QuestionList.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";

export function FormAutomationPage() {
  const [url, setUrl] = useState("");
  const [context, setContext] = useState("");
  const [session, setSession] = useState(null);
  const [fillResults, setFillResults] = useState([]);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [modelError, setModelError] = useState("");

  const questionCount = session?.questions?.length || 0;
  const answerCount = useMemo(() => Object.keys(session?.answers || {}).length, [session]);

  // Load available OpenRouter models on mount
  useEffect(() => {
    async function loadModels() {
      try {
        const data = await api.getModels();
        if (data.error) {
          setModelError(data.error);
          setAvailableModels([]);
          setSelectedModels([]);
        } else {
          setAvailableModels(data.available || []);
          setSelectedModels(data.selected || []);
          setModelError("");
        }
      } catch (err) {
        console.error("Failed to load models:", err);
        setModelError("Failed to fetch available models.");
      }
    }
    loadModels();
  }, []);

  // Update selectedAnswers in sync with session questions and LLM answers
  useEffect(() => {
    const nextAnswers = {};
    if (session?.questions) {
      session.questions.forEach((q) => {
        nextAnswers[q.id] = session.answers?.[q.id]?.selected_option || "";
      });
    }
    setSelectedAnswers(nextAnswers);
  }, [session?.questions, session?.answers]);

  async function runAction(action, callback) {
    setBusyAction(action);
    setError("");
    try {
      await callback();
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setBusyAction("");
    }
  }

  function disabled(action) {
    return Boolean(busyAction) && busyAction !== action;
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Human-in-the-loop</p>
            <h1>LLM Form Automation Assistant</h1>
          </div>
          <StatusBadge status={session?.status} />
        </header>

        <section className="control-surface" aria-label="Session controls">
          <div className="url-row">
            <label>
              <span>Form URL</span>
              <input
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/form"
                type="url"
              />
            </label>
            <button
              className="primary-button"
              disabled={!url || disabled("create")}
              onClick={() =>
                runAction("create", async () => {
                  const nextSession = await api.createSession(url);
                  setSession(nextSession);
                  setFillResults([]);
                })
              }
              title="Open form in Selenium browser"
            >
              <Play size={18} />
              <span>{busyAction === "create" ? "Opening" : "Open"}</span>
            </button>
          </div>

          <label className="context-field">
            <span>User context for LLMs</span>
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              placeholder="Optional facts the models should use when answering form questions."
              rows={3}
            />
          </label>

          {/* OpenRouter voting models selection panel */}
          {modelError ? (
            <div className="model-selector-panel error" style={{ padding: "12px", border: "1px solid #ffd9d9", borderRadius: "8px", background: "#fff2f2", color: "#d32f2f" }}>
              <span style={{ display: "block", fontSize: "0.86rem", fontWeight: "700", marginBottom: "4px" }}>OpenRouter API Key Needed</span>
              <p style={{ margin: 0, fontSize: "0.8rem", lineHeight: "1.4" }}>{modelError}</p>
            </div>
          ) : availableModels.length > 0 ? (
            <div className="model-selector-panel" style={{ padding: "12px", border: "1px solid #d7dee5", borderRadius: "8px", background: "#fbfcfd" }}>
              <span style={{ display: "block", fontSize: "0.86rem", fontWeight: "700", color: "#4b5863", marginBottom: "8px" }}>
                Select Voting Models (OpenRouter Open-Source)
              </span>
              <div className="model-checkbox-grid" style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
                {availableModels.map((model) => {
                  const isChecked = selectedModels.includes(model);
                  return (
                    <label key={model} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.86rem", fontWeight: "600", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {
                          setSelectedModels(prev =>
                            isChecked
                              ? prev.filter(m => m !== model)
                              : [...prev, model]
                          );
                        }}
                      />
                      <span>{model}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="model-selector-panel error" style={{ padding: "12px", border: "1px solid #ffd9d9", borderRadius: "8px", background: "#ffd9d9", color: "#4b1414" }}>
              <span style={{ display: "block", fontSize: "0.86rem", fontWeight: "700", marginBottom: "4px" }}>OpenRouter Models</span>
              <p style={{ margin: 0, fontSize: "0.8rem" }}>No open-source models available. Ensure your API Key is set in backend/.env.</p>
            </div>
          )}

          <div className="action-grid">
            <button
              disabled={!session?.id || disabled("refresh")}
              onClick={() =>
                runAction("refresh", async () => {
                  setSession(await api.getSession(session.id));
                })
              }
              title="Refresh session state"
            >
              <RotateCw size={18} />
              <span>Refresh</span>
            </button>
            <button
              disabled={!session?.id || disabled("scrape")}
              onClick={() =>
                runAction("scrape", async () => {
                  setSession(await api.scrape(session.id));
                })
              }
              title="Scrape questions after manual login and CAPTCHA"
            >
              <ClipboardList size={18} />
              <span>Scrape</span>
            </button>
            <button
              disabled={!session?.id || !questionCount || disabled("answer") || selectedModels.length === 0}
              onClick={() =>
                runAction("answer", async () => {
                  setSession(await api.answer(session.id, context, selectedModels));
                })
              }
              title="Ask OpenRouter open-source models and vote"
            >
              <Bot size={18} />
              <span>Answer</span>
            </button>
            <button
              disabled={!session?.id || !Object.keys(selectedAnswers).length || disabled("fill")}
              onClick={() =>
                runAction("fill", async () => {
                  const response = await api.fill(session.id, selectedAnswers);
                  setSession(response.session);
                  setFillResults(response.fill_results || []);
                })
              }
              title="Fill answers without submitting"
            >
              <SquareMousePointer size={18} />
              <span>Fill</span>
            </button>
            <button
              disabled={!session?.id || disabled("close")}
              onClick={() =>
                runAction("close", async () => {
                  setSession(await api.close(session.id));
                })
              }
              title="Close Selenium browser"
            >
              <X size={18} />
              <span>Close</span>
            </button>
          </div>

          {error ? <div className="error-banner">{error}</div> : null}
        </section>

        <section className="metrics-row" aria-label="Session metrics">
          <div>
            <span>Session</span>
            <strong>{session?.id ? session.id.slice(0, 8) : "None"}</strong>
          </div>
          <div>
            <span>Questions</span>
            <strong>{questionCount}</strong>
          </div>
          <div>
            <span>Answers</span>
            <strong>{answerCount}</strong>
          </div>
          <div>
            <span>Fill Results</span>
            <strong>{fillResults.length}</strong>
          </div>
        </section>

        <section className="content-grid">
          <div>
            <div className="section-heading">
              <h2>Questions And Answers</h2>
              <Send size={18} />
            </div>
            <QuestionList
              questions={session?.questions || []}
              answers={session?.answers || {}}
              selectedAnswers={selectedAnswers}
              onSelectOption={(questionId, option) => {
                setSelectedAnswers(prev => ({ ...prev, [questionId]: option }));
              }}
            />
          </div>

          <aside className="audit-panel">
            <h2>Audit Log</h2>
            <div className="audit-list">
              {(session?.audit_log || []).slice().reverse().map((event, index) => (
                <div className="audit-item" key={`${event.timestamp}-${index}`}>
                  <strong>{event.event}</strong>
                  <span>{event.timestamp}</span>
                </div>
              ))}
              {!session?.audit_log?.length ? <p>No audit events yet.</p> : null}
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}
