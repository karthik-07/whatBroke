# Pacman scenarios

All records are synthetic.

- `transactions.log`: five package events covering each supported action; four
  unrelated records. Observed bounds: February 1–7, 2026, at 08:00 UTC.
- `malformed.log`: two valid package events and four malformed records. Parsing
  must continue through the final removal and report partial status.

Other edge cases are generated in temporary files by the tests.
