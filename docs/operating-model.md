# operating model

The user owns product intent, priorities, and approvals. The build agent owns execution pressure: research, implementation, tests, debugging, documentation, and surfacing tradeoffs.

## agent behavior

- make reversible implementation decisions without blocking on small questions
- keep the user at architecture / product-review level
- surface only decisions that materially change scope, cost, privacy, or the product thesis
- prefer a working vertical slice over broad scaffolding
- verify generated code before presenting it
- keep commits small and tied to one concrete change
- document real failures and pivots instead of cleaning the history into a fake straight line

## code style

- straightforward control flow over abstraction for its own sake
- short functions with explicit inputs / outputs
- single quotes in TypeScript / JavaScript
- semicolons in TypeScript / JavaScript
- small comments only when they explain a non-obvious decision
- comments should be short and lower-case
- descriptive but not enterprise-heavy names
- no decorative generated-doc comments

## public writing style

- concise and technical
- explain the problem before listing technologies
- avoid AI buzzwords when a concrete mechanism is available
- state limitations directly
- do not claim production scale or user impact before it exists
