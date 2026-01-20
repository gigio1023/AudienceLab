import { AgentActivityEvent, RawActivityRecord } from "@/types/activity";

export const ActivityInterface = {
    normalize(
        record: RawActivityRecord,
        source: string,
        fallbackId: string
    ): AgentActivityEvent {
        // Parse fields from record
        // Expected record keys: timestamp, agentId, decision, result, etc.

        const agentId = (record.agentId as string) || "unknown";
        const timestamp = (record.timestamp as string) || new Date().toISOString();

        // Decision block has main info
        const decision = (record.decision as Record<string, unknown>) || {};
        const result = (record.result as Record<string, unknown>) || {};

        const action = (decision.action as string) || (result.action as string) || "unknown";
        const target = (decision.target as string) || (result.target as string) || null;

        // Content can be comment_text
        const content = (decision.comment_text as string) || (result.comment as string) || null;

        // Metadata can hold reasoning, screenshot, etc.
        const metadata: Record<string, unknown> = {
            reasoning: decision.reasoning || result.reasoning,
            status: record.status,
            step: record.step,
            screenshot: record.screenshot || result.screenshot
        };

        return {
            id: fallbackId, // Or generate unique id
            agent_id: agentId,
            action,
            timestamp,
            source,
            target,
            content,
            metadata
        };
    }
};
