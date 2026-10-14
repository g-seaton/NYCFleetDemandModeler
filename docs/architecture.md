# Architecture notes

## Separation of concerns

The repository deliberately separates four stateful objects:

1. **observations**: trip records and realized OD flows,
2. **features/predictions**: the DS layer,
3. **fleet state**: vehicles available by zone,
4. **decisions**: repositioning moves returned by the optimizer.

This prevents a common portfolio mistake where model training, optimization, and simulation are mixed together in one notebook.

## Production-shaped data model

Suggested PostgreSQL schemas:

- `raw`: immutable landed source records,
- `staging`: cleaned and typed views,
- `analytics`: demand marts and model-ready features,
- `decision`: forecasts, fleet snapshots, optimization runs, recommended moves.

## Observability

For a production extension, log for each optimization run:

- forecast version,
- solver/version,
- parameter configuration,
- runtime,
- objective value,
- model status,
- number of repositioning moves,
- predicted uncovered demand.

These fields make optimization decisions auditable and reproducible.
