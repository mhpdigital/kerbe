# Validation: kerbe:coverage vs the retired suite — subscription slice, 2026-08-20

Blind A/B on the same code state (`slice/subscription@9eef0067`): kerbe:coverage 0.1.1
(274 promises, 239 present, 36 open, extraction capped at 5 passes) vs the retired suite's
final loop (36 findings, not converged). The new run never read the prior report; a
separate agent mapped the two afterwards.

## Result

- **Reproduced (10 old ↔ 19 new rows):** including the churned-trial money-path blocker,
  the per-state plan-card family, the referred-friends list. The new run splits per leaf,
  which is why 10 findings map to 19 rows.
- **New-only (17):** the gifted/VIP state family (5 rows — the old loop's biggest blind
  spot), NZD-vs-`|usd` at 7 sites, gifted rows never expiring, the undeleted admin page,
  the reconcile conflict class never emitted, mobile tab bar, cutover preconditions.
- **Old-only, correctly excluded (8):** 7 fail the missing-functionality admission test
  (doc drift, process artifacts) and 1 the new run verified present with defensible
  evidence.
- **Old-only, genuine recall gaps (17, incl. 4–5 blockers):** success-CTA-403s, un-cancel
  deadlock, card-never-attached, Free-plan order summary, Payment-Element-cannot-mount,
  plus all CSS-fidelity findings.

## The one failure mode behind every recall gap

**The verify recipes check static presence and wiring; they never follow the promise one
hop into behaviour.** Every missed blocker is still statically checkable:

1. **Evidence locality:** several `present` verdicts cited evidence that is not in the
   artifact the promise names (grid code cited for a checkout screen). Rule needed: the
   evidence for a promise on screen X must live in X's template/controller chain.
2. **Action-chain hop:** a promised action must be followed one hop — the route a CTA
   links must exist AND be reachable by the promised audience (security config), and act
   on the promised object/state (a cancel that produces a state the reactivate guard
   rejects is `partial`).
3. **State-machine promises:** "member can un-cancel" is a promise about a transition;
   verify the transition's precondition is producible, not that a method named reactivate
   exists.
4. **Visual fidelity is out of scope by design** — but must be SAID: the report should
   carry a standing "not checked: visual fidelity vs design" line so absence of CSS
   findings is never read as CSS being fine.
5. **P-079 conflict:** the new run's shallow read contradicted the old run's deeper proof
   on the same commit — spot-audits must re-derive, not re-cite.

## Actions

- [ ] Harden `adapters/stack/*/verify.md` + SKILL.md verify phase with rules 1–3 (recipe
      classes: evidence-locality, action-chain, state-transition), add rule 4's standing
      disclaimer to the verdict summary, and rule 5 to the quality pass.
- [ ] Grow both fixtures with planted defects of the new classes (a CTA linking a
      role-gated route; a state transition whose guard rejects its own product) so the
      gate covers them.
- [ ] Re-run the subscription audit on the hardened skill; expect the four missed blockers
      to surface as rows.

Working fix list for the slice itself (both runs' findings merged):
`<planning-repo>/planning/slices/subscription/GAP_FIXES.md`.
