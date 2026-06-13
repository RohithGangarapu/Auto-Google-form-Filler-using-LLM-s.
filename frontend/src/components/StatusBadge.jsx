const STATUS_LABELS = {
  created: "Created",
  browser_opened: "Browser Opened",
  waiting_for_user_auth: "Waiting For User",
  scraped: "Scraped",
  answered: "Answered",
  filled: "Filled",
  closed: "Closed",
  error: "Error",
};

export function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-${status || "created"}`}>
      {STATUS_LABELS[status] || status || "Created"}
    </span>
  );
}
