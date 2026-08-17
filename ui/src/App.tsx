import {
  Activity,
  AlertCircle,
  Bot,
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
  Globe,
  Loader2,
  Mail,
  MessageCircle,
  Play,
  Terminal,
  X,
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
  title: string

  actionTaken: string
  contactDetail: string
  timestamp: string

  score: number
  industryMatch: string
  geographyMatch: string
  potential: string
  analysisMethod: string

  reason: string

  emails: string[]
  excludedEmails: string[]
  sourcePages: string[]

  outreachSubject: string
  outreachMessage: string
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

  const [
    selectedResult,
    setSelectedResult,
  ] = useState<ResultEntry | null>(null)

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
    setSelectedResult(null)
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


  // ========================================================
  // CAMPAIGN SUMMARY
  // ========================================================

  const websitesFound = (() => {
    for (const log of logs) {
      const match =
        log.message.match(
          /Found\s+(\d+)\s+results/i,
        )

      if (match) {
        return Number(match[1])
      }
    }

    return 0
  })()


  const rejectedCount =
    logs.filter(
      (log) =>
        log.message
          .toLowerCase()
          .includes(
            'skipping website - not a qualified',
          ),
    ).length


  const qualifiedCount =
    results.length


  const outreachPreparedCount =
    results.filter(
      (result) =>
        result.actionTaken
          .toLowerCase()
          .includes('prepared'),
    ).length


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


          {/* ================================================= */}
          {/* CAMPAIGN SUMMARY */}
          {/* ================================================= */}

          <section className="summary-grid">
            <div className="summary-card">
              <div className="summary-icon">
                <Globe size={18} />
              </div>

              <div>
                <span className="summary-label">
                  Websites Found
                </span>

                <strong>
                  {websitesFound}
                </strong>
              </div>
            </div>


            <div className="summary-card">
              <div className="summary-icon success">
                <CheckCircle2 size={18} />
              </div>

              <div>
                <span className="summary-label">
                  Qualified
                </span>

                <strong>
                  {qualifiedCount}
                </strong>
              </div>
            </div>


            <div className="summary-card">
              <div className="summary-icon rejected">
                <AlertCircle size={18} />
              </div>

              <div>
                <span className="summary-label">
                  Rejected
                </span>

                <strong>
                  {rejectedCount}
                </strong>
              </div>
            </div>


            <div className="summary-card">
              <div className="summary-icon outreach">
                <Mail size={18} />
              </div>

              <div>
                <span className="summary-label">
                  Outreach Prepared
                </span>

                <strong>
                  {outreachPreparedCount}
                </strong>
              </div>
            </div>
          </section>


          {/* ================================================= */}
          {/* RESULTS */}
          {/* ================================================= */}

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
                    <th />
                  </tr>
                </thead>

                <tbody>
                  {results.length === 0
                    ? (
                      <tr>
                        <td
                          colSpan={9}
                          className="empty-results"
                        >
                          No qualified
                          opportunities yet.
                        </td>
                      </tr>
                    )
                    : results.map(
                      (result) => {
                        const isSelected =
                          selectedResult?.id
                          === result.id

                        return (
                          <tr
                            key={result.id}
                            className={
                              `result-row ${
                                isSelected
                                  ? 'selected'
                                  : ''
                              }`
                            }
                            onClick={() =>
                              setSelectedResult(
                                isSelected
                                  ? null
                                  : result,
                              )
                            }
                          >
                            <td>
                              <a
                                href={result.url}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(event) =>
                                  event.stopPropagation()
                                }
                              >
                                {getHostname(
                                  result.url,
                                )}
                              </a>
                            </td>

                            <td>
                              <span className="score-badge">
                                {result.score}
                              </span>
                            </td>

                            <td>
                              <span
                                className={
                                  `match-badge ${
                                    result
                                      .industryMatch
                                      .toLowerCase()
                                  }`
                                }
                              >
                                {
                                  result.industryMatch
                                }
                              </span>
                            </td>

                            <td>
                              <span
                                className={
                                  `match-badge ${
                                    result
                                      .geographyMatch
                                      .toLowerCase()
                                  }`
                                }
                              >
                                {
                                  result.geographyMatch
                                }
                              </span>
                            </td>

                            <td>
                              <span
                                className={
                                  `match-badge ${
                                    result
                                      .potential
                                      .toLowerCase()
                                  }`
                                }
                              >
                                {
                                  result.potential
                                }
                              </span>
                            </td>

                            <td>
                              <span className="method-badge">
                                {
                                  result.analysisMethod
                                }
                              </span>
                            </td>

                            <td>
                              <span className="action-cell">
                                {getActionIcon(
                                  result.actionTaken,
                                )}

                                {
                                  result.actionTaken
                                }
                              </span>
                            </td>

                            <td className="contact-cell">
                              {
                                result.contactDetail
                              }
                            </td>

                            <td className="expand-cell">
                              {isSelected
                                ? (
                                  <ChevronUp
                                    size={16}
                                  />
                                )
                                : (
                                  <ChevronDown
                                    size={16}
                                  />
                                )
                              }
                            </td>
                          </tr>
                        )
                      },
                    )
                  }
                </tbody>
              </table>
            </div>
          </div>


          {/* ================================================= */}
          {/* SELECTED OPPORTUNITY DETAIL */}
          {/* ================================================= */}

          {selectedResult && (
            <section className="detail-panel">
              <div className="detail-header">
                <div>
                  <span className="detail-eyebrow">
                    Qualified Opportunity
                  </span>

                  <h2>
                    {selectedResult.title
                      || getHostname(
                        selectedResult.url,
                      )
                    }
                  </h2>

                  <a
                    href={selectedResult.url}
                    target="_blank"
                    rel="noreferrer"
                    className="detail-url"
                  >
                    {getHostname(
                      selectedResult.url,
                    )}

                    <ExternalLink
                      size={13}
                    />
                  </a>
                </div>

                <button
                  type="button"
                  className="detail-close"
                  onClick={() =>
                    setSelectedResult(null)
                  }
                  aria-label="Close detail panel"
                >
                  <X size={18} />
                </button>
              </div>


              <div className="detail-score-row">
                <div>
                  <span>Score</span>
                  <strong>
                    {selectedResult.score}
                  </strong>
                </div>

                <div>
                  <span>Industry</span>
                  <strong>
                    {
                      selectedResult.industryMatch
                    }
                  </strong>
                </div>

                <div>
                  <span>Geography</span>
                  <strong>
                    {
                      selectedResult.geographyMatch
                    }
                  </strong>
                </div>

                <div>
                  <span>Guest Post</span>
                  <strong>
                    {
                      selectedResult.potential
                    }
                  </strong>
                </div>

                <div>
                  <span>Method</span>
                  <strong>
                    {
                      selectedResult.analysisMethod
                    }
                  </strong>
                </div>
              </div>


              <div className="detail-grid">
                <div className="detail-section detail-wide">
                  <h3>
                    Why it qualified
                  </h3>

                  <p>
                    {selectedResult.reason
                      || 'No relevance reason was provided.'
                    }
                  </p>
                </div>


                <div className="detail-section">
                  <h3>
                    Contact emails
                  </h3>

                  {selectedResult.emails.length > 0
                    ? (
                      <ul className="detail-list">
                        {selectedResult.emails.map(
                          (email) => (
                            <li key={email}>
                              <Mail size={14} />
                              <span>
                                {email}
                              </span>
                            </li>
                          ),
                        )}
                      </ul>
                    )
                    : (
                      <p className="muted">
                        No validated emails found.
                      </p>
                    )
                  }
                </div>


                <div className="detail-section">
                  <h3>
                    Excluded emails
                  </h3>

                  {selectedResult.excludedEmails.length > 0
                    ? (
                      <ul className="detail-list excluded">
                        {selectedResult.excludedEmails.map(
                          (email) => (
                            <li key={email}>
                              <AlertCircle
                                size={14}
                              />
                              <span>
                                {email}
                              </span>
                            </li>
                          ),
                        )}
                      </ul>
                    )
                    : (
                      <p className="muted">
                        None
                      </p>
                    )
                  }
                </div>


                <div className="detail-section detail-wide">
                  <h3>
                    Relevant pages
                  </h3>

                  {selectedResult.sourcePages.length > 0
                    ? (
                      <div className="source-page-list">
                        {selectedResult.sourcePages.map(
                          (page) => (
                            <a
                              key={page}
                              href={page}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <ExternalLink
                                size={13}
                              />

                              <span>
                                {page}
                              </span>
                            </a>
                          ),
                        )}
                      </div>
                    )
                    : (
                      <p className="muted">
                        No additional relevant pages detected.
                      </p>
                    )
                  }
                </div>


                <div className="detail-section detail-wide outreach-detail">
                  <div className="detail-section-title">
                    <div>
                      <Mail size={16} />

                      <h3>
                        Prepared outreach
                      </h3>
                    </div>

                    <span className="prepared-pill">
                      Prepared
                    </span>
                  </div>

                  {selectedResult.outreachSubject && (
                    <div className="outreach-field">
                      <span>
                        Subject
                      </span>

                      <strong>
                        {
                          selectedResult.outreachSubject
                        }
                      </strong>
                    </div>
                  )}

                  <div className="outreach-field">
                    <span>
                      Target
                    </span>

                    <strong>
                      {
                        selectedResult.contactDetail
                      }
                    </strong>
                  </div>

                  {selectedResult.outreachMessage
                    ? (
                      <div className="outreach-message">
                        {
                          selectedResult.outreachMessage
                        }
                      </div>
                    )
                    : (
                      <p className="muted">
                        No outreach message was prepared.
                      </p>
                    )
                  }
                </div>
              </div>
            </section>
          )}
        </section>
      </main>
    </div>
  )
}


export default App