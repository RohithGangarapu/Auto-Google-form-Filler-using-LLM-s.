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
              <div className="text-answer-container">
                {question.type === "paragraph" ? (
                  <textarea
                    value={currentSelection}
                    onChange={(e) => onSelectOption(question.id, e.target.value)}
                    placeholder="Provide long answer..."
                    rows={3}
                  />
                ) : (
                  <input
                    type="text"
                    value={currentSelection}
                    onChange={(e) => onSelectOption(question.id, e.target.value)}
                    placeholder="Provide short answer..."
                  />
                )}
              </div>
            ) : null}

            {/* Render model predictions and breakdown */}
            {answer ? (
              <div className="answer-panel">
                <div className="summary-row">
                  <div>
                    <p className="answer-label">LLM Majority Choice</p>
                    <strong>{answer.selected_option || "No answer voted"}</strong>
                  </div>
                  <div className="confidence-badge">
                    <span className="answer-label">Confidence</span>
                    <strong>{Math.round((answer.confidence || 0) * 100)}%</strong>
                  </div>
                </div>

                {answer.candidates && answer.candidates.length > 0 && (
                  <details className="model-votes-details">
                    <summary>
                      View individual model votes
                    </summary>
                    <div className="model-candidates-list">
                      {answer.candidates.map((cand, cIdx) => (
                        <div key={cIdx} className="model-candidate-card">
                          <div className="candidate-header">
                            <span className="candidate-name">{cand.model}</span>
                            <span className="candidate-conf">{Math.round(cand.confidence * 100)}% conf</span>
                          </div>
                          {cand.option && (
                            <p className="candidate-option">
                              Answer: <strong>{cand.option}</strong>
                            </p>
                          )}
                          {cand.reasoning && (
                            <p className="candidate-reasoning">
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
