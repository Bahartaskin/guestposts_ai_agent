import express from "express";
import path from "path";
import fs from "fs";
import { spawn } from "child_process";
import { EventEmitter } from "events";
import { createServer as createViteServer } from "vite";


const app = express();

const PORT = 3000;

app.use(express.json());


type CampaignStatus =
  | "running"
  | "completed"
  | "error";


interface LogEntry {
  id: string;
  timestamp: string;
  step: string;
  message: string;
  type:
    | "info"
    | "action"
    | "condition"
    | "success"
    | "warning";
}


interface ResultEntry {
  id: string;
  url: string;
  actionTaken: string;
  contactDetail: string;
  timestamp: string;

  score: number;
  industryMatch: string;
  geographyMatch: string;
  potential: string;
  analysisMethod: string;
}


interface Campaign {
  status: CampaignStatus;
  geography: string;
  industry: string;
  logs: LogEntry[];
  results: ResultEntry[];
}


const activeCampaigns = new Map<
  string,
  Campaign
>();


const agentEmitter = new EventEmitter();


function createId(): string {
  return (
    Date.now().toString()
    + "-"
    + Math.random().toString(36).slice(2)
  );
}


function classifyLog(
  message: string
): {
  step: string;
  type: LogEntry["type"];
} {

  const lower = message.toLowerCase();

  if (
    lower.includes("search query")
    || lower.includes("searching the web")
  ) {
    return {
      step: "SEARCH",
      type: "action",
    };
  }

  if (
    lower.includes("getting website content")
    || lower.includes("scraping website")
  ) {
    return {
      step: "SCRAPE",
      type: "action",
    };
  }

  if (
    lower.includes("ai relevance")
    || lower.includes("heuristic relevance")
    || lower.includes("relevance score")
  ) {
    return {
      step: "RELEVANCE",
      type: "condition",
    };
  }

  if (
    lower.includes("website passed relevance")
    || lower.includes("qualification: qualified")
  ) {
    return {
      step: "QUALIFY",
      type: "success",
    };
  }

  if (
    lower.includes("skipping website")
  ) {
    return {
      step: "FILTER",
      type: "warning",
    };
  }

  if (
    lower.includes("extracting links")
    || lower.includes("relevant links")
  ) {
    return {
      step: "LINKS",
      type: "action",
    };
  }

  if (
    lower.includes("emails found")
    || lower.includes("contact emails")
    || lower.includes("valid / best")
  ) {
    return {
      step: "CONTACT",
      type: "action",
    };
  }

  if (
    lower.includes("outreach action")
    || lower.includes("action: email")
    || lower.includes("action: whatsapp")
  ) {
    return {
      step: "OUTREACH",
      type: "success",
    };
  }

  if (
    lower.includes("error")
    || lower.includes("failed")
  ) {
    return {
      step: "ERROR",
      type: "warning",
    };
  }

  return {
    step: "AGENT",
    type: "info",
  };
}


function emitLog(
  campaignId: string,
  message: string
) {

  const campaign =
    activeCampaigns.get(campaignId);

  if (!campaign) {
    return;
  }

  const cleanMessage =
    message.trim();

  if (!cleanMessage) {
    return;
  }

  const classification =
    classifyLog(cleanMessage);

  const logEntry: LogEntry = {
    id: createId(),
    timestamp: new Date().toISOString(),
    step: classification.step,
    message: cleanMessage,
    type: classification.type,
  };

  campaign.logs.push(logEntry);

  agentEmitter.emit(
    `log-${campaignId}`,
    logEntry
  );
}


function emitResult(
  campaignId: string,
  result: ResultEntry
) {

  const campaign =
    activeCampaigns.get(campaignId);

  if (!campaign) {
    return;
  }

  campaign.results.push(result);

  agentEmitter.emit(
    `result-${campaignId}`,
    result
  );
}


