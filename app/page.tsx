'use client';

import { FormEvent, useState } from 'react';
import { ArrowUp, Pill, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

const sampleQuestions = [
  '布洛芬缓释胶囊一天吃几次？',
  '二甲双胍需要随餐服用吗？',
  '阿莫西林有哪些禁忌？',
  '华法林与其他药物同服要注意什么？',
];

const evidence = [
  '口服，成人及12岁以上儿童一日2次，早、晚各1次；一次0.3～0.6g，或遵医嘱。',
  '本品必须整粒吞服，不得打开、压碎或溶解后服用。',
  '用于止痛不得超过5天，用于解热不得超过3天；症状不缓解时请咨询医师或药师。',
];

export default function Home() {
  const [question, setQuestion] = useState('');
  const [submittedQuestion, setSubmittedQuestion] = useState('');

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (!nextQuestion) return;
    setSubmittedQuestion(nextQuestion);
  }

  return (
    <main className="app-shell">
      <div className="ambient-scene" aria-hidden="true">
        <div className="ambient-grid" />
        <div className="aurora aurora-one" />
        <div className="aurora aurora-two" />
        <div className="aurora aurora-three" />
        <div className="light-beam light-beam-one" />
        <div className="light-beam light-beam-two" />
      </div>

      <header className="brand-bar">
        <div className="brand-lockup">
          <span className="brand-symbol" aria-hidden="true">
            <Pill />
          </span>
          <span className="brand-name">智药问点</span>
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-description">药品说明书问答系统</span>
          <span className="demo-mark">Demo</span>
        </div>
      </header>

      <section className="hero-section">
        <div className="intelligence-mark" aria-hidden="true">
          <span className="orbit orbit-outer" />
          <span className="orbit orbit-inner" />
          <span className="intelligence-core">
            <Sparkles />
          </span>
        </div>

        <div className="hero-copy">
          <h1>
            从说明书中，
            <span>找到明确答案。</span>
          </h1>
          <p>输入药品名称和你的问题，快速查找说明书中的相关信息。</p>
        </div>

        <form className="question-panel" onSubmit={submitQuestion}>
          <Textarea
            aria-label="输入药品说明书问题"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：布洛芬缓释胶囊一天吃几次？"
            className="question-input"
            rows={2}
          />
          <div className="question-footer">
            <span className="input-hint">输入药品名称，开始提问</span>
            <Button
              type="submit"
              size="icon-lg"
              aria-label="发送问题"
              className="send-button"
              disabled={!question.trim()}
            >
              <ArrowUp />
            </Button>
          </div>
        </form>

        <div className="suggestion-list" aria-label="示例问题">
          {sampleQuestions.map((item) => (
            <button
              type="button"
              key={item}
              className="suggestion-chip"
              onClick={() => setQuestion(item)}
            >
              {item}
            </button>
          ))}
        </div>

        {submittedQuestion ? (
          <section className="result-preview" aria-live="polite">
            <p className="result-question">{submittedQuestion}</p>
            <div className="answer-panel">
              <p>
                说明书信息显示，成人及 12 岁以上儿童通常每日服用 2 次，早晚各一次。服用时应整粒吞服，具体剂量请以所持药品说明书为准。
              </p>
            </div>
            <div className="evidence-grid">
              {evidence.map((item, index) => (
                <article className="evidence-card" key={item}>
                  <span className="evidence-index">0{index + 1}</span>
                  <p>{item}</p>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
