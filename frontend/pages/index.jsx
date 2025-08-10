// frontend/pages/index.jsx
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:5000'

function AssistantBubble({ content, animate, onDone }) {
  const [shown, setShown] = useState(animate ? '' : content)

  useEffect(() => {
    if (!animate) return
    const total = content.length
    const step = total > 1500 ? 6 : total > 800 ? 4 : total > 300 ? 2 : 1
    const id = setInterval(() => {
      setShown(prev => {
        const nextLen = Math.min(total, prev.length + step)
        if (nextLen >= total) { clearInterval(id); onDone && onDone() }
        return content.slice(0, nextLen)
      })
    }, 16)
    return () => clearInterval(id)
  }, [content, animate, onDone])

  const isTyping = animate && shown.length < content.length

  return (
    <div className="bubble">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {isTyping ? shown : content}
      </ReactMarkdown>
      {isTyping ? <span className="caret" /> : null}
      <div style={{ marginTop: 8, display: 'flex', gap: 8, opacity: .9 }}>
        <button
          type="button"
          className="secondary"
          disabled={isTyping}
          onClick={() => navigator.clipboard?.writeText(content)}
        >
          Copy
        </button>
      </div>
    </div>
  )
}

export default function Home() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [modelBadge, setModelBadge] = useState('')
  const [toast, setToast] = useState({ text: '', show: false })
  const [isComposing, setIsComposing] = useState(false) // IME-safe Enter-to-send
  const boxRef = useRef(null)
  const taRef = useRef(null)

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    fetch(`${API_BASE}/api/health`).then(r => r.json()).then(d => {
      setModelBadge(d?.model ? `Model: ${d.model}` : '')
    }).catch(() => {})
  }, [])

  function showToast(t) {
    setToast({ text: t, show: true })
    setTimeout(() => setToast(s => ({ ...s, show: false })), 1500)
  }

  function clearChat(){
    setMessages([]); setInput('');
    if (taRef.current) { taRef.current.style.height = '120px'; taRef.current.focus() }
  }

  async function sendPrompt(e){
    e?.preventDefault?.()
    const text = input.trim()
    if (!text) return

    const nextMsgs = [...messages, { role: 'user', content: text, animate: true }]
    setMessages(nextMsgs)
    setInput('')
    setLoading(true)

    try{
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMsgs })
      })
      const data = await res.json()
      const reply = data?.reply ?? 'No reply.'
      setMessages(prev => [...prev, { role: 'assistant', content: reply, animate: true }])
    }catch(err){
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${String(err)}` }])
    }finally{
      setLoading(false)
      taRef.current?.focus()
    }
  }

  // ENTER sends • Shift+Enter makes newline • IME-safe using composition flags
  function onKeyDown(e){
    if (
      e.key === 'Enter' &&
      !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey
    ){
      if (isComposing) return
      e.preventDefault()
      if (!loading) sendPrompt()
    }
  }

  function onTextareaInput(e){
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.max(120, el.scrollHeight) + 'px'
  }

  // Offer CSV if last assistant message looks like a Markdown table
  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
  const canDownloadCSV = lastAssistant && lastAssistant.content.includes('|')
  function downloadCSVFromMarkdown(md){
    const lines = md.split('\n').filter(l => l.trim().startsWith('|'))
    if (!lines.length) return
    const rows = lines
      .map(l => l.trim().replace(/^\|/, '').replace(/\|$/, ''))
      .filter(l => !/^-{3,}/.test(l.replace(/\s|\|/g, '')))
      .map(l => l.split('|').map(c => `"${c.trim().replace(/"/g, '""')}"`).join(','))
    const csv = rows.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `export_${Date.now()}.csv`
    document.body.appendChild(a); a.click(); a.remove()
    showToast('CSV downloaded')
  }

  function markDone(idx){
    setMessages(prev => {
      const arr = [...prev]
      if (arr[idx] && arr[idx].animate) arr[idx] = { ...arr[idx], animate: false }
      return arr
    })
  }

  return (
    <div>
      <header className="nav animate-in">
        <div className="brand">Nova (Free)</div>
        <nav>
          <a href="#">Home</a>
          <a href="#">Chat</a>
        </nav>
        {modelBadge ? <span className="badge">{modelBadge}</span> : null}
      </header>

      <main className="container">
        {/* Two-column layout: chat (left) + instructions (right) */}
        <div className="layout">
          {/* Left: chat */}
          <div className="maincol">
            <div className="card animate-in">
              <section className="chat">
                <h2 style={{margin:'6px 2px'}}>Nova (Free) — General Chat, Research & SEO Writing</h2>
                <div className="h-intent">Type your message and press <b>Enter</b> to send. Use <b>Shift+Enter</b> for a new line.</div>

                <div className="messages" ref={boxRef}>
                  {messages.map((m, i) => (
                    <div key={i} className={`msg ${m.role === 'user' ? 'user' : 'ai'} animate-in`}>
                      {m.role === 'assistant'
                        ? <AssistantBubble content={m.content} animate={!!m.animate} onDone={() => markDone(i)} />
                        : <div className="bubble">{m.content}</div>}
                    </div>
                  ))}
                  {loading && (
                    <div className="msg ai animate-in">
                      <div className="bubble" style={{display:'flex',alignItems:'center',gap:8}}>
                        <span className="spinner" /> thinking…
                      </div>
                    </div>
                  )}
                </div>

                {/* Composer */}
                <form onSubmit={sendPrompt} className="composer slide-up">
                  <textarea
                    ref={taRef}
                    placeholder='Ask anything (Enter to send • Shift+Enter for newline)'
                    value={input}
                    onChange={onTextareaInput}
                    onKeyDown={onKeyDown}
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    required
                    style={{height:120}}
                  />
                  <div className="actions">
                    <button type="submit" disabled={loading}>{loading ? 'Sending…' : 'Send'}</button>
                    <button type="button" className="secondary" onClick={clearChat}>Clear</button>
                    {canDownloadCSV && (
                      <button type="button" className="secondary" onClick={() => downloadCSVFromMarkdown(lastAssistant.content)}>
                        Download CSV
                      </button>
                    )}
                  </div>
                </form>
              </section>
            </div>
          </div>

          {/* Right: instructions */}
          <aside className="sidecol">
            <div className="panel pop-in">
              <h3 style={{margin:'8px 0 6px'}}>Tips & Limits</h3>
              <ul style={{margin:'0 0 10px 18px', lineHeight:1.5}}>
                <li>General conversation is supported.</li>
                <li>Ask for keyword clusters, outlines, briefs, meta titles/descriptions, articles, or research summaries — no preset needed.</li>
                <li><b>No coding or debugging</b> in Nova Free. For code, upgrade to premium models (Main/Power or GWEN).</li>
                <li>Use clear topics for best SEO outputs (e.g., “keyword clusters for healthy meal prep”).</li>
                <li>Tables detected in answers can be downloaded as CSV.</li>
              </ul>
              <h4>Example prompts</h4>
              <ul style={{margin:'4px 0 0 18px'}}>
                <li>“Keyword clusters for electric scooters”</li>
                <li>“Outline: benefits of standing desks”</li>
                <li>“Write an article about remote team rituals”</li>
                <li>“Research summary: zero-trust security”</li>
                <li>“Meta titles & descriptions for gluten-free bread”</li>
              </ul>
            </div>
          </aside>
        </div>

        <footer className="foot fade-in">
          © {new Date().getFullYear()} Nova (Free)
        </footer>
      </main>

      {/* Toast */}
      <div className={`toast ${toast.show ? 'show' : ''}`}>{toast.text}</div>
    </div>
  )
}
