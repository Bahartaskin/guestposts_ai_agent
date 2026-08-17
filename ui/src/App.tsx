import {
  Activity,
  AlertCircle,
  Bot,
  Briefcase,
  CheckCircle2,
  FileText,
  Globe,
  Loader2,
  Mail,
  MessageCircle,
  Play,
  Terminal,
} from 'lucide-react'
import {
  useEffect,
  useRef,
  useState,
} from 'react'


interface LogEntry {
  id: string
  timestamp: string
  step: string
  message: string
  type:
    | 'info'
    | 'action'
    | 'condition'
    | 'success'
    | 'warning'
}


interface ResultEntry {
  id: string
  url: string
  actionTaken: string
  contactDetail: string
  timestamp: string

  score: number
  industryMatch: string
  geographyMatch: string
  potential: string
  analysisMethod: string
}


type CampaignStatus =
  | 'idle'
  | 'running'
  | 'completed'
  | 'error'


function App() {
  const [geography, setGeography] =
    useState('')

  const [industry, setIndustry] =
    useState('')

  const [campaignId, setCampaignId] =
    useState<string | null>(null)

  const [status, setStatus] =
    useState<CampaignStatus>('idle')

  const [logs, setLogs] =
    useState<LogEntry[]>([])

  const [results, setResults] =
    useState<ResultEntry[]>([])

  const logsEndRef =
    useRef<HTMLDivElement>(null)


  // ========================================================
  // AUTO-SCROLL TERMINAL
  // ========================================================

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [logs])


  // ========================================================
  // SSE CONNECTION
  // ========================================================

  useEffect(() => {
    if (!campaignId) {
      return
    }

    const eventSource =
      new EventSource(
        `/api/campaigns/${campaignId}/stream`,
      )


    eventSource.onmessage = (event) => {
      try {
        const parsed =
          JSON.parse(event.data)

        if (parsed.type === 'log') {
          setLogs((previous) => {
            const exists =
              previous.some(
                (item) =>
                  item.id === parsed.data.id,
              )

            if (exists) {
              return previous
            }

            return [
              ...previous,
              parsed.data,
            ]
          })
        }

        if (parsed.type === 'result') {
          setResults((previous) => {
            const exists =
              previous.some(
                (item) =>
                  item.id === parsed.data.id,
              )

            if (exists) {
              return previous
            }

            return [
              ...previous,
              parsed.data,
            ]
          })
        }

        if (parsed.type === 'status') {
          setStatus(parsed.data)

          if (
            parsed.data === 'completed'
            || parsed.data === 'error'
          ) {
            eventSource.close()
          }
        }
      } catch (error) {
        console.error(
          'Could not parse SSE event:',
          error,
        )
      }
    }


    eventSource.onerror = () => {
      console.error(
        'Campaign SSE connection failed.',
      )

      eventSource.close()
    }


    return () => {
      eventSource.close()
    }
  }, [campaignId])


  // ========================================================
  // START CAMPAIGN
  // ========================================================

  const handleStart = async (
    event?: React.FormEvent,
  ) => {
    event?.preventDefault()

    if (
      status === 'running'
      || !geography.trim()
      || !industry.trim()
    ) {
      return
    }

    setLogs([])
    setResults([])
    setCampaignId(null)
    setStatus('running')

    try {
      const response =
        await fetch(
          '/api/campaigns',
          {
            method: 'POST',
            headers: {
              'Content-Type':
                'application/json',
            },
            body: JSON.stringify({
              geography:
                geography.trim(),
              industry:
                industry.trim(),
            }),
          },
        )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          data.error
          || 'Could not start campaign.',
        )
      }

      if (!data.campaignId) {
        throw new Error(
          'Campaign ID was not returned.',
        )
      }

      setCampaignId(
        data.campaignId,
      )
    } catch (error) {
      console.error(error)

      setStatus('error')

      setLogs([
        {
          id: `frontend-${Date.now()}`,
          timestamp:
            new Date().toISOString(),
          step: 'ERROR',
          message:
            error instanceof Error
              ? error.message
              : 'Could not start campaign.',
          type: 'warning',
        },
      ])
    }
  }


  // ========================================================
  // KEYBOARD SHORTCUT
  // ========================================================

  const handleKeyDown = (
    event:
      React.KeyboardEvent<HTMLFormElement>,
  ) => {
    if (
      (event.ctrlKey || event.metaKey)
      && event.key === 'Enter'
    ) {
      event.preventDefault()

      void handleStart()
    }
  }


  // ========================================================
  // UI HELPERS
  // ========================================================

  const getLogIcon = (
    type: LogEntry['type'],
  ) => {
    switch (type) {
      case 'action':
        return (
          <Play
            size={15}
            className="log-icon action"
          />
        )

      case 'condition':
        return (
          <Activity
            size={15}
            className="log-icon condition"
          />
        )

      case 'success':
        return (
          <CheckCircle2
            size={15}
            className="log-icon success"
          />
        )

      case 'warning':
        return (
          <AlertCircle
            size={15}
            className="log-icon warning"
          />
        )

      default:
        return (
          <Bot
            size={15}
            className="log-icon info"
          />
        )
    }
  }


  const getActionIcon = (
    action: string,
  ) => {
    const value =
      action.toLowerCase()

    if (value.includes('email')) {
      return <Mail size={16} />
    }

    if (
      value.includes('whatsapp')
    ) {
      return (
        <MessageCircle size={16} />
      )
    }

    return <FileText size={16} />
  }


  const getHostname = (
    url: string,
  ) => {
    try {
      return new URL(url)
        .hostname
        .replace('www.', '')
    } catch {
      return url
    }
  }


  const statusLabel = {
    idle: 'Ready',
    running: 'Running',
    completed: 'Completed',
    error: 'Error',
  }[status]


  return (
    <div className="app-shell">
      {/* ================================================== */}
      {/* HEADER */}
      {/* ================================================== */}

      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-icon">
              <Bot size={21} />
            </div>

            <div>
              <h1>
                GuestPosts.biz Agent
              </h1>

              <p>
                Guest Post Discovery
                & Outreach Pipeline
              </p>
            </div>
          </div>

          <div className="status">
            <span
              className={
                `status-dot ${status}`
              }
            />

            <span>
              {statusLabel}
            </span>
          </div>
        </div>
      </header>


      {/* ================================================== */}
      {/* MAIN */}
      {/* ================================================== */}

      <main className="dashboard">
        {/* ================================================= */}
        {/* CONFIG */}
        {/* ================================================= */}

        <aside className="sidebar">
          <section className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Play size={17} />

                <span>
                  New Campaign
                </span>
              </div>

              <p>
                Define campaign
                parameters and run the
                discovery agent.
              </p>
            </div>

            <form
              className="campaign-form"
              onSubmit={handleStart}
              onKeyDown={
                handleKeyDown
              }
            >
              <label>
                <span className="label-row">
                  <Globe size={16} />
                  Geography
                </span>

                <input
                  value={geography}
                  onChange={(event) =>
                    setGeography(
                      event.target.value,
                    )
                  }
                  disabled={
                    status === 'running'
                  }
                  placeholder="e.g. UAE, UK, USA"
                />
              </label>


              <label>
                <span className="label-row">
                  <Briefcase
                    size={16}
                  />
                  Industry
                </span>

                <input
                  value={industry}
                  onChange={(event) =>
                    setIndustry(
                      event.target.value,
                    )
                  }
                  disabled={
                    status === 'running'
                  }
                  placeholder="e.g. Sports, Finance, Tech"
                />
              </label>


              <button
                type="submit"
                className="start-button"
                disabled={
                  status === 'running'
                  || !geography.trim()
                  || !industry.trim()
                }
              >
                {status === 'running'
                  ? (
                    <>
                      <Loader2
                        size={18}
                        className="spinner"
                      />

                      Agent is Running...
                    </>
                  )
                  : (
                    <>
                      <Bot size={18} />

                      Start Agent
                    </>
                  )
                }
              </button>

              <span className="shortcut">
                Ctrl / Cmd + Enter
              </span>
            </form>
          </section>


          <section className="info-panel">
            <div className="info-title">
              <AlertCircle
                size={17}
              />

              Demo Mode
            </div>

            <p>
              Outreach actions are
              prepared but not sent.
              The demo uses the real
              discovery, scraping,
              relevance and contact
              pipeline.
            </p>

            <div className="pipeline-mini">
              <span>
                Search
              </span>
              <span>→</span>
              <span>
                Relevance
              </span>
              <span>→</span>
              <span>
                Contact
              </span>
              <span>→</span>
              <span>
                Outreach
              </span>
            </div>
          </section>
        </aside>


        {/* ================================================= */}
        {/* MAIN CONTENT */}
        {/* ================================================= */}

        <section className="workspace">
          {/* TERMINAL */}

          <div className="terminal-panel">
            <div className="terminal-header">
              <div>
                <Terminal size={16} />

                <span>
                  agent-execution.log
                </span>
              </div>

              <div className="window-dots">
                <span />
                <span />
                <span />
              </div>
            </div>


            <div className="terminal-body">
              {logs.length === 0
                ? (
                  <div className="terminal-empty">
                    Waiting for a campaign
                    to start...
                  </div>
                )
                : (
                  <div className="log-list">
                    {logs.map(
                      (log) => (
                        <div
                          className="log-row"
                          key={log.id}
                        >
                          <span className="log-time">
                            {new Date(
                              log.timestamp,
                            ).toLocaleTimeString(
                              [],
                              {
                                hour12:
                                  false,
                                hour:
                                  '2-digit',
                                minute:
                                  '2-digit',
                                second:
                                  '2-digit',
                              },
                            )}
                          </span>

                          <span className="log-symbol">
                            {getLogIcon(
                              log.type,
                            )}
                          </span>

                          <span className="log-step">
                            [{log.step}]
                          </span>

                          <span
                            className={
                              `log-message ${log.type}`
                            }
                          >
                            {log.message}
                          </span>
                        </div>
                      ),
                    )}

                    <div
                      ref={logsEndRef}
                    />
                  </div>
                )
              }
            </div>
          </div>


          {/* RESULTS */}

          <div className="results-panel">
            <div className="results-header">
              <div className="panel-title">
                <Briefcase
                  size={17}
                />

                <span>
                  Qualified Opportunities
                </span>
              </div>

              <span className="result-count">
                Total: {results.length}
              </span>
            </div>


            <div className="table-wrapper">
              <table>
                <thead>
  <tr>
    <th>Website</th>
    <th>Score</th>
    <th>Industry</th>
    <th>Geography</th>
    <th>Guest Post</th>
    <th>Method</th>
    <th>Outreach</th>
    <th>Contact</th>
  </tr>
</thead>
                <tbody>
                  {results.length === 0
                    ? (
                      <tr>
                        <td
                          colSpan={8}
                          className="empty-results"
                        >
                          No qualified
                          opportunities yet.
                        </td>
                      </tr>
                    )
                    : results.map(
                      (result) => (
                        <tr
                          key={
                            result.id
                          }
                        >
                          
<td>
  <a
    href={result.url}
    target="_blank"
    rel="noreferrer"
  >
    {getHostname(result.url)}
  </a>
</td>

<td>
  <span className="score-badge">
    {result.score}
  </span>
</td>

<td>
  <span
    className={`match-badge ${result.industryMatch.toLowerCase()}`}
  >
    {result.industryMatch}
  </span>
</td>

<td>
  <span
    className={`match-badge ${result.geographyMatch.toLowerCase()}`}
  >
    {result.geographyMatch}
  </span>
</td>

<td>
  <span
    className={`match-badge ${result.potential.toLowerCase()}`}
  >
    {result.potential}
  </span>
</td>

<td>
  <span className="method-badge">
    {result.analysisMethod}
  </span>
</td>

<td>
  <span className="action-cell">
    {getActionIcon(
      result.actionTaken,
    )}
    {result.actionTaken}
  </span>
</td>

<td className="contact-cell">
  {result.contactDetail}
</td>
<td>
  <span className="action-cell">
    {getActionIcon(
      result.actionTaken,
    )}

    {result.actionTaken}
  </span>
</td>

<td className="contact-cell">
  {result.contactDetail}
</td>
                        </tr>
                      ),
                    )
                  }
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}


export default App