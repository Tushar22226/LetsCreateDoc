import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';
import MarkdownRenderer from './components/MarkdownRenderer';
import { ProjectHistory } from './features/documentation/components/ProjectHistory';

// --- Services ---
const API_BASE_URL = 'http://localhost:8000';

type OptionalOutputKey = 'include_code' | 'include_flowcharts' | 'include_graphs' | 'include_charts';

interface Section {
  title: string;
  description?: string;
}

interface ProjectData {
  title: string;
  page_count: number;
  description: string;
  custom_index: Section[];
  theme_color: string;
  include_code: boolean;
  include_flowcharts: boolean;
  include_graphs: boolean;
  include_charts: boolean;
  comment?: string;
}

const App: React.FC = () => {
  const [step, setStep] = useState<'idle' | 'planning' | 'streaming' | 'complete' | 'history'>('idle');
  const [data, setData] = useState<ProjectData>({
    title: '',
    page_count: 50,
    description: '',
    custom_index: [],
    theme_color: '#1F4E79',
    include_code: true,
    include_flowcharts: true,
    include_graphs: true,
    include_charts: true,
    comment: ''
  });

  const [planMd, setPlanMd] = useState('');
  const [streamingContent, setStreamingContent] = useState<{ section: string; thought: string; content: string }[]>([]);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [newItem, setNewItem] = useState('');
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);
  const optionalOutputs: { key: OptionalOutputKey; label: string }[] = [
    { key: 'include_code', label: 'Code snippets' },
    { key: 'include_flowcharts', label: 'Flowcharts' },
    { key: 'include_graphs', label: 'Graphs' },
    { key: 'include_charts', label: 'Charts' },
  ];

  const terminalRef = useRef<HTMLDivElement>(null);
  const planRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [streamingContent]);

  useEffect(() => {
    if (planRef.current) {
      planRef.current.scrollTop = planRef.current.scrollHeight;
    }
  }, [planMd]);

  const handleCsvImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0 && !line.toLowerCase().includes('section title'))
        .map(line => {
          // Robust CSV parsing for two columns: "Title","Description"
          const parts = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/); // Split only on commas not inside quotes
          const title = parts[0]?.replace(/^["'](.+)["']$/, '$1').trim();
          const description = parts[1]?.replace(/^["'](.+)["']$/, '$1').trim();
          return { title, description };
        })
        .filter(s => s.title);

      setData(prev => ({ ...prev, custom_index: [...prev.custom_index, ...lines] }));
      e.target.value = '';
    };
    reader.readAsText(file);
  };

  const handleGeneratePlan = async () => {
    setIsLoadingPlan(true);
    setStep('planning');
    setPlanMd(''); // Clear old plan

    const queryParams = new URLSearchParams({
      title: data.title,
      description: data.description,
      page_count: data.page_count.toString(),
      comment: data.comment || '',
      theme_color: data.theme_color,
      include_code: String(data.include_code),
      include_flowcharts: String(data.include_flowcharts),
      include_graphs: String(data.include_graphs),
      include_charts: String(data.include_charts)
    });

    const eventSource = new EventSource(`${API_BASE_URL}/documentation/stream-plan?${queryParams.toString()}`);

    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.status === 'planning_started') {
        setCurrentProjectId(payload.id);
      } else if (payload.status === 'planning_progress') {
        setIsLoadingPlan(false);
        setPlanMd(prev => prev + (payload.content || ''));
      } else if (payload.status === 'planning_completed') {
        setPlanMd(payload.plan);
        setCurrentProjectId(payload.id);
        eventSource.close();
        setIsLoadingPlan(false);
      } else if (payload.status === 'error') {
        alert('Plan generation error: ' + payload.message);
        eventSource.close();
        setIsLoadingPlan(false);
        setStep('idle');
      }
    };

    eventSource.onerror = () => {
      console.error('SSE Error during planning');
      eventSource.close();
      setIsLoadingPlan(false);
    };
  };

  const handleStartStreaming = () => {
    setStep('streaming');
    setStreamingContent([]);
    setGenerationProgress(0);

    // Extract sections from plan if custom_index is empty
    let sections = data.custom_index;
    if (sections.length === 0) {
      sections = planMd.split('\n').filter(l => l.startsWith('#') || l.startsWith('##')).map(l => ({ title: l.replace(/^#+\s*/, '').trim() }));
    }

    const queryParams = new URLSearchParams({
      title: data.title,
      description: data.description,
      page_count: data.page_count.toString(),
      custom_index: JSON.stringify(sections),
      comment: data.comment || '',
      theme_color: data.theme_color,
      include_code: String(data.include_code),
      include_flowcharts: String(data.include_flowcharts),
      include_graphs: String(data.include_graphs),
      include_charts: String(data.include_charts),
      project_id: currentProjectId?.toString() || ''
    });

    const eventSource = new EventSource(`${API_BASE_URL}/documentation/stream-generation?${queryParams.toString()}`);

    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.status === 'started') {
        setGenerationProgress(0);
      } else if (payload.status === 'generating') {
        setStreamingContent(prev => [...prev, { section: payload.section, thought: '', content: '' }]);
      } else if (payload.status === 'progress') {
        setStreamingContent(prev => {
          const last = prev[prev.length - 1];
          if (last) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...last,
              thought: last.thought + (payload.thought || ''), // REVERT: Accumulate deltas
              content: last.content + (payload.content || '')  // Append content delta
            };
            return updated;
          }
          return prev;
        });
      } else if (payload.status === 'completed_section') {
        setGenerationProgress(prev => prev + (100 / sections.length));
      } else if (payload.status === 'finished') {
        eventSource.close();
        setGenerationProgress(100);
        setIsFinalizing(true);
        fetchFinalDocx();
      } else if (payload.status === 'error') {
        alert('Streaming error: ' + payload.message);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      console.error('SSE Error connecting to generation pipeline');
      eventSource.close();
    };
  };

  const fetchFinalDocx = async () => {
    try {
      // Ensure we use the latest sections (including those from planMd)
      let sections = data.custom_index;
      if (sections.length === 0) {
        sections = planMd.split('\n').filter(l => l.startsWith('#') || l.startsWith('##')).map(l => ({ title: l.replace(/^#+\s*/, '').trim() }));
      }

      const res = await axios.post(`${API_BASE_URL}/documentation/generate-docx?project_id=${currentProjectId}`, {
        ...data,
        custom_index: sections
      }, { responseType: 'blob' });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      setDownloadUrl(url);
      setStep('complete');
    } catch {
      alert('Final DOCX compilation failed.');
    } finally {
      setIsFinalizing(false);
    }
  };

  return (
    <div className="app-root">
      <header>
        <div className="header-content">
          <div className="logo" style={{ cursor: 'pointer' }} onClick={() => setStep('idle')}>Knowledge<span>Forge</span></div>
          <div className="nav-links" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: '0.875rem' }}>v1.1.0 • Thinking Engine 3.1</span>
            <button
              onClick={() => setStep(step === 'history' ? 'idle' : 'history')}
              style={{ padding: '0.5rem 1rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', cursor: 'pointer', fontSize: '0.875rem' }}
            >
              {step === 'history' ? 'Craft New Document' : 'View History'}
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        {step === 'idle' && (
          <div className="fade-in">
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
              <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '0.5rem' }}>Design Your Documentation.</h1>
              <p style={{ color: '#64748b' }}>Configure your project and collaborate with the AI Architect to build a perfect blueprint.</p>
            </div>
            <div className="form-grid">
              <div className="card">
                <h2 style={{ marginBottom: '1.5rem' }}>Project Details</h2>
                <div className="form-group">
                  <label>Title</label>
                  <input value={data.title} onChange={e => setData({ ...data, title: e.target.value })} placeholder="Project Name" />
                </div>
                <div className="form-group">
                  <label>Target Pages</label>
                  <input type="number" value={data.page_count} onChange={e => setData({ ...data, page_count: parseInt(e.target.value) })} />
                </div>
                <div className="form-group">
                  <label>Document Accent</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem' }}>
                    <input
                      type="color"
                      value={data.theme_color}
                      onChange={e => setData({ ...data, theme_color: e.target.value.toUpperCase() })}
                      style={{ width: '3.25rem', height: '2.5rem', padding: 0, border: '1px solid #cbd5e1', borderRadius: '8px', background: '#ffffff' }}
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                      <strong style={{ color: '#1e293b', letterSpacing: '0.04em' }}>{data.theme_color.toUpperCase()}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        Used across the cover page, section headings, tables, and document accents.
                      </span>
                    </div>
                  </div>
                </div>
                <div className="form-group">
                  <label>Optional Outputs</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.75rem' }}>
                    {optionalOutputs.map((option) => (
                      <label
                        key={option.key}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.55rem',
                          padding: '0.7rem 0.8rem',
                          border: '1px solid #e2e8f0',
                          borderRadius: '10px',
                          background: '#f8fafc',
                          color: '#1e293b',
                          fontSize: '0.92rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={data[option.key]}
                          onChange={e => setData(prev => ({
                            ...prev,
                            [option.key]: e.target.checked,
                          }))}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </div>
                  <p style={{ marginTop: '0.55rem', color: '#64748b', fontSize: '0.78rem' }}>
                    Unchecked items will be excluded from the plan and final document generation.
                  </p>
                </div>
                <div className="form-group">
                  <label>Detailed Brief</label>
                  <textarea rows={8} value={data.description} onChange={e => setData({ ...data, description: e.target.value })} placeholder="Describe your system..." />
                </div>
                <button className="btn-primary btn-full" disabled={!data.title || !data.description} onClick={handleGeneratePlan}>
                  📝 Prepare Documentation Plan
                </button>
              </div>
              <div className="side-panel card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h2>Structure</h2>
                  <label className="btn-outline" style={{ fontSize: '0.7rem', cursor: 'pointer' }}>
                    CSV <input type="file" accept=".csv" onChange={handleCsvImport} style={{ display: 'none' }} />
                  </label>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                  <input placeholder="Section Title..." value={newItem} onChange={e => setNewItem(e.target.value)} />
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      placeholder="Optional Description..."
                      style={{ flex: 1, fontSize: '0.8rem' }}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && newItem) {
                          const desc = (e.target as HTMLInputElement).value;
                          setData({ ...data, custom_index: [...data.custom_index, { title: newItem, description: desc }] });
                          setNewItem('');
                          (e.target as HTMLInputElement).value = '';
                        }
                      }}
                    />
                    <button className="btn-outline" onClick={(e) => {
                      const input = (e.target as HTMLElement).previousElementSibling as HTMLInputElement;
                      if (newItem) {
                        setData({ ...data, custom_index: [...data.custom_index, { title: newItem, description: input.value }] });
                        setNewItem('');
                        input.value = '';
                      }
                    }}>+</button>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: 'auto' }}>
                  {data.custom_index.map((item, i) => (
                    <div key={i} className="index-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.2rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600 }}>{item.title}</span>
                        <button onClick={() => setData({ ...data, custom_index: data.custom_index.filter((_, idx) => idx !== i) })}>✕</button>
                      </div>
                      {item.description && <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{item.description}</span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'planning' && (
          <div className="plan-view fade-in">
            <div className="card">
              <h2>Documentation Blueprint</h2>
              <div className="markdown-viewport" ref={planRef} style={{ maxHeight: '60vh', overflowY: 'auto', background: '#ffffff', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
                {isLoadingPlan ? <div className="loading-spinner" style={{ margin: '4rem auto' }}></div> : <MarkdownRenderer content={planMd} />}
              </div>
              <div className="form-group">
                <label>Architect Feedback / Comments</label>
                <textarea rows={3} value={data.comment} onChange={e => setData({ ...data, comment: e.target.value })} placeholder="Suggest changes to the plan..." />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button className="btn-primary" style={{ flex: 1 }} onClick={handleStartStreaming}>🚀 Approve & Start Forging</button>
                <button className="btn-outline" style={{ flex: 1 }} onClick={handleGeneratePlan}>🔄 Regenerate Plan</button>
              </div>
            </div>
          </div>
        )}

        {step === 'streaming' && (
          <div className="stream-view fade-in">
            <div className="card" style={{ maxWidth: '900px', margin: '0 auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2>Forging: {data.title}</h2>
                <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>{Math.round(generationProgress)}%</span>
              </div>
              <div className="progress-bar" style={{ marginBottom: '2rem' }}>
                <div className="progress-fill" style={{ width: `${generationProgress}%` }}></div>
              </div>

              {isFinalizing && (
                <div className="card fade-in" style={{ background: '#eff6ff', border: '1px solid #3b82f6', marginBottom: '2rem', padding: '1rem', textAlign: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                    <div className="loading-spinner"></div>
                    <span style={{ fontWeight: 600, color: '#1e40af' }}>Finalizing Document Master...</span>
                  </div>
                </div>
              )}
              <div className="streaming-terminal" ref={terminalRef}>
                {streamingContent.map((s, idx) => (
                  <div key={idx} className="section-block">
                    <h3 style={{ color: '#1e293b', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>Section: {s.section}</h3>
                    {s.thought && <div className="thought-bubble"><strong>Thinking:</strong><p>{s.thought}</p></div>}
                    <div className="content-render">
                      <MarkdownRenderer content={s.content} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 'complete' && (
          <div className="complete-view card" style={{ maxWidth: 600, margin: '4rem auto', textAlign: 'center' }}>
            <div style={{ fontSize: '4rem' }}>🏆</div>
            <h2>Forge Successful</h2>
            <p style={{ color: '#64748b', marginBottom: '2rem' }}>The master artifact is ready for distribution.</p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button className="btn-primary" onClick={() => {
                const link = document.createElement('a');
                link.href = downloadUrl!;
                link.setAttribute('download', `${data.title || 'Master_Doc'}.docx`);
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
              }}>⬇️ Download DOCX</button>
              <button className="btn-outline" onClick={() => setStep('idle')}>New Project</button>
            </div>
          </div>
        )}

        {step === 'history' && (
          <div className="history-view fade-in">
            <ProjectHistory />
          </div>
        )}
      </main>

      <footer>© 2026 Developed with Elite Engineering Standards. Powered by DeepSeek V3.1 Thinking</footer>
    </div>
  );
};

export default App;
