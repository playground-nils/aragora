'use client';

import Link from 'next/link';
import { useTheme } from '@/context/ThemeContext';
import { Header } from '@/components/landing/Header';
import { Footer } from '@/components/landing/Footer';
import { ConnectOpenRouterButton } from '@/components/openrouter/ConnectOpenRouterButton';

function CodeBlock({
  children,
  lang,
}: {
  children: string;
  lang?: string;
}) {
  return (
    <div className="relative group rounded-lg overflow-hidden border border-[var(--border)]">
      {lang && (
        <div className="flex items-center justify-between px-4 py-2 bg-[var(--surface-elevated)] border-b border-[var(--border)]">
          <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
            {lang}
          </span>
        </div>
      )}
      <pre className="p-4 bg-[var(--surface)] overflow-x-auto text-[13px] font-mono text-[var(--text)] leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function Step({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)]/30 p-6 md:p-8">
      <div className="flex items-center gap-3 mb-5">
        <span className="flex items-center justify-center w-9 h-9 text-sm font-semibold rounded-full bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/25">
          {number}
        </span>
        <h2 className="text-xl font-semibold text-[var(--text)]">
          {title}
        </h2>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

export default function QuickstartPage() {
  const { theme } = useTheme();

  return (
    <div
      className="min-h-screen"
      style={{
        backgroundColor: 'var(--bg)',
        color: 'var(--text)',
      }}
      data-landing-theme={theme}
    >
      <Header />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        {/* Title */}
        <div className="text-center mb-14">
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--accent)] mb-3">
            Quickstart
          </h1>
          <p className="text-[var(--text-muted)] text-lg">
            Get from zero to a working adversarial debate in under a minute.
          </p>
        </div>

        <div className="space-y-8">
          {/* Step 1 */}
          <Step number={1} title="Install">
            <CodeBlock lang="bash">pip install aragora-debate</CodeBlock>
          </Step>

          {/* Step 2 */}
          <Step number={2} title="Zero-Key Demo">
            <p className="text-[var(--text-muted)]">
              No API keys needed — runs with styled mock agents locally:
            </p>
            <CodeBlock lang="python">{`from aragora_debate.arena import Arena
from aragora_debate.styled_mock import StyledMockAgent
import asyncio

agents = [
    StyledMockAgent('analyst', style='supportive'),
    StyledMockAgent('critic', style='critical'),
    StyledMockAgent('pm', style='balanced'),
]
arena = Arena(question='Should we migrate to microservices?', agents=agents)
result = asyncio.run(arena.run())
print(result.receipt.to_markdown())`}</CodeBlock>
            <p className="text-[var(--text-muted)] text-sm">
              Three agents debate, critique each other, vote, and produce an
              audit-ready decision receipt.
            </p>
          </Step>

          {/* Step 3 */}
          <Step number={3} title="Add Real AI Models">
            <div className="rounded-lg border border-[var(--accent)]/20 bg-[var(--accent)]/5 p-4 flex items-center justify-between">
              <div>
                <p className="font-semibold text-[var(--text)]">One-click setup via OpenRouter</p>
                <p className="text-sm text-[var(--text-muted)]">Connect your account and set a budget — no key pasting needed.</p>
              </div>
              <ConnectOpenRouterButton />
            </div>
            <p className="text-[var(--text-muted)]">
              Or set API keys manually:
            </p>
            <CodeBlock lang="bash">{`export ANTHROPIC_API_KEY="sk-ant-..."   # Claude
# or
export OPENAI_API_KEY="sk-..."          # GPT`}</CodeBlock>
            <p className="text-[var(--text-muted)]">
              Then run a real multi-model debate:
            </p>
            <CodeBlock lang="python">{`import asyncio
from aragora import Arena, Environment, DebateProtocol

env = Environment(task="Design a rate limiter for our API")
protocol = DebateProtocol(rounds=3, consensus="majority")

# Arena auto-discovers available agents from your API keys
arena = Arena(env, protocol=protocol)
result = asyncio.run(arena.run())
print(result.summary)`}</CodeBlock>
          </Step>

          {/* Step 4 */}
          <Step number={4} title="TypeScript SDK">
            <CodeBlock lang="bash">npm install @aragora/sdk</CodeBlock>
            <CodeBlock lang="typescript">{`import { AragoraClient } from "@aragora/sdk";

const client = new AragoraClient({ baseUrl: "http://localhost:8080" });
const result = await client.debates.create({
  task: "Should we use microservices or a monolith?",
  agents: ["claude", "openai"],
  rounds: 3,
});
console.log(result.summary);`}</CodeBlock>
          </Step>

          {/* Step 5 */}
          <Step number={5} title="Self-Host">
            <CodeBlock lang="bash">
              docker compose -f deploy/demo/docker-compose.yml up
            </CodeBlock>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { label: 'Landing page', url: 'localhost:3000' },
                { label: 'API docs', url: 'localhost:8080/api/v2/docs' },
                { label: 'Playground', url: 'localhost:3000/playground' },
                { label: 'CLI', url: 'aragora debate "your question"' },
              ].map((item) => (
                <div
                  key={item.label}
                  className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface)]"
                >
                  <span className="text-sm font-semibold text-[var(--accent)]">
                    {item.label}
                  </span>
                  <span className="text-sm text-[var(--text-muted)] ml-2 font-mono">
                    {item.url}
                  </span>
                </div>
              ))}
            </div>
          </Step>
        </div>

        {/* Next Steps */}
        <div className="mt-14">
          <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-5">
            Next Steps
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Link
              href="/try"
              className="p-5 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/5 hover:bg-[var(--accent)]/10 transition-colors"
            >
              <span className="text-base font-semibold text-[var(--accent)]">
                Try a debate now
              </span>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                No install needed — run in your browser
              </p>
            </Link>
            <Link
              href="/docs"
              className="p-5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)]/30 transition-colors"
            >
              <span className="text-base font-semibold text-[var(--text)]">
                API Reference
              </span>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                Full REST API documentation
              </p>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
