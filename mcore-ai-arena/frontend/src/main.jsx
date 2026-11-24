import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

const AVAILABLE_MODELS = [
  { id: 'gemini-4-neon', label: 'Gemini 4 Neon', accent: '#38BDF8' },
  { id: 'gemini-4-hydrogen', label: 'Gemini 4 Hydrogen', accent: '#34D399' },
  { id: 'openai/gpt-oss-120b', label: 'Groq GPT-OSS 120B', accent: '#F97316' },
  { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4', accent: '#F59E0B' },
  { id: 'deepseek-chat', label: 'DeepSeek V3', accent: '#60A5FA' },
  { id: 'gpt-4o', label: 'GPT-4o', accent: '#A78BFA' }
];

function App() {
  const [prompt, setPrompt] = useState('');
  const [selected, setSelected] = useState(['gemini-4-neon', 'gemini-4-hydrogen', 'openai/gpt-oss-120b']);
  const [bypassCache, setBypassCache] = useState(false);
  const [results, setResults] = useState([]);
  const [winner, setWinner] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleModel = (id) => {
    setSelected((prev) => prev.includes(id) ? (prev.length > 1 ? prev.filter((m) => m !== id) : prev) : [...prev, id]);
  };

  const runComparison = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setWinner(null);
    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, models: selected, bypass_cache: bypassCache })
      });
      const data = await res.json();
      setResults(Array.isArray(data) ? data : [{ model: 'Gateway', provider: 'System', response: JSON.stringify(data), latency_ms: 0, status: 'error' }]);
    } catch (err) {
      setResults([{ model: 'System', provider: 'Gateway', response: String(err), latency_ms: 0, status: 'error' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'radial-gradient(circle at top, #0F172A, #070B14 65%)', padding: '2rem' }}>
      <header style={{ maxWidth: 1320, margin: '0 auto 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <span style={{ fontSize: 12, letterSpacing: 2, color: '#38BDF8', fontWeight: 700 }}>MCORE AI WORKSPACE</span>
          <h1 style={{ margin: '4px 0 0', fontSize: 28, fontWeight: 800 }}>Multi-Model Perspective Arena</h1>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {AVAILABLE_MODELS.map((m) => {
            const active = selected.includes(m.id);
            return (
              <button key={m.id} onClick={() => toggleModel(m.id)} style={{
                padding: '8px 14px', borderRadius: 999,
                border: `1px solid ${active ? m.accent : '#1E293B'}`,
                background: active ? 'rgba(56, 189, 248, 0.12)' : '#0F172A',
                color: active ? '#F8FAFC' : '#94A3B8', cursor: 'pointer', fontWeight: 600
              }}>{m.label}</button>
            );
          })}
        </div>
      </header>

      <main style={{ maxWidth: 1320, margin: '0 auto' }}>
        <form onSubmit={runComparison} style={{ display: 'flex', gap: 12, marginBottom: '2rem', flexWrap: 'wrap' }}>
          <input value={prompt} onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter one prompt to evaluate across all active models simultaneously..."
            style={{ flex: 1, minWidth: 280, padding: '14px 18px', borderRadius: 12, border: '1px solid #1E293B', background: '#0F172A', color: '#F8FAFC', fontSize: 15 }} />
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94A3B8', fontSize: 13 }}>
            <input type="checkbox" checked={bypassCache} onChange={(e) => setBypassCache(e.target.checked)} /> Fresh Run
          </label>
          <button type="submit" disabled={loading} style={{
            padding: '14px 24px', borderRadius: 12, border: 'none',
            background: 'linear-gradient(135deg, #38BDF8, #6366F1)', color: '#070B14', fontWeight: 800, cursor: 'pointer'
          }}>{loading ? 'Synthesizing...' : 'Compare Perspectives'}</button>
        </form>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {results.map((r) => {
            const isWinner = winner === r.model;
            return (
              <div key={r.model} style={{
                background: '#0F172A', border: `1px solid ${isWinner ? '#34D399' : '#1E293B'}`,
                borderRadius: 16, padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                    <strong style={{ color: '#38BDF8' }}>{r.model}</strong>
                    <span style={{ fontSize: 12, color: '#94A3B8' }}>{r.provider} · {r.cached ? 'CACHED · ' : ''}{r.latency_ms} ms</span>
                  </div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 14, lineHeight: 1.6, color: '#E2E8F0' }}>{r.response}</pre>
                </div>
                <button onClick={() => setWinner(r.model)} style={{
                  marginTop: 16, padding: '10px', borderRadius: 10, border: '1px solid #334155',
                  background: isWinner ? '#34D399' : '#1E293B', color: isWinner ? '#070B14' : '#F8FAFC', fontWeight: 700, cursor: 'pointer'
                }}>{isWinner ? 'Selected Perspective' : 'Choose This Perspective'}</button>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById('root')).render(<App />);
