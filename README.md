
# GuestPosts.biz AI Agent

An AI-assisted guest post discovery and outreach preparation agent.

The project automates the early stages of guest-post outreach by searching for potential publisher websites, evaluating their relevance, discovering contact information, and preparing outreach for qualified opportunities.

A local web interface is included to make the full pipeline easy to run and review.

## Current Status

The project currently has a working end-to-end demo.

The demo supports:

- Campaign-based website discovery using an **industry** and **geography**
- Guest-post focused web search
- AI-assisted relevance evaluation
- Conservative heuristic fallback when an AI provider is unavailable
- Industry, geography, and guest-post-potential scoring
- Filtering of irrelevant or low-quality opportunities
- Contact email discovery
- Scanning of relevant pages such as contact, contributor, blog, and write-for-us pages
- Email filtering and prioritization
- Outreach preparation without automatically sending messages
- Live execution logs through the web interface
- Campaign summary statistics
- Detailed qualified-opportunity views
- JSON and CSV result output
- Automated tests for core pipeline behavior

## Demo Workflow

```text
Industry + Geography
        |
        v
Guest Post Search
        |
        v
Candidate Websites
        |
        v
Relevance Analysis
   /            \
 AI          Heuristic
                Fallback
        |
        v
Qualification
   /            \
Reject        Qualified
                 |
                 v
          Website Scraping
                 |
                 v
          Contact Discovery
                 |
                 v
          Email Validation
                 |
                 v
        Outreach Preparation
                 |
                 v
             Demo UI
```

## Example Campaign

A sample campaign can be run with:

```text
Industry: sports
Geography: UAE
```

The agent builds a guest-post-oriented search query and evaluates the returned websites.

In the current development example, geographically irrelevant sports publishers are rejected while a UAE-connected opportunity can proceed to contact discovery and outreach preparation.

The exact results can vary because search results and website content change over time.

## Relevance Analysis

Each candidate is evaluated using signals including:

- Industry relevance
- Geographic relevance
- Guest-post availability
- Publisher characteristics
- Marketplace / SEO-service indicators

The result contains fields such as:

```text
Relevance Score
Industry Match
Geography Match
Guest Post Potential
Analysis Method
Reason
```

The system can use an AI provider for relevance analysis. If the configured provider is unavailable because of quota, rate limits, or another provider error, the pipeline can fall back to conservative heuristic analysis instead of stopping the campaign.

This fallback is intended to keep the demo functional while avoiding overly permissive qualification.

## Contact Discovery

Only qualified opportunities proceed to deeper website processing.

The scraper can inspect the main page and relevant internal pages, including:

- Contact pages
- Write-for-us pages
- Contributor pages
- Guest-post submission pages
- Blog/editorial pages

Discovered email addresses are filtered before being presented as outreach targets.

Obvious placeholder or unsuitable addresses can be excluded from the final contact list.

## Outreach Preparation

For a qualified opportunity, the agent can select a preferred contact and prepare an outreach action.

Current demo behavior is intentionally safe:

> Outreach is prepared for review, but messages are not automatically sent.

Automated email/contact-form execution can be added as a later controlled stage.

## Web Interface

The project includes a React + TypeScript demo UI.

The interface provides:

- Campaign configuration
- Start-agent controls
- Live pipeline logs
- Campaign status
- Websites-found summary
- Qualified/rejected counts
- Outreach-prepared count
- Qualified opportunities table
- Relevance score and match indicators
- Contact information
- Opportunity detail view
- Prepared outreach information

The local application runs at:

```text
http://localhost:3000
```

`localhost` is only accessible from the machine running the application. Public deployment is planned separately.

## Project Structure

```text
guestposts_ai_agent/
├── main.py
├── search.py
├── relevance.py
├── scraper.py
├── outreach.py
├── logger.py
├── requirements.txt
├── results.json
├── results.csv
├── logs/
├── tests/
└── ui/
    ├── src/
    │   ├── App.tsx
    │   ├── index.css
    │   └── main.tsx
    ├── server.ts
    ├── package.json
    └── vite.config.ts
```

## Requirements

### Backend

- Python
- Project dependencies listed in `requirements.txt`

### Demo UI

- Node.js
- npm
- React
- TypeScript
- Vite
- Express

## Local Setup

Clone the repository:

```bash
git clone https://github.com/Bahartaskin/guestposts_ai_agent.git
cd guestposts_ai_agent
```

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install UI dependencies:

```bash
cd ui
npm install
```

## Environment Variables

Create a local `.env` file in the project root and configure the providers you want to use.

For example:

```env
AI_PROVIDER=auto

TAVILY_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

Do **not** commit API keys or the `.env` file to GitHub.

Provider availability depends on the configured accounts, credits, and quotas.

## Run the CLI Pipeline

From the project root:

```bash
source .venv/bin/activate
python main.py
```

The program will request:

```text
Enter industry:
Enter geography:
```

## Run the Demo UI

From the `ui` directory:

```bash
npm run dev
```

Then open:

```text
http://localhost:3000
```

The Express server connects the React interface to the Python agent and streams campaign progress to the UI.

## Tests

Run the Python test suite from the project root:

```bash
python -m pytest -q
```

The project includes tests for areas such as relevance heuristics, search behavior, result parsing, and outreach preparation.

Before committing UI changes, also run:

```bash
cd ui
npm run build
```

## Output

Campaign results are written to:

```text
results.json
results.csv
```

Runtime logs are stored under:

```text
logs/
```

These files are primarily development/runtime artifacts and may change after each campaign.

## Technology Stack

**Backend**

- Python
- Requests
- BeautifulSoup
- Tavily search integration
- Gemini / OpenAI relevance integrations
- Heuristic relevance fallback

**Frontend / Demo Layer**

- React
- TypeScript
- Vite
- Express
- Lucide React

## Current Development Priorities

The next phase focuses on moving from a working MVP/demo toward a more production-ready agent.

Planned improvements include:

1. More robust AI-provider availability and relevance evaluation
2. Broader qualification testing across industries and geographies
3. Improved publisher-quality and false-positive detection
4. Stronger contact validation and prioritization
5. Controlled outreach execution with approval and rate limits
6. Persistent campaign/result storage
7. Public deployment of the demo
8. Additional monitoring, logging, and production hardening

## Safety and Outreach Controls

The current implementation separates **discovery/qualification** from **message execution**.

This allows a human reviewer to inspect:

- Why a website qualified
- Which contacts were discovered
- Which pages were used
- What outreach action is being prepared

before any future sending capability is enabled.

## Repository

GitHub:

https://github.com/Bahartaskin/guestposts_ai_agent

---

**GuestPosts.biz AI Agent — Working MVP / Demo**
