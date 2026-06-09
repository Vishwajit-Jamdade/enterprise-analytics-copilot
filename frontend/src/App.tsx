import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Copy,
  RefreshCcw,
  Send,
  Sparkles,
  SquarePen,
  CheckCircle2,
  AlertTriangle,
  PanelRightOpen,
  Database,
  ChartColumn,
} from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { checkHealth, sendChat, streamChat  } from "./api";
import type { ArtifactInfo, ChatMessage, DashboardState, HealthResponse } from "./types";

const APP_SESSION_KEY = "enterprise-data-assistant:session";
const MESSAGE_KEY_PREFIX = "enterprise-data-assistant:messages:";
const DASHBOARD_KEY_PREFIX = "enterprise-data-assistant:dashboard:";

const QUICK_PROMPTS = [
  "Show the monthly revenue trend.",
  "Summarize the gold.fact_sales table.",
  "What tables are available in the gold schema?",
  "Build a sales dashboard from the available data.",
];

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  kind: "text",
  content:
    "Ask for a chart, a schema summary, or a dashboard-style analysis. The agent can inspect gold-layer tables and render a revenue trend image when needed.",
};

function createSessionId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatTime(value: string) {
  if (!value || value === "now") {
    return "updated just now";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleTimeString();
}

function readJson<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function extractArtifactUrl(artifact: ArtifactInfo | null) {
  if (!artifact) return null;
  return artifact.url.startsWith("/") ? artifact.url : `/${artifact.url}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem(APP_SESSION_KEY);
    return saved || createSessionId();
  });
  const [chatTitle, setChatTitle] = useState(() => {
  return localStorage.getItem(`title-${sessionId}`) || "New Analysis";
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = readJson<ChatMessage[]>(`${MESSAGE_KEY_PREFIX}${sessionId}`, [WELCOME_MESSAGE]);
    return saved.length ? saved : [WELCOME_MESSAGE];
  });
  const [dashboard, setDashboard] = useState<DashboardState | null>(() => {
    return readJson<DashboardState | null>(`${DASHBOARD_KEY_PREFIX}${sessionId}`, null);
  });
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState<HealthResponse | null>(null);
  const [healthState, setHealthState] = useState<"checking" | "online" | "offline">("checking");
  const [lastError, setLastError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    localStorage.setItem(APP_SESSION_KEY, sessionId);
    const savedMessages = readJson<ChatMessage[]>(
      `${MESSAGE_KEY_PREFIX}${sessionId}`,
      [WELCOME_MESSAGE],
    );
    setChatTitle(
    localStorage.getItem(`title-${sessionId}`) || "New Analysis"
    );
    setMessages(savedMessages.length ? savedMessages : [WELCOME_MESSAGE]);
    setDashboard(readJson<DashboardState | null>(`${DASHBOARD_KEY_PREFIX}${sessionId}`, null));
  }, [sessionId]);

  useEffect(() => {
    localStorage.setItem(`${MESSAGE_KEY_PREFIX}${sessionId}`, JSON.stringify(messages));
  }, [messages, sessionId]);

  useEffect(() => {
    localStorage.setItem(`${DASHBOARD_KEY_PREFIX}${sessionId}`, JSON.stringify(dashboard));
  }, [dashboard, sessionId]);
  useEffect(() => {
  localStorage.setItem(
    `title-${sessionId}`,
    chatTitle
  );
  }, [chatTitle, sessionId]);

  useEffect(() => {
    const node = scrollRef.current; 
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, isSending]);

  useEffect(() => {
    checkHealth()
      .then((data) => {
        setStatus(data);
        setHealthState("online");
      })
      .catch((error: unknown) => {
        setLastError(error instanceof Error ? error.message : "Backend unavailable");
        setHealthState("offline");
      });
  }, []);

  const artifactUrl = useMemo(
    () => extractArtifactUrl(dashboard?.artifact ?? null),
    [dashboard],
  );

  const handleReset = () => {
    const nextSessionId = createSessionId();
    setSessionId(nextSessionId);
    setMessages([WELCOME_MESSAGE]);
    setDashboard(null);
    setInput("");
    setLastError(null);
    textareaRef.current?.focus();
  };

  const handleCopySession = async () => {
    await navigator.clipboard.writeText(sessionId);
  };

  const submitMessage = async (messageText: string) => {
    const trimmed = messageText.trim();
      if (!trimmed || isSending) return;

  if (
    messages.length <= 1 &&
    chatTitle === "New Analysis"
  ) {
    setChatTitle(
      trimmed.length > 50
        ? trimmed.substring(0, 50) + "..."
        : trimmed
    );
  };

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      kind: "text",
      content: trimmed,
    };
    const pendingMessage: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "assistant",
      kind: "status",
      content: "Analyzing data...",
    };

    setMessages((current) => [...current, userMessage, pendingMessage]);
    setInput("");
    setIsSending(true);
    setLastError(null);

    try {
      const response = await sendChat({
        message: trimmed,
        session_id: sessionId,
        user_id: "demo-user",
      });

      setSessionId(response.session_id);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingMessage.id
            ? {
                ...message,
                role: "assistant",
                kind: response.status === "error" ? "error" : "text",
                content: response.assistant_message,
              }
            : message,
        ),
      );
      setDashboard(response.dashboard);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Request failed";
      setLastError(message);
      setMessages((current) =>
        current.map((entry) =>
          entry.id === pendingMessage.id
            ? {
                ...entry,
                role: "assistant",
                kind: "error",
                content: `Request failed: ${message}`,
              }
            : entry,
        ),
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = () => {
    void submitMessage(input);
  };

  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  const online = healthState === "online";

  const suggestedQuestions = [
    "Top 10 products by revenue",
    "Monthly sales trend",
    "Revenue by region",
    "Top customers",
    "Sales breakdown by category",
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Bot size={18} strokeWidth={2.1} />
          </div>
          <div>
            <div className="eyebrow">Enterprise Data Assistant</div>
            <div className="subtitle">React chat UI for the Gemini-backed Python agent</div>
          </div>
        </div>

        <div className="topbar-actions">
          <span className={`status-pill ${online ? "status-online" : "status-offline"}`}>
            {online ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            {online ? "Connected" : "Offline"}
          </span>
          <button className="icon-button" onClick={handleCopySession} type="button" title="Copy session id">
            <Copy size={16} />
          </button>
          <button className="icon-button" onClick={handleReset} type="button" title="Start a new session">
            <RefreshCcw size={16} />
          </button>
        </div>
      </header>

      <main className="workspace">
        <section className="panel chat-panel">
          <div className="panel-header">
            <div>
              <h1>Chat</h1>
              <p>
                Session <code>{sessionId}</code>
              </p>
            </div>
            <button className="ghost-button" type="button" onClick={handleReset}>
              <SquarePen size={15} />
              New session
            </button>
          </div>

          <div className="prompt-strip">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="prompt-chip"
                onClick={() => handleQuickPrompt(prompt)}
              >
                <Sparkles size={14} />
                <span>{prompt}</span>
              </button>
            ))}
          </div>

          <div className="message-list" ref={scrollRef}>
  {messages.map((message, index) => (
    <article
      key={message.id}
      className={`message message-${message.role} message-${message.kind ?? "text"}`}
    >
      <div className="message-meta">
        <span>{message.role === "user" ? "You" : "Assistant"}</span>

        {message.kind === "status" && (
          <span className="message-badge">running</span>
        )}
      </div>

      <div className="message-body">

        {message.kind === "status" ? (
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}

        {artifactUrl &&
          message.role === "assistant" &&
          index === messages.length - 1 && (
            <div style={{ marginTop: "12px" }}>
              <img
                src={artifactUrl}
                alt="Generated Chart"
                style={{
                  width: "100%",
                  borderRadius: "12px",
                  border: "1px solid #333"
                }}
              />
            </div>
          )}
      </div>
    </article>
  ))}
</div>
<div className="suggestions">
  {suggestedQuestions.map((question) => (
    <button
      key={question}
      type="button"
      className="suggestion-chip"
      onClick={() => submitMessage(question)}
    >
      {question}
    </button>
  ))}
</div>
          <div className="composer">
            <label className="composer-label" htmlFor="prompt-input">
              Prompt the agent
            </label>
            <textarea
              id="prompt-input"
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Ask for a KPI, a chart, a SQL-backed summary, or a dashboard layout..."
            />
            <div className="composer-actions">
            <div className="status-copy">
                {lastError ? (
                  <span className="error-text">{lastError}</span>
                ) : (
                  <span>
                    {status?.auth_mode === "vertex"
                      ? "Vertex AI mode"
                      : status?.api_key_state === "configured"
                        ? "Gemini API key detected"
                        : "Gemini API key missing"}
                  </span>
                )}
              </div>
              <button
                type="button"
                className="primary-button"
                onClick={handleSubmit}
                disabled={isSending || !input.trim() || !online}
              >
                <Send size={16} />
                {isSending ? "Running" : "Send"}
              </button>
            </div>
          </div>
        </section>

        <aside className="panel dashboard-panel">
          <div className="panel-header">
            <div>
              <h2>Dashboard</h2>
              <p>Auto-generated from the latest agent run</p>
            </div>
            <PanelRightOpen size={18} />
          </div>

          <div className="dashboard-section">
            <div className="metric-grid">
              <div className="metric">
                <span className="metric-label">Turns</span>
                <strong>{dashboard?.turn_count ?? messages.length}</strong>
              </div>
              <div className="metric">
                <span className="metric-label">Tools</span>
                <strong>{dashboard?.tool_count ?? 0}</strong>
              </div>
              <div className="metric">
                <span className="metric-label">Tables</span>
                <strong>{dashboard?.tables.length ?? 0}</strong>
              </div>
              <div className="metric">
                <span className="metric-label">Artifacts</span>
                <strong>{dashboard?.artifact ? 1 : 0}</strong>
              </div>
            </div>
          </div>

          <div className="dashboard-section">
            <div className="section-title">
              <ChartColumn size={16} />
              <h3>Latest Insight</h3>
            </div>
            <p className="section-copy">
              {dashboard?.summary || "Run a prompt to populate the dashboard with insight, tool trace, and chart output."}
            </p>
          </div>

          <div className="dashboard-section">
            <div className="section-title">
              <Database size={16} />
              <h3>Referenced Tables</h3>
            </div>
            <div className="tag-cloud">
              {dashboard?.tables.length ? (
                dashboard.tables.map((table) => <span key={table} className="tag">{table}</span>)
              ) : (
                <span className="muted-text">No tables referenced yet.</span>
              )}
            </div>
          </div>

          <div className="dashboard-section">
            <div className="section-title">
              <ChartColumn size={16} />
              <h3>Chart Preview</h3>
            </div>
            {artifactUrl ? (
              <a className="chart-frame" href={artifactUrl} target="_blank" rel="noreferrer">
                <img src={artifactUrl} alt={dashboard?.artifact?.name ?? "Chart artifact"} />
              </a>
            ) : (
              <div className="empty-state">
                The agent will surface a chart here when it returns an image artifact.
              </div>
            )}
          </div>

          <div className="dashboard-section">
            <div className="section-title">
              <Bot size={16} />
              <h3>Tool Trace</h3>
            </div>
            {dashboard?.tool_names.length ? (
              <div className="tool-list">
                {dashboard.tool_names.map((tool) => (
                  <div key={tool} className="tool-row">
                    <span>{tool}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No tool calls yet.</div>
            )}
            <div className="updated-line">
              Session updated {formatTime(dashboard?.last_updated ?? "")}
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
