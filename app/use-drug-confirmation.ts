'use client';

import { useEffect, useState } from 'react';

export type DrugCandidate = {
  drug_id: string;
  drug_name: string;
  dosage_form: string;
  specification: string;
  manufacturer: string;
};

type StreamPayload = {
  session_id?: string;
  message?: string;
  question?: string;
  delta?: string;
  evidence?: string[];
  candidates?: DrugCandidate[];
  drug?: DrugCandidate | null;
};

type SessionSnapshot = {
  session_id: string;
  confirmed_drug?: DrugCandidate | null;
  pending_candidates: DrugCandidate[];
  turns: Array<{
    question: string;
    answer: string;
    evidence: string[];
  }>;
};

const SESSION_KEY = 'medquery.session_id';

export function useDrugConfirmation() {
  const [sessionId, setSessionId] = useState<string>();
  const [candidates, setCandidates] = useState<DrugCandidate[]>([]);
  const [confirmedDrug, setConfirmedDrug] = useState<DrugCandidate>();
  const [clarification, setClarification] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [evidence, setEvidence] = useState<string[]>([]);

  useEffect(() => {
    const storedSessionId = window.localStorage.getItem(SESSION_KEY);
    if (!storedSessionId) return;

    fetch(`/api/sessions/${storedSessionId}`).then(async (response) => {
      if (!response.ok) {
        window.localStorage.removeItem(SESSION_KEY);
        return;
      }
      const snapshot = (await response.json()) as SessionSnapshot;
      setSessionId(snapshot.session_id);
      setConfirmedDrug(snapshot.confirmed_drug ?? undefined);
      setCandidates(snapshot.pending_candidates ?? []);
      const latest = snapshot.turns.at(-1);
      if (latest) {
        setAnswer(latest.answer);
        setEvidence(latest.evidence);
      }
    });
  }, []);

  async function submitQuestion(message: string, resume = false) {
    if (!message || (isSending && !resume)) return;
    setIsSending(true);
    setClarification('');
    if (!resume) {
      setPendingQuestion(message);
      setAnswer('');
      setEvidence([]);
    }
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, resume }),
    });
    await consumeSse(response, handleStreamEvent);
    setIsSending(false);
  }

  function handleStreamEvent(event: string, payload: StreamPayload) {
    if (event === 'session' && payload.session_id) {
      setSessionId(payload.session_id);
      window.localStorage.setItem(SESSION_KEY, payload.session_id);
    }
    if (event === 'drug_confirmation_required') {
      setCandidates(payload.candidates ?? []);
    }
    if (event === 'drug_clarification_required') {
      setCandidates([]);
      setClarification(payload.message ?? '请补充要查询的药品名称。');
    }
    if (event === 'drug_confirmed' && payload.drug) {
      setConfirmedDrug(payload.drug);
      setCandidates([]);
    }
    if (event === 'answer_delta' && payload.delta) {
      setAnswer((current) => current + payload.delta);
    }
    if (event === 'evidence') {
      setEvidence(payload.evidence ?? []);
    }
  }

  async function decideCandidate(candidate: DrugCandidate, accepted: boolean) {
    if (!sessionId || isSending) return;
    setIsSending(true);
    const response = await fetch(
      `/api/sessions/${sessionId}/drug-confirmation`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drug_id: candidate.drug_id, accepted }),
      },
    );
    const payload = (await response.json()) as StreamPayload & {
      status: string;
    };
    if (payload.status === 'confirmed' && payload.drug) {
      setConfirmedDrug(payload.drug);
      setCandidates([]);
      setClarification('');
      await submitQuestion(payload.question ?? pendingQuestion, true);
      return;
    }
    setCandidates(payload.candidates ?? []);
    setClarification(payload.message ?? '请补充药品名称。');
    setIsSending(false);
  }

  return {
    answer,
    candidates,
    clarification,
    confirmedDrug,
    decideCandidate,
    evidence,
    isSending,
    submitQuestion,
  };
}

async function consumeSse(
  response: Response,
  onEvent: (event: string, payload: StreamPayload) => void,
) {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      emitSseBlock(block, onEvent);
      boundary = buffer.indexOf('\n\n');
    }
    if (done) break;
  }
}

function emitSseBlock(
  block: string,
  onEvent: (event: string, payload: StreamPayload) => void,
) {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    if (line.startsWith('data:')) data.push(line.slice(5).trim());
  }
  if (data.length) onEvent(event, JSON.parse(data.join('\n')));
}
