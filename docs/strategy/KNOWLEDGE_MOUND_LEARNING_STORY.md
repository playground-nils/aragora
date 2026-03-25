# Knowledge Mound Learning Story

This is the commercial explanation of what Aragora means when it says the
platform "learns."

## One-Line Version

Knowledge Mound turns vetted work into reusable organizational memory. It is
not a license to treat every model output as truth.

## Founder Language

The founder story is compounding judgment.

Every time Aragora produces a good receipt, the system should get better at the
next similar decision. That learning does not come from vague "AI magic." It
comes from storing the parts of prior work that are actually worth reusing:

- the decision outcome
- the evidence behind it
- the dissent around it
- the pattern of how it was resolved

That gives Aragora a real memory moat. The product does not just run another
debate; it starts the next debate with better precedent, better context, and a
clearer picture of what this organization has already learned.

## Buyer Language

The buyer story is governed institutional memory.

Knowledge Mound is where Aragora stores high-signal knowledge with provenance,
confidence, and access controls. It lets teams reuse prior decisions without
flattening everything into an unreviewable blob of AI output.

For a buyer, the value is straightforward:

- repeated decisions get faster
- similar cases get more consistent
- auditors can see where knowledge came from
- stale or conflicting knowledge can be challenged instead of silently reused

## What Gets Learned

Aragora learns the parts of work that are strong enough to be reused later.

- High-confidence debate outcomes can be written back into the Knowledge Mound.
  The current write path skips low-confidence outcomes and only writes debate
  outcomes to the mound when confidence is at least `0.7`.
- Knowledge is stored as claims, facts, insights, and references with
  provenance, rather than as an opaque summary.
- Cross-debate patterns are accumulated over time, including decision style,
  risk tolerance, domain expertise, debate dynamics, and resolution patterns.
- Contradiction signals, freshness signals, and validation activity are also
  learned so retrieval quality improves over time instead of freezing the first
  answer forever.

## What Does Not Get Learned

The critical commercial boundary is that Aragora does not silently canonize weak
or unresolved outputs.

- Low-confidence debate outcomes do not get promoted into shared memory through
  the normal writeback path.
- Unresolved disagreement is not treated as settled policy. It remains dissent,
  contradiction, or a review task.
- Superseded knowledge is not treated as evergreen truth. Older items can decay
  in confidence and be marked stale when contradicted or left unvalidated.
- Sensitive cost telemetry is not included unless the opt-in cost adapter is
  enabled.
- Manual knowledge still sits at the top of the authority hierarchy, which means
  automated retrieval does not outrank explicit user-provided knowledge.

## What Must Be Reviewed

The review story matters as much as the learning story.

- Contradictions between new knowledge and existing knowledge must be resolved
  before teams treat the newer claim as settled operating truth.
- Important claims should be reviewed before promotion into verified or
  policy-like knowledge tiers.
- Any receipt showing low confidence, meaningful dissent, or high-risk side
  effects should stay on a human review path.
- Irreversible actions should remain receipt-gated. Knowledge Mound can improve
  the recommendation, but it should not erase the review boundary.

## Simple Talk Track

If someone asks, "What exactly is Aragora learning?" the short answer is:

Aragora learns reusable organizational knowledge from high-confidence,
provenance-backed work. It does not learn by blindly trusting every output, and
it keeps contradictions and consequential actions on an explicit review path.
