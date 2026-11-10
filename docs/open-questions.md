# Open questions for SAS

These are decisions the team can't make alone. Until SAS answers, the team's **assumption** is used, and it's marked as such in code and config.

| # | Question | Why it matters | Current assumption (team) | Status |
|---|----------|----------------|---------------------------|--------|
| Q1 | Which metrics are in scope for the single-camera version? | Decides what to build in Iterations 2–3 | Shoulder tilt, tempo, stroke length ratio, head movement (stretch) | Open |
| Q2 | How does Parspective define each metric exactly (reference points, sign conventions, phase boundaries)? | Our numbers are only comparable if the definitions match | Our own provisional definitions, documented in [metrics.md](metrics.md) | Open (spike SP 01) |
| Q3 | How do you define the stroke events (takeaway, top, impact, finish)? Is impact the ball-contact frame or the return to address? | Tempo depends directly on these | Impact = hands return to the address position (no ball/putter tracking yet) | Open |
| Q4 | What accuracy tolerance per metric counts as "matches Parspective"? | Pass/fail criterion for SP 02 | Tilt ±2°, tempo ratio ±0.2, stroke length ratio ±0.15 (placeholders) | Open |
| Q5 | How should the combined score (US 04) be weighted, and what are the target values? | The current score is a placeholder | Equal-ish weights; targets: tempo 2.0, tilt change 0°, length ratio 1.0 | Open |
| Q6 | Can we get sample videos with Parspective reference outputs? | Needed for SP 02 | None available yet; synthetic tests only | Open |
| Q7 | Data retention policy for videos/results/emails at events? | Privacy and legal | Delete after 24 h (configurable); emails are never stored, only used to send | Open |
| Q8 | Target devices and OS versions? Will SAS provide demo phones? | Native vs. web, camera capability | Recent iOS/Android phones plus a web fallback | Open |
| Q9 | Which email sender/domain should results come from at the expo? | SMTP setup | Console backend only (no real email sent) until SAS provides SMTP | Open |
| Q10 | Is face-on the preferred single-camera view? Would down-the-line also be useful? | Down-the-line suits putter path; face-on suits tilt/tempo | Face-on only for Iteration 1 | Open |
| Q11 | Is real putter-head tracking expected later? | The hand-midpoint proxy has limits | Proxy for now; putter tracking is future work | Open |
