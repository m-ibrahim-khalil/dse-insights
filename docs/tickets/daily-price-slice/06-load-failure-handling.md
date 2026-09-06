# 06 — Load failure handling and a row-count guard

**What to build:** A load that survives bad input and refuses suspicious input.
One malformed landed file must not cost the operator the rest of a week's
recovery, and a truncated response must be caught before it reaches the warehouse
rather than discovered later as a hole in a chart.

The row-count guard matters because of how the source fails: a truncated response
is still valid HTML and still parses. It produces a Trading Day with too few
Instruments, which no schema assertion rejects.

**Blocked by:** 05 — Idempotent loading over a range of Trading Days

**Status:** ready-for-agent

- [ ] A malformed landed file fails loudly for that file alone, and the rest of
      the range continues
- [ ] Every failure names the file and the reason, and the command's exit status
      reflects that something failed
- [ ] A Trading Day whose row count is implausibly low against recent Trading
      Days is refused before anything is written
- [ ] The threshold is derived from observed history, not a hardcoded constant
- [ ] The guard can be explicitly overridden for a Trading Day known to be
      genuinely short
- [ ] Rows read and rows written are reported per Trading Day, so a partial load
      is visible rather than silent
- [ ] A test asserts a corrupt fixture does not prevent its neighbours loading
