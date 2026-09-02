'use client';

import { Check, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { DrugCandidate } from '@/app/use-drug-confirmation';


export function ConfirmedDrugBadge({ drug }: { drug?: DrugCandidate }) {
  if (!drug) return null;
  return (
    <div className="confirmed-drug" aria-live="polite">
      <Check aria-hidden="true" />
      <span>{drug.drug_name}</span>
    </div>
  );
}


export function DrugCandidatePanel({
  candidates,
  clarification,
  disabled,
  onDecision,
}: {
  candidates: DrugCandidate[];
  clarification: string;
  disabled: boolean;
  onDecision: (candidate: DrugCandidate, accepted: boolean) => void;
}) {
  if (!candidates.length) {
    return clarification ? (
      <p className="clarification-message" aria-live="polite">
        {clarification}
      </p>
    ) : null;
  }

  return (
    <section className="drug-confirmation" aria-live="polite">
      <h2>请确认药品</h2>
      <div className="drug-candidate-list">
        {candidates.map((candidate) => (
          <article className="drug-candidate" key={candidate.drug_id}>
            <div>
              <h3>{candidate.drug_name}</h3>
              <p>
                {candidate.dosage_form} · {candidate.specification}
              </p>
              <p>{candidate.manufacturer}</p>
            </div>
            <div className="candidate-actions">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`排除${candidate.drug_name}`}
                disabled={disabled}
                onClick={() => onDecision(candidate, false)}
              >
                <X />
              </Button>
              <Button
                type="button"
                className="confirm-button"
                disabled={disabled}
                onClick={() => onDecision(candidate, true)}
              >
                确认
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
