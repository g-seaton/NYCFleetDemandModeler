# Mathematical formulation

## Sets

- \(Z\): service zones
- \(A \subseteq Z \times Z\): feasible repositioning arcs

## Parameters

- \(v_i\): available vehicles in zone \(i\)
- \(d_j\): forecast pickup demand in zone \(j\)
- \(c_{ij}\): travel minutes from \(i\) to \(j\)
- \(\lambda_r\): cost per reposition vehicle-minute
- \(\lambda_u\): penalty for one unit of uncovered demand

## Variables

- \(x_{ij} \in \mathbb{Z}_+\): vehicles moved from \(i\) to \(j\)
- \(u_j \ge 0\): uncovered forecast demand after repositioning

## Objective

\[
\min \lambda_r \sum_{(i,j)\in A} c_{ij}x_{ij} + \lambda_u\sum_{j\in Z}u_j
\]

## Constraints

Vehicle supply:

\[
\sum_{j:(i,j)\in A}x_{ij} \le v_i \quad \forall i\in Z
\]

Demand coverage:

\[
v_j - \sum_{k:(j,k)\in A}x_{jk} + \sum_{i:(i,j)\in A}x_{ij} + u_j \ge d_j
\]

The uncovered-demand variable keeps the model feasible even if total demand exceeds fleet supply or movement-radius restrictions make some shortages unreachable.

## Why integer variables?

A vehicle is indivisible, so repositioning decisions should be integer. For large fleets the LP relaxation can be useful for speed, but this portfolio implementation keeps the operational interpretation exact.

## Extensions

1. Multi-period time-expanded network with vehicles traveling across periods.
2. Scenario-indexed demand for stochastic optimization.
3. Chance/service-level constraints.
4. Driver availability and break constraints.
5. Equity constraints by borough or neighborhood.
