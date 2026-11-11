# Client timing clarification — 11 November 2026

The November 8 checkpoint remains pinned and unchanged at `client-checkpoint-20261108`.
This note records the timing distinction requested in the latest source review.

## Exact timing scope

- The exclusive process lock is acquired before saved state and its deadline are loaded or
  created. Time waiting for that lock is outside the request deadline.
- The persisted five-minute request deadline begins when new state is created after lock
  acquisition.
- Token admission, request dispatch and response-body reading are checked against that
  persisted deadline.
- If the request/body child is still active at the deadline, termination uses one join of up to
  two seconds, followed when needed by a kill and second join of up to two seconds.
- Cleanup can therefore add up to four seconds after the request deadline.
- Post-response parsing, validation, evidence writes and report writes are outside the
  five-minute request deadline.
- The report does not describe this as a strict whole-process five-minute limit.

## Execution status

- Listing diagnostic remains on hold pending the client's separate decision.
- Provider requests: 0.
- Provider credits used: 0.
- Azure runs: 0.
- Pending pages: 780.
- Retryable failures: 216.
- Unresolved paths: 18.

No completion or live listing-route claim is made.
