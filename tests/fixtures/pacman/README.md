# Pacman scenarios

All records are synthetic.

- `transactions.log`: five package events covering each supported action; four
  unrelated records. Observed bounds: February 1–7, 2026, at 08:00 UTC.
- `malformed.log`: two valid package events and four malformed records. Parsing
  must continue through the final removal and report partial status.

Other edge cases are generated in temporary files by the tests.

- `correlation.log`: synthetic changes on January 1, 2026, before, at, inside,
  and after a 01:00–02:00 UTC comparison window. Only the 01:30 linux upgrade
  is a strictly preceding candidate inside that window.
