import { useActivityFeedIndex } from "@/hooks/useActivityFeedIndex";
import { useAgentActivityFeed } from "@/hooks/useAgentActivityFeed";
import { useSimulationResult } from "@/hooks/useSimulationResult";
import personasData from "../../sns-vibe/seeds/personas.json";

type PersonaSeed = {
  username: string;
  age_range: string;
  location: string;
  occupation: string;
  personality_traits: string[];
  communication_style: string;
  interests: string[];
  preferred_content_types: string[];
  engagement_level: string;
  posting_frequency: string;
  active_hours: string;
};

const numberFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const formatNumber = (value: number) => numberFormatter.format(value);
const defaultActionCosts: Record<string, number> = {
  like: 1,
  comment: 3,
  follow: 5,
  share: 2,
  explore: 1,
  scroll: 0.5,
  skip: 0
};

export default function App() {
  const simulationId = import.meta.env.VITE_SIMULATION_ID ?? "latest";
  const { result, status, lastUpdated } = useSimulationResult(simulationId, { intervalMs: 2000 });
  const simulation = result;
  const { index: activityIndex } = useActivityFeedIndex({ intervalMs: 5000 });
  const envFiles = (import.meta.env.VITE_AGENT_FEEDS ?? "agent-01.jsonl,agent-02.jsonl,agent-03.jsonl")
    .split(",")
    .map((item: string) => item.trim())
    .filter(Boolean);
  const agentFiles = activityIndex?.files?.length ? activityIndex.files : envFiles;
  const {
    events: activityEvents,
    status: activityStatus,
    lastUpdated: activityUpdated
  } = useAgentActivityFeed(agentFiles, { intervalMs: 2000, maxLines: 200, limit: 120 });
  const agentMap = new Map<
    string,
    {
      id: string;
      total: number;
      lastAction: string;
      lastTimestamp: string;
      actionCounts: Record<string, number>;
      lastTs: number;
    }
  >();
  const actionTotals: Record<string, number> = {};

  activityEvents.forEach(event => {
    const id = event.agent_id || "unknown";
    if (!agentMap.has(id)) {
      agentMap.set(id, {
        id,
        total: 0,
        lastAction: event.action,
        lastTimestamp: event.timestamp ?? "",
        actionCounts: {},
        lastTs: 0
      });
    }
    const entry = agentMap.get(id);
    if (!entry) return;
    entry.total += 1;
    entry.actionCounts[event.action] = (entry.actionCounts[event.action] ?? 0) + 1;
    const ts = Date.parse(event.timestamp) || 0;
    if (ts >= entry.lastTs) {
      entry.lastTs = ts;
      entry.lastAction = event.action;
      entry.lastTimestamp = event.timestamp ?? "";
    }
    actionTotals[event.action] = (actionTotals[event.action] ?? 0) + 1;
  });

  const agentSummaries = Array.from(agentMap.values()).sort((a, b) => b.total - a.total);
  const actionSeries = Object.entries(actionTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const activeAgentCount = agentSummaries.length;
  const actionCountsForBudget = Object.keys(actionTotals).length ? actionTotals : {};
  const actionCosts = {
    ...defaultActionCosts
  };
  const budgetTotal = 500;
  const budgetUnit = "";
  const budgetUsedRaw = Object.entries(actionCountsForBudget).reduce((sum, [action, count]) => {
    const cost = actionCosts[action] ?? 1;
    return sum + cost * count;
  }, 0);
  const budgetUsed = budgetTotal ? Math.min(budgetUsedRaw, budgetTotal) : budgetUsedRaw;
  const budgetRatio = budgetTotal ? Math.min(1, budgetUsed / budgetTotal) : 0;
  const budgetLabel = budgetTotal
    ? `${formatNumber(budgetUsed)} / ${formatNumber(budgetTotal)}${budgetUnit ? ` ${budgetUnit}` : ""}`
    : `${formatNumber(budgetUsed)}${budgetUnit ? ` ${budgetUnit}` : ""}`;
  const budgetPercentLabel = budgetTotal ? `${(budgetRatio * 100).toFixed(1)}%` : "n/a";
  const metrics = simulation?.result?.metrics ?? {
    reach: activeAgentCount,
    engagement: activityEvents.length,
    conversionEstimate: 0,
    roas: 0
  };
  const confidenceLevel = simulation?.result?.confidenceLevel ?? "live";
  const statCards = [
    {
      label: "Reach",
      value: typeof metrics?.reach === "number" ? formatNumber(metrics.reach) : "—"
    },
    {
      label: "Engagement",
      value: typeof metrics?.engagement === "number" ? formatNumber(metrics.engagement) : "—"
    },
    {
      label: "Conversion est.",
      value: typeof metrics?.conversionEstimate === "number" ? formatNumber(metrics.conversionEstimate) : "—"
    },
    {
      label: "ROAS",
      value: typeof metrics?.roas === "number" ? formatNumber(metrics.roas) : "—"
    },
    {
      label: "Confidence",
      value: confidenceLevel
    }
  ];
  const latestActivity = activityEvents[0];
  const feedLabel = status === "error" ? "feed error" : status === "loading" ? "connecting" : "live";
  const activityLabel = activityStatus === "error" ? "feed error" : activityStatus === "loading" ? "connecting" : "live";
  const personaSeeds = personasData as PersonaSeed[];
  const personaByUsername = new Map(
    personaSeeds.map(persona => [persona.username.toLowerCase(), persona])
  );
  const agentPersonaById = new Map<string, string>();
  const extractPersonaFromSource = (source: string) => {
    const markerIndex = source.indexOf("__");
    if (markerIndex === -1) return null;
    return source.slice(markerIndex + 2).replace(/\.jsonl$/i, "") || null;
  };
  activityEvents.forEach(event => {
    const username = extractPersonaFromSource(event.source);
    if (username) {
      agentPersonaById.set(event.agent_id, username);
    }
  });
  const agentPersonaPairs = agentSummaries
    .map(agent => {
      const username = agentPersonaById.get(agent.id);
      if (!username) return null;
      const persona = personaByUsername.get(username.toLowerCase());
      return persona ? { agentId: agent.id, persona } : null;
    })
    .filter((entry): entry is { agentId: string; persona: PersonaSeed } => Boolean(entry));
  const sampledPersonas = personaSeeds.slice(-3);
  const latestPersona = latestActivity?.agent_id ? agentPersonaById.get(latestActivity.agent_id) ?? null : null;
  const postContext = simulation?.config.parameters?.postContext ?? "";
  const handleMatch = postContext.match(/@([a-zA-Z0-9._-]+)/);
  const influencerHandle = handleMatch ? `@${handleMatch[1]}` : "local";
  const primaryPersona = agentPersonaPairs[0]?.persona.username ?? "Swarm run";
  const influencer = {
    name: simulation?.config.targetPersona ?? primaryPersona,
    handle: influencerHandle,
    focus: simulation?.config.goal ?? "Local multi-agent activity"
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-title">
          <span className="header-eyebrow">Marketing simulation</span>
          <h1>{influencer.name}</h1>
          <p>
            {influencer.handle} · {influencer.focus}
          </p>
        </div>
        <div className="header-meta">
          <div className="meta-block">
            <span className="meta-label">Simulation</span>
            <span className="meta-value">{feedLabel}</span>
          </div>
          <div className="meta-block">
            <span className="meta-label">Updated</span>
            <span className="meta-value">
              {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "waiting"}
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="stats-section">
          <div className="section-header">
            <h2>Live overview</h2>
            <p>Real-time metrics for the running simulation.</p>
          </div>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Status</span>
              <span className="stat-value">{simulation?.status ?? (activityEvents.length ? "running" : "waiting")}</span>
              <span className="stat-note">Simulation ID: {simulation?.simulationId ?? "activity-only"}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Agents</span>
              <span className="stat-value">{activeAgentCount || simulation?.config.parameters?.agentCount || agentFiles.length}</span>
              <span className="stat-note">
                Target: {simulation?.config.parameters?.agentCount ?? agentFiles.length}
              </span>
            </div>
            {statCards.map(card => (
              <div key={card.label} className="stat-card">
                <span className="stat-label">{card.label}</span>
                <span className="stat-value">{card.value}</span>
              </div>
            ))}
          </div>
          <div className="progress-row">
            <div className="progress-meta">
              <span>Budget used (action credits)</span>
              <span>{budgetLabel}</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${budgetRatio * 100}%` }} />
            </div>
            <div className="progress-meta progress-meta--subtle">
              <span>{budgetPercentLabel} of budget</span>
              <span>{activityEvents.length ? activityEvents.length : "no"} live actions</span>
            </div>
          </div>
          <div className="activity-summary">
            <div className="activity-line">
              <span className="meta-label">Latest activity</span>
              <span className="meta-value">
                {latestActivity
                  ? `${latestActivity.agent_id}${latestPersona ? ` · ${latestPersona}` : ""} · ${latestActivity.action}`
                  : "Waiting for agent logs"}
              </span>
            </div>
            {latestActivity?.content && <p className="activity-note">{latestActivity.content}</p>}
            {typeof latestActivity?.metadata?.screenshot === "string" && (
              <div className="activity-screenshot" style={{ marginTop: "1rem" }}>
                <img
                  src={latestActivity.metadata.screenshot}
                  alt="Agent view"
                  style={{
                    maxWidth: "100%",
                    borderRadius: "0.5rem",
                    border: "1px solid rgba(255,255,255,0.1)"
                  }}
                />
              </div>
            )}
            <div className="activity-meta">
              <span className="meta-label">Activity feed</span>
              <span className="meta-value">{activityLabel}</span>
              <span className="meta-label">Updated</span>
              <span className="meta-value">
                {activityUpdated ? new Date(activityUpdated).toLocaleTimeString() : "waiting"}
              </span>
              <span className="meta-label">Sources</span>
              <span className="meta-value">{agentFiles.length}</span>
            </div>
            <p className="activity-footnote">Source: /simulation/{simulationId}.json</p>
          </div>
        </section>

        <section className="agents-section">
          <div className="section-header">
            <h2>Multi-agent activity map</h2>
            <p>Live activity summarized across each agent stream.</p>
          </div>
          <div className="agents-layout">
            <div className="action-mix">
              <div className="action-mix-header">
                <span className="meta-label">Action mix</span>
                <span className="meta-value">{activityEvents.length} events</span>
              </div>
              {actionSeries.length ? (
                <div className="action-bars">
                  {actionSeries.map(([action, count]) => (
                    <div key={action} className="action-row">
                      <span className="action-label">{action}</span>
                      <div className="action-bar">
                        <div
                          className="action-fill"
                          style={{
                            width: `${Math.max(6, Math.round((count / activityEvents.length) * 100))}%`
                          }}
                        />
                      </div>
                      <span className="action-count">{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-note">Waiting for agent logs.</p>
              )}
            </div>

            <div className="agent-grid">
              {agentSummaries.length ? (
                agentSummaries.map(agent => (
                  <div key={agent.id} className="agent-card">
                    <div className="agent-header">
                      <strong>
                        {agent.id}
                        {agentPersonaById.has(agent.id) ? ` · ${agentPersonaById.get(agent.id)}` : ""}
                      </strong>
                      <span className="agent-total">{agent.total} actions</span>
                    </div>
                    <div className="agent-last">
                      <span className="meta-label">Last</span>
                      <span className="meta-value">
                        {agent.lastAction}
                        {agent.lastTimestamp && ` · ${new Date(agent.lastTimestamp).toLocaleTimeString()}`}
                      </span>
                    </div>
                    <div className="agent-actions">
                      {Object.entries(agent.actionCounts)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(([action, count]) => (
                          <div key={action} className="agent-action">
                            <span>{action}</span>
                            <span>{count}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-card">No active agent logs yet.</div>
              )}
            </div>
          </div>
        </section>

        <section className="persona-section">
          <div className="section-header">
            <h2>User personas</h2>
            <p>Sampled personas from the seed list.</p>
          </div>
          <div className="persona-grid">
            {sampledPersonas.map(persona => (
              <div key={persona.username} className="persona-card">
                <div className="persona-header">
                  <div>
                    <strong>{persona.username}</strong>
                    <span className="persona-id">{persona.occupation}</span>
                  </div>
                  <span className="persona-tone">{persona.communication_style}</span>
                </div>
                <p className="persona-description">
                  {persona.age_range} · {persona.location} · {persona.engagement_level} engagement
                </p>
                <p className="persona-description">
                  Traits: {persona.personality_traits.slice(0, 3).join(", ")}
                </p>
                <p className="persona-description">
                  Interests: {persona.interests.slice(0, 3).join(", ")}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