function loadPipelineResults(
  campaignId: string
) {

  const projectRoot =
    path.resolve(process.cwd(), "..");

  const resultsPath =
    path.join(
      projectRoot,
      "results.json"
    );

  if (!fs.existsSync(resultsPath)) {

    emitLog(
      campaignId,
      "results.json was not found."
    );

    return;
  }

  try {

    const raw =
      fs.readFileSync(
        resultsPath,
        "utf-8"
      );

    const parsed =
      JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      return;
    }

    for (const site of parsed) {

      const outreach =
        site.outreach || {};

      const action =
        outreach.action
        || "Manual Review";

      const status =
        outreach.status
        || "Required";

      const target =
        outreach.target
        || (
          site.emails
          && site.emails.length
            ? site.emails[0]
            : site.url
        );

      emitResult(
  campaignId,
  {
    id: createId(),
    url: site.url,
    actionTaken:
      `${action} ${status}`,
    contactDetail: target,
    timestamp:
      new Date().toISOString(),

    score: site.score ?? 0,
    industryMatch:
      site.industry_match ?? "",
    geographyMatch:
      site.geography_match ?? "",
    potential:
      site.potential ?? "",
    analysisMethod:
      site.analysis_method ?? "",
  }
);
    }

  } catch (error) {

    emitLog(
      campaignId,
      `Could not parse results.json: ${error}`
    );
  }
}


function runPythonAgent(
  campaignId: string,
  geography: string,
  industry: string
) {

  const campaign =
    activeCampaigns.get(campaignId);

  if (!campaign) {
    return;
  }

  const projectRoot =
    path.resolve(process.cwd(), "..");

  const pythonBinary =
    process.env.PYTHON_BIN
    || path.join(
      projectRoot,
      ".venv",
      "bin",
      "python"
    );

  const mainPath =
    path.join(
      projectRoot,
      "main.py"
    );

  emitLog(
    campaignId,
    `Starting GuestPosts.biz agent`
  );

  emitLog(
    campaignId,
    `Industry: ${industry} | Geography: ${geography}`
  );


  const child = spawn(
    pythonBinary,
    [
      "-u",
      mainPath,
    ],
    {
      cwd: projectRoot,

      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },

      stdio: [
        "pipe",
        "pipe",
        "pipe",
      ],
    }
  );


  child.stdin.write(
    `${industry}\n`
  );

  child.stdin.write(
    `${geography}\n`
  );

  child.stdin.end();


  let stdoutBuffer = "";

  child.stdout.on(
    "data",
    (data) => {

      stdoutBuffer +=
        data.toString();

      const lines =
        stdoutBuffer.split("\n");

      stdoutBuffer =
        lines.pop() || "";

      for (const line of lines) {

        emitLog(
          campaignId,
          line
        );
      }
    }
  );


  let stderrBuffer = "";

  child.stderr.on(
    "data",
    (data) => {

      stderrBuffer +=
        data.toString();

      const lines =
        stderrBuffer.split("\n");

      stderrBuffer =
        lines.pop() || "";

      for (const line of lines) {

        const clean =
          line.trim();

        if (!clean) {
          continue;
        }

        emitLog(
          campaignId,
          clean
        );
      }
    }
  );


  child.on(
    "error",
    (error) => {

      emitLog(
        campaignId,
        `Python process failed: ${error.message}`
      );

      campaign.status = "error";

      agentEmitter.emit(
        `status-${campaignId}`,
        "error"
      );
    }
  );


  child.on(
    "close",
    (code) => {

      if (stdoutBuffer.trim()) {

        emitLog(
          campaignId,
          stdoutBuffer
        );
      }

      if (stderrBuffer.trim()) {

        emitLog(
          campaignId,
          stderrBuffer
        );
      }


      if (code === 0) {

        loadPipelineResults(
          campaignId
        );

        campaign.status =
          "completed";

        emitLog(
          campaignId,
          "Campaign finished successfully."
        );

        agentEmitter.emit(
          `status-${campaignId}`,
          "completed"
        );

      } else {

        campaign.status =
          "error";

        emitLog(
          campaignId,
          `Agent exited with code ${code}`
        );

        agentEmitter.emit(
          `status-${campaignId}`,
          "error"
        );
      }
    }
  );
}


