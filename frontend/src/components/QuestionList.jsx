import { CheckCircle2, CircleAlert } from "lucide-react";

export function QuestionList({ questions = [], answers = {}, selectedAnswers = {}, onSelectOption }) {
  if (!questions.length) {
    return (
      <div className="empty-state">
        <CircleAlert size={18} />
        <span>No questions scraped yet.</span>
      </div>
    );
  }

  return (
    <div className="question-list">
      {questions.map((question) => {
        const answer = answers[question.id];
        const currentSelection = selectedAnswers[question.id] || "";
        
        // Parse selected choices for checkboxes
        const selectedChoices = question.type === "checkbox"
          ? currentSelection.split(",").map(x => x.trim()).filter(Boolean)
          : [];

        return (
          <article className="question-card" key={question.id}>
            <div className="question-main">
              <div>
                <p className="question-type">{question.type}</p>
                <h3>{question.prompt}</h3>
              </div>
              {currentSelection ? <CheckCircle2 size={20} className="answer-icon" /> : null}
            </div>

            {/* Render interactive options (Radio & Checkbox) */}
            {question.options?.length ? (
              <div className="option-row">
                {question.options.map((option, idx) => {
                  let isSelected = false;
                  let toggleHandler = () => {};

                  if (question.type === "checkbox") {
                    isSelected = selectedChoices.includes(option);
                    toggleHandler = () => {
                      const next = isSelected
                        ? selectedChoices.filter(x => x !== option)
                        : [...selectedChoices, option];
                      onSelectOption(question.id, next.join(", "));
                    };
                  } else {
                    isSelected = currentSelection === option;
                    toggleHandler = () => onSelectOption(question.id, option);
                  }

                  return (
                    <button
                      key={idx}
                      className={`option-chip ${isSelected ? "selected" : ""}`}
                      onClick={toggleHandler}
                      type="button"
                    >
                      {option}
                    </button>
                  );
                })}
              </div>
            ) : null}

            {/* Render text input fields (Text & Paragraph) */}
            {question.type === "text" || question.type === "paragraph" ? (
              <div className="text-answer-container" style={{ marginTop: "12px" }}>
                {question.type === "paragraph" ? (
                  <textarea
                    value={currentSelection}
                    onChange={(e) => onSelectOption(question.id, e.target.value)}
                    placeholder="Provide long answer..."
                    rows={3}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid #c7d0d9",
                      background: "#fbfcfd",
                      resize: "vertical"
                    }}
                  />
                ) : (
                  <input
                    type="text"
                    value={currentSelection}
                    onChange={(e) => onSelectOption(question.id, e.target.value)}
                    placeholder="Provide short answer..."
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid #c7d0d9",
                      background: "#fbfcfd"
                    }}
                  />
                )}
              </div>
            ) : null}

            {/* Render model predictions and breakdown */}
            {answer ? (
              <div className="answer-panel">
                <div className="summary-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                  <div>
                    <p className="answer-label" style={{ margin: 0 }}>LLM Majority Choice</p>
                    <strong style={{ display: "block", marginTop: "4px" }}>{answer.selected_option || "No answer voted"}</strong>
                  </div>
                  <div className="confidence-badge" style={{ textAlign: "right" }}>
                    <span className="answer-label" style={{ margin: 0 }}>Confidence</span>
                    <strong style={{ display: "block", marginTop: "4px" }}>{Math.round((answer.confidence || 0) * 100)}%</strong>
                  </div>
                </div>

                {answer.candidates && answer.candidates.length > 0 && (
                  <details className="model-votes-details" style={{ marginTop: "12px", borderTop: "1px dashed #e3e8ed", paddingTop: "8px" }}>
                    <summary style={{ cursor: "pointer", fontSize: "0.82rem", color: "#1d6f8f", fontWeight: "600", outline: "none" }}>
                      View individual model votes
                    </summary>
                    <div className="model-candidates-list" style={{ marginTop: "8px", display: "grid", gap: "8px" }}>
                      {answer.candidates.map((cand, cIdx) => (
                        <div key={cIdx} className="model-candidate-card" style={{ padding: "8px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "6px", fontSize: "0.86rem" }}>
                          <div className="candidate-header" style={{ display: "flex", justifyContent: "space-between", fontWeight: "600", color: "#334155" }}>
                            <span className="candidate-name">{cand.model}</span>
                            <span className="candidate-conf" style={{ color: "#475569", fontSize: "0.8rem" }}>{Math.round(cand.confidence * 100)}% conf</span>
                          </div>
                          {cand.option && (
                            <p className="candidate-option" style={{ margin: "4px 0 0", color: "#0f172a" }}>
                              Answer: <strong>{cand.option}</strong>
                            </p>
                          )}
                          {cand.reasoning && (
                            <p className="candidate-reasoning" style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.8rem", fontStyle: "italic" }}>
                              {cand.reasoning}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
