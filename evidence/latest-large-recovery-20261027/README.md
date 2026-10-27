# Latest-version 132-product recovery test

Live test using source commit `e6306ff54a2c234d98b20abe50b15e68dc728fec`.

- Store 100, ZIP 72712, PICKUP
- 132 accepted products: 12 from each of 11 required categories
- process ended with SIGKILL after 30 committed products
- same code and settings resumed the checkpoint
- interrupted product retried and completed once
- all prior committed products retained
- SQLite integrity passed
- zero duplicate product IDs
- two wrong-store responses rejected and excluded
- final sample validation passed

This is larger latest-version recovery evidence. It is not full category coverage.
Files exclude cookies, browser profiles, session secrets, and full HTML.