// ============================================================
// CREATE CAMPAIGN
// ============================================================

app.post(
  "/api/campaigns",
  (req, res) => {

    const {
      geography,
      industry,
    } = req.body;


    if (
      !geography
      || !industry
    ) {

      return res
        .status(400)
        .json({
          error:
            "Geography and industry are required",
        });
    }


    const campaignId =
      `camp-${createId()}`;


    activeCampaigns.set(
      campaignId,
      {
        status: "running",
        geography,
        industry,
        logs: [],
        results: [],
      }
    );


    runPythonAgent(
      campaignId,
      geography,
      industry
    );


    return res.json({
      campaignId,
    });
  }
);


// ============================================================
// GET CAMPAIGN
// ============================================================

app.get(
  "/api/campaigns/:id",
  (req, res) => {

    const campaign =
      activeCampaigns.get(
        req.params.id
      );


    if (!campaign) {

      return res
        .status(404)
        .json({
          error:
            "Campaign not found",
        });
    }


    return res.json(
      campaign
    );
  }
);


// ============================================================
// SSE STREAM
// ============================================================

app.get(
  "/api/campaigns/:id/stream",
  (req, res) => {

    const campaignId =
      req.params.id;

    const campaign =
      activeCampaigns.get(
        campaignId
      );


    if (!campaign) {

      return res
        .status(404)
        .json({
          error:
            "Campaign not found",
        });
    }


    res.setHeader(
      "Content-Type",
      "text/event-stream"
    );

    res.setHeader(
      "Cache-Control",
      "no-cache"
    );

    res.setHeader(
      "Connection",
      "keep-alive"
    );

    res.flushHeaders();


    res.write(
      `data: ${JSON.stringify({
        type: "status",
        data: campaign.status,
      })}\n\n`
    );


    for (const log of campaign.logs) {

      res.write(
        `data: ${JSON.stringify({
          type: "log",
          data: log,
        })}\n\n`
      );
    }


    for (
      const result
      of campaign.results
    ) {

      res.write(
        `data: ${JSON.stringify({
          type: "result",
          data: result,
        })}\n\n`
      );
    }


    const onLog =
      (log: LogEntry) => {

        res.write(
          `data: ${JSON.stringify({
            type: "log",
            data: log,
          })}\n\n`
        );
      };


    const onResult =
      (result: ResultEntry) => {

        res.write(
          `data: ${JSON.stringify({
            type: "result",
            data: result,
          })}\n\n`
        );
      };


    const onStatus =
      (status: CampaignStatus) => {

        res.write(
          `data: ${JSON.stringify({
            type: "status",
            data: status,
          })}\n\n`
        );
      };


    agentEmitter.on(
      `log-${campaignId}`,
      onLog
    );

    agentEmitter.on(
      `result-${campaignId}`,
      onResult
    );

    agentEmitter.on(
      `status-${campaignId}`,
      onStatus
    );


    req.on(
      "close",
      () => {

        agentEmitter.off(
          `log-${campaignId}`,
          onLog
        );

        agentEmitter.off(
          `result-${campaignId}`,
          onResult
        );

        agentEmitter.off(
          `status-${campaignId}`,
          onStatus
        );
      }
    );
  }
);


// ============================================================
// START SERVER
// ============================================================

async function startServer() {

  if (
    process.env.NODE_ENV
    !== "production"
  ) {

    const vite =
      await createViteServer({
        server: {
          middlewareMode: true,
        },

        appType: "spa",
      });

    app.use(
      vite.middlewares
    );

  } else {

    const distPath =
      path.join(
        process.cwd(),
        "dist"
      );

    app.use(
      express.static(
        distPath
      )
    );

    app.get(
      "*",
      (_req, res) => {

        res.sendFile(
          path.join(
            distPath,
            "index.html"
          )
        );
      }
    );
  }


  app.listen(
    PORT,
    "0.0.0.0",
    () => {

      console.log(
        `GuestPosts.biz demo running on http://localhost:${PORT}`
      );
    }
  );
}


startServer();