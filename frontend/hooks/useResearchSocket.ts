'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { WsProgressEvent, AgentStatus } from '@/types/research';
import { AGENTS } from '@/types/research';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface ResearchSocketState {
  isConnected: boolean;
  progress: number;
  costSoFar: number;
  events: WsProgressEvent[];
  agentStatuses: AgentStatus[];
  isComplete: boolean;
  isError: boolean;
  reportId: string | null;
  currentAgent: string | null;
}

export function useResearchSocket(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<NodeJS.Timeout | null>(null);

  const [state, setState] = useState<ResearchSocketState>({
    isConnected: false,
    progress: 0,
    costSoFar: 0,
    events: [],
    agentStatuses: AGENTS.map(a => ({ ...a })),
    isComplete: false,
    isError: false,
    reportId: null,
    currentAgent: null,
  });

  const updateAgentStatus = useCallback(
    (agentName: string, status: AgentStatus['status'], message?: string) => {
      setState(prev => ({
        ...prev,
        agentStatuses: prev.agentStatuses.map(a =>
          a.name === agentName
            ? {
                ...a,
                status,
                message,
                startedAt: status === 'running' ? new Date().toISOString() : a.startedAt,
                completedAt:
                  status === 'complete' || status === 'error'
                    ? new Date().toISOString()
                    : a.completedAt,
              }
            : a
        ),
      }));
    },
    []
  );

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(prev => ({ ...prev, isConnected: true }));
      // Start ping interval
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = (evt) => {
      try {
        const event: WsProgressEvent = JSON.parse(evt.data);

        if (event.event === 'pong') {
          return;
        }

        setState(prev => {
          const newState = {
            ...prev,
            progress: event.progress ?? prev.progress,
            costSoFar: event.cost_so_far ?? prev.costSoFar,
            events: [...prev.events, event].slice(-100),
            currentAgent: event.agent ?? prev.currentAgent,
          };

          if (event.event === 'report_ready') {
            newState.isComplete = true;
            newState.progress = 100;
            newState.reportId = (event.data?.report_id as string) ?? prev.reportId;
          }

          if (event.event === 'agent_error' && !event.agent) {
            newState.isError = true;
          }

          return newState;
        });

        // Update agent statuses
        if (event.agent) {
          if (event.event === 'agent_start') {
            updateAgentStatus(event.agent, 'running', event.message);
          } else if (event.event === 'agent_complete') {
            updateAgentStatus(event.agent, 'complete', event.message);
          } else if (event.event === 'agent_error') {
            updateAgentStatus(event.agent, 'error', event.message);
          }
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onerror = () => {
      setState(prev => ({ ...prev, isConnected: false }));
    };

    ws.onclose = () => {
      setState(prev => ({ ...prev, isConnected: false }));
      if (pingRef.current) clearInterval(pingRef.current);
    };

    return () => {
      if (pingRef.current) clearInterval(pingRef.current);
      ws.close();
    };
  }, [jobId, updateAgentStatus]);

  return state;
}
