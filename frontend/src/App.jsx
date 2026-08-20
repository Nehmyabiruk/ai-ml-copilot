import {  useState } from 'react'
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
const apiFetch = (path, options = {}) => fetch(path, { ...options, credentials: 'include' })

function repositoryName(url) {
  return (url.trim().replace(/\/$/, '').split('/').pop() || 'repository').replace(/\.git$/, '')
}

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [project, setProject] = useState(null)
  const [documents, setDocuments] = useState([])
  const [ingesting, setIngesting] = useState(false)
  const [status, setStatus] = useState('Enter a Git repository URL to start.')
  const [trace, setTrace] = useState('')
  const [targetFile, setTargetFile] = useState('')
  const [repairing, setRepairing] = useState(false)
  const [auditing, setAuditing] = useState(false)
  const [issues, setIssues] = useState([])
  const [repairPlan, setRepairPlan] = useState(null)
  const [repairApplied, setRepairApplied] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [pullRequest, setPullRequest] = useState(null)
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState([])
  const [sending, setSending] = useState(false)

  const loadDocuments = async (projectId) => {
    const response = await apiFetch(`${API_BASE}/projects/${projectId}/documents`)
    if (!response.ok) throw new Error('Could not load the ingested files.')
    const data = await response.json()
    setDocuments(data.documents || [])
  }

  const ingest = async () => {
    if (!repoUrl.trim()) return setStatus('Please provide a repository URL.')
    setIngesting(true)
    setStatus('Creating repository workspace…')
    setProject(null)
    setDocuments([])
    setRepairPlan(null)
    setRepairApplied(false)
    setMessages([])
    setTargetFile('')
    setIssues([])
    try {
      const create = await apiFetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: repositoryName(repoUrl), repository_url: repoUrl.trim() }),
      })
      const created = await create.json()
      if (!create.ok) throw new Error(created.detail || 'Could not create repository workspace.')
      setStatus('Cloning and indexing repository files…')
      const index = await apiFetch(`${API_BASE}/projects/${created.id}/ingest-repo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repository_url: repoUrl.trim() }),
      })
      const indexed = await index.json()
      if (!index.ok) throw new Error(indexed.detail || 'Repository ingestion failed.')
      setProject(created)
      await loadDocuments(created.id)
      const fullName = indexed?.repository?.full_name || repositoryName(repoUrl)
      const filesIngested = indexed?.ingestion?.files_ingested || 0
      setStatus(`Ingested ${filesIngested} files from ${fullName}. Chat and repairs now use this repository only.`)
    } catch (error) {
      setStatus(`Ingestion failed: ${error.message}`)
    } finally {
      setIngesting(false)
    }
  }

  const repair = async () => {
    if (!project) return setStatus('Ingest a repository before requesting a repair.')
    if (!trace.trim()) return setStatus('Paste the error or traceback you want fixed.')
    setRepairing(true)
    setRepairPlan(null)
    setRepairApplied(false)
    try {
      const response = await apiFetch(`${API_BASE}/projects/${project.id}/repair`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: targetFile || undefined, issue: { type: 'runtime', message: trace } }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Repair request failed.')
      setRepairPlan(data)
      setStatus(`Repair generated for ${data.file_path}. Review it below.`)
    } catch (error) {
      setStatus(`Repair failed: ${error.message}`)
    } finally {
      setRepairing(false)
    }
  }

  const applyRepair = async () => {
    if (!project || !repairPlan) return
    try {
      const response = await apiFetch(`${API_BASE}/projects/${project.id}/apply-repair`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: repairPlan.file_path, fixed_code: repairPlan.fixed_code }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not apply the repair.')
      setRepairApplied(true)
      setStatus(data.message)
      await loadDocuments(project.id)
    } catch (error) {
      setStatus(`Apply repair failed: ${error.message}`)
    }
  }

  const pushRepair = async () => {
    if (!project || !repairPlan || !repairApplied) return
    setPushing(true)
    try {
      const response = await apiFetch(`${API_BASE}/github/projects/${project.id}/pull-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: repairPlan.file_path,
          original_code: repairPlan.original_code,
          fixed_code: repairPlan.fixed_code,
          explanation: repairPlan.summary,
          commit_message: `fix: repair ${repairPlan.file_path}`,
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'GitHub pull request failed.')
      setPullRequest(data)
      setStatus(`Pull request #${data.pull_request_number} created.`)
    } catch (error) {
      setStatus(`GitHub push failed: ${error.message}`)
    } finally {
      setPushing(false)
    }
  }

  const audit = async () => {
    if (!project) return setStatus('Ingest a repository before auditing it.')
    setAuditing(true)
    try {
      const response = await apiFetch(`${API_BASE}/projects/${project.id}/audit`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Audit request failed.')
      setIssues(data.issues || [])
      if (!data.total) return setStatus('Auto scan complete: no static errors were found in this repository.')
      const first = data.issues[0]
      setTargetFile(first.file_path)
      setTrace(`${first.file_path}:${first.line}:${first.column} — ${first.message}`)
      setStatus(`Auto scan found ${data.total} issue(s). Select any issue below, then generate its repair.`)
    } catch (error) {
      setStatus(`Audit failed: ${error.message}`)
    } finally {
      setAuditing(false)
    }
  }

  const send = async () => {
    const question = chatInput.trim()
    if (!question || !project) return
    setMessages((items) => [...items, { role: 'You', text: question }])
    setChatInput('')
    setSending(true)
    try {
      const response = await apiFetch(`${API_BASE}/projects/${project.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Chat request failed.')
      setMessages((items) => [...items, { role: 'Copilot', text: data.answer, sources: data.sources || [] }])
    } catch (error) {
      setMessages((items) => [...items, { role: 'Copilot', text: `Chat failed: ${error.message}` }])
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 p-5 text-slate-100">
      <div className="mx-auto max-w-7xl space-y-5">
        <header>
          <h1 className="text-3xl font-semibold">AI/ML Copilot Engine</h1>
          <p className="text-slate-400">Repository-scoped repair and RAG chat</p>
        </header>

        <section className="rounded-2xl border border-slate-700 bg-slate-900 p-5">
          <h2 className="text-lg font-semibold">1. Connect and ingest a repository</h2>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <input
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 p-3"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
            />
            <button
              className="rounded-xl bg-violet-600 px-5 py-3 disabled:opacity-50"
              onClick={ingest}
              disabled={ingesting}
            >
              {ingesting ? 'Ingesting…' : 'Ingest Repository'}
            </button>
          </div>
          <p className="mt-3 text-sm text-emerald-300">{status}</p>
          {project && (
            <p className="mt-2 text-sm text-slate-400">
              Active repository: <span className="text-white">{project.name}</span> (project #{project.id})
            </p>
          )}
        </section>

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-700 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold">Ingested files</h2>
            {!documents.length ? (
              <p className="mt-3 text-slate-400">No repository is active.</p>
            ) : (
              <ul className="mt-3 max-h-72 space-y-2 overflow-auto">
                {documents.map((doc) => (
                  <li key={doc.id} className="rounded-lg bg-slate-950 p-2 text-sm">
                    <span>{doc.file_path}</span>
                    <span className="ml-2 text-slate-500">{doc.chunks_count} chunks</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold">Fix an error in this repository</h2>
            <textarea
              className="mt-3 h-36 w-full rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-sm"
              value={trace}
              onChange={(e) => { setTrace(e.target.value); setTargetFile('') }}
              placeholder="Paste an error trace. Include the file path when available."
            />
            <div className="mt-3 flex gap-3">
              <button
                className="rounded-xl bg-amber-600 px-4 py-2 disabled:opacity-50"
                onClick={repair}
                disabled={repairing}
              >
                {repairing ? 'Generating…' : 'Generate repair'}
              </button>
              <button
                className="rounded-xl border border-slate-600 px-4 py-2 disabled:opacity-50"
                onClick={audit}
                disabled={auditing}
              >
                {auditing ? 'Scanning…' : 'Auto error scan'}
              </button>
            </div>
            {issues.length > 0 && (
              <div className="mt-4 max-h-44 space-y-2 overflow-auto">
                <p className="text-sm text-amber-300">Detected errors ({issues.length})</p>
                {issues.map((issue, index) => (
                  <button
                    key={`${issue.file_path}-${issue.line}-${index}`}
                    onClick={() => {
                      setTargetFile(issue.file_path)
                      setTrace(`${issue.file_path}:${issue.line}:${issue.column} — ${issue.message}`)
                    }}
                    className="block w-full rounded-lg border border-amber-700/50 bg-slate-950 p-2 text-left text-xs hover:bg-amber-950/30"
                  >
                    <span className="font-medium text-amber-200">{issue.file_path}:{issue.line}</span>
                    <span className="ml-2 text-slate-300">{issue.message}</span>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>

        {repairPlan && (
          <section className="rounded-2xl border border-emerald-700 bg-slate-900 p-5">
            <h2 className="font-semibold">Review repair: {repairPlan.file_path}</h2>
            <p className="mt-2 text-slate-300">{repairPlan.summary}</p>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <pre className="max-h-96 overflow-auto rounded-xl bg-red-950/30 p-3 text-xs text-red-100">{repairPlan.original_code}</pre>
              <pre className="max-h-96 overflow-auto rounded-xl bg-emerald-950/30 p-3 text-xs text-emerald-100">{repairPlan.fixed_code}</pre>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button className="rounded-xl bg-emerald-600 px-4 py-2" onClick={applyRepair}>
                {repairApplied ? '' : ''}
              </button>
              <button
                className="rounded-xl bg-violet-600 px-4 py-2 disabled:opacity-50"
                onClick={pushRepair}
                disabled={!repairApplied || pushing}
              >
                {pushing ? '' : ''}
              </button>
              {pullRequest && (
                <a
                  className="rounded-xl border border-cyan-400 px-4 py-2 text-cyan-200"
                  href={pullRequest.pull_request_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open Pull Request
                </a>
              )}
            </div>
          </section>
        )}

        <section className="rounded-2xl border border-slate-700 bg-slate-900 p-5">
          <h2 className="text-lg font-semibold">Grok-style RAG chat</h2>
          <p className="text-sm text-slate-400">Answers are retrieved only from the active ingested repository.</p>
          <div className="mt-3 max-h-80 space-y-3 overflow-auto">
            {messages.map((message, i) => (
              <div key={i} className="rounded-xl bg-slate-950 p-3">
                <strong>{message.role}</strong>
                <p className="mt-1 whitespace-pre-wrap">{message.text}</p>
                {message.sources?.length > 0 && (
                  <p className="mt-2 text-xs text-violet-300">
                    Sources: {message.sources.map((s) => s.file_path).join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-3">
            <input
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 p-3"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              disabled={!project || sending}
              placeholder={project ? 'Ask about this repository…' : 'Ingest a repository first'}
            />
            <button
              className="rounded-xl bg-violet-600 px-5 disabled:opacity-50"
              onClick={send}
              disabled={!project || sending}
            >
              {sending ? 'Thinking…' : 'Send'}
            </button>
          </div>
        </section>
      </div>
    </main>
  )
}

export default App
