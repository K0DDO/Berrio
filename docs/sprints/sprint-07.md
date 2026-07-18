# Sprint 7 — Bank email parsers

## Delivered

- Pluggable parsers: tinkoff, sber (+ alfa/vtb placeholders)
- `bank_connections`, `transactions` (`0006_banks`)
- `POST /banks/connections`, `GET /banks/connections`
- `POST /banks/parse-email` — ingest without IMAP
- `GET /banks/transactions`

## Not yet

Real IMAP mailbox sync (needs credentials + worker). Architecture ready via `BankParser` protocol.
