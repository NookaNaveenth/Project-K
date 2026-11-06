import React, { StrictMode, Component } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./components/calendar/Calendar.css";
import App from "./App.jsx";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Critical Application Render Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    try {
      sessionStorage.clear();
      localStorage.clear();
    } catch {
      // ignore storage access errors
    }
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "#f8fafc",
            color: "#1e293b",
            fontFamily: "Inter, system-ui, -apple-system, sans-serif",
            padding: "24px",
          }}
        >
          <div
            style={{
              maxWidth: "680px",
              width: "100%",
              background: "#ffffff",
              borderRadius: "12px",
              boxShadow:
                "0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)",
              border: "1px solid #e2e8f0",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                background: "#003a70",
                color: "#ffffff",
                padding: "20px 24px",
                display: "flex",
                alignItems: "center",
                gap: "14px",
              }}
            >
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "50%",
                  background: "rgba(239, 68, 68, 0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "2px solid #ef4444",
                  flexShrink: 0,
                }}
              >
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: "18px",
                    fontWeight: 700,
                    letterSpacing: "-0.01em",
                  }}
                >
                  FaceAttend — Render Notice
                </h2>
                <div style={{ fontSize: "13px", opacity: 0.85, marginTop: "2px" }}>
                  An unexpected error occurred in the user interface.
                </div>
              </div>
            </div>

            <div style={{ padding: "24px" }}>
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  padding: "14px 16px",
                  marginBottom: "18px",
                  fontSize: "13.5px",
                  color: "#991b1b",
                  fontWeight: 600,
                  wordBreak: "break-word",
                  fontFamily: "monospace",
                }}
              >
                {this.state.error?.toString()}
              </div>

              {this.state.errorInfo?.componentStack && (
                <details style={{ marginBottom: "20px", cursor: "pointer" }}>
                  <summary
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#475569",
                      padding: "4px 0",
                    }}
                  >
                    View Component Stack
                  </summary>
                  <pre
                    style={{
                      marginTop: "8px",
                      padding: "12px 14px",
                      background: "#0f172a",
                      color: "#f8fafc",
                      borderRadius: "6px",
                      fontSize: "11.5px",
                      lineHeight: 1.5,
                      overflowX: "auto",
                      whiteSpace: "pre-wrap",
                      maxHeight: "220px",
                    }}
                  >
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}

              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  type="button"
                  onClick={this.handleReload}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    background: "#00aae7",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "6px",
                    fontWeight: 700,
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Reload Page
                </button>
                <button
                  type="button"
                  onClick={this.handleReset}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    background: "#f1f5f9",
                    color: "#475569",
                    border: "1px solid #cbd5e1",
                    borderRadius: "6px",
                    fontWeight: 600,
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Clear Session & Reload
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
);
