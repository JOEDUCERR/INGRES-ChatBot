import { useState, useRef, useEffect } from "react"
import axios from "axios"

const BACKEND = "http://127.0.0.1:8000"

const SUGGESTIONS = [
  "Which state has the highest ground water availability?",
  "Show rainfall data for Punjab in 2022-23",
  "Top 5 districts by ground water recharge",
  "What is the stage of ground water extraction in Rajasthan?",
]

export default function App() {
  const [question, setQuestion] = useState("")
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const send = async (q) => {
    const text = (q || question).trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { role: "user", text }])
    setQuestion("")
    setLoading(true)

    try {
      const res = await axios.post(`${BACKEND}/chat`, { question: text })
      setMessages(prev => [...prev, { role: "bot", text: res.data.answer }])
    } catch {
      setMessages(prev => [...prev, { role: "bot", text: "Error: Could not reach the backend. Is the server running?" }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerIcon}>💧</div>
        <div>
          <div style={styles.headerTitle}>INGRES Groundwater AI</div>
          <div style={styles.headerSub}>Powered by LLaMA 3.1 · SQLite database</div>
        </div>
        <div style={styles.statusBadge}>● Online</div>
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.welcome}>
            <div style={styles.welcomeTitle}>Ask me about groundwater data</div>
            <div style={styles.welcomeSub}>
              Query rainfall, recharge levels, extraction rates, and availability across states and districts.
            </div>
            <div style={styles.chips}>
              {SUGGESTIONS.map((s, i) => (
                <button key={i} style={styles.chip} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ ...styles.row, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            {msg.role === "bot" && <div style={styles.avatarBot}>AI</div>}
            <div style={msg.role === "user" ? styles.bubbleUser : styles.bubbleBot}>
              {msg.text}
            </div>
            {msg.role === "user" && <div style={styles.avatarUser}>You</div>}
          </div>
        ))}

        {loading && (
          <div style={{ ...styles.row, justifyContent: "flex-start" }}>
            <div style={styles.avatarBot}>AI</div>
            <div style={styles.bubbleBot}>
              <span style={styles.typing}>Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={styles.inputRow}>
        <textarea
          ref={textareaRef}
          style={styles.textarea}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about groundwater data..."
          rows={1}
        />
        <button style={styles.sendBtn} onClick={() => send()} disabled={loading || !question.trim()}>
          ➤
        </button>
      </div>
    </div>
  )
}

const styles = {
  app: { display: "flex", flexDirection: "column", height: "100vh", maxWidth: 780, margin: "0 auto", fontFamily: "system-ui, sans-serif", background: "#fff" },
  header: { display: "flex", alignItems: "center", gap: 12, padding: "14px 20px", borderBottom: "1px solid #e5e7eb", background: "#f9fafb" },
  headerIcon: { fontSize: 22 },
  headerTitle: { fontWeight: 600, fontSize: 15, color: "#111" },
  headerSub: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  statusBadge: { marginLeft: "auto", fontSize: 11, color: "#059669", fontWeight: 500 },
  messages: { flex: 1, overflowY: "auto", padding: "20px 16px", display: "flex", flexDirection: "column", gap: 12 },
  welcome: { textAlign: "center", padding: "30px 0 10px" },
  welcomeTitle: { fontSize: 18, fontWeight: 600, color: "#111", marginBottom: 8 },
  welcomeSub: { fontSize: 14, color: "#6b7280", maxWidth: 400, margin: "0 auto", lineHeight: 1.6 },
  chips: { display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 16 },
  chip: { fontSize: 12, padding: "7px 14px", border: "1px solid #d1fae5", borderRadius: 20, cursor: "pointer", color: "#065f46", background: "#ecfdf5", fontFamily: "inherit" },
  row: { display: "flex", gap: 8, alignItems: "flex-end" },
  avatarBot: { width: 28, height: 28, borderRadius: "50%", background: "#d1fae5", color: "#065f46", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 600, flexShrink: 0 },
  avatarUser: { width: 28, height: 28, borderRadius: "50%", background: "#ede9fe", color: "#4c1d95", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 600, flexShrink: 0 },
  bubbleBot: { maxWidth: "70%", padding: "10px 14px", borderRadius: 16, borderBottomLeftRadius: 4, background: "#f3f4f6", fontSize: 14, lineHeight: 1.6, color: "#111" },
  bubbleUser: { maxWidth: "70%", padding: "10px 14px", borderRadius: 16, borderBottomRightRadius: 4, background: "#d1fae5", fontSize: 14, lineHeight: 1.6, color: "#064e3b" },
  typing: { color: "#6b7280", fontStyle: "italic" },
  inputRow: { display: "flex", gap: 8, padding: "12px 16px", borderTop: "1px solid #e5e7eb", alignItems: "center" },
  textarea: { flex: 1, border: "1px solid #d1d5db", borderRadius: 8, padding: "10px 12px", fontSize: 14, fontFamily: "inherit", resize: "none", outline: "none" },
  sendBtn: { width: 40, height: 40, borderRadius: "50%", border: "none", background: "#059669", color: "#fff", fontSize: 16, cursor: "pointer" },
}