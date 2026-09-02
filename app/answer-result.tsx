'use client';


export function AnswerResult({
  answer,
  evidence,
}: {
  answer: string;
  evidence: string[];
}) {
  if (!answer && !evidence.length) return null;

  return (
    <section className="result-preview" aria-live="polite">
      {answer ? (
        <div className="answer-panel">
          <p>{answer}</p>
        </div>
      ) : null}
      {evidence.length ? (
        <div className="evidence-grid">
          {evidence.map((item, index) => (
            <article className="evidence-card" key={`${index}-${item}`}>
              <p>{item}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
