# Interview talking points

## 30-second explanation

I built a decision system rather than only a prediction model. Raw trip data is transformed into zone-level time-series features, an XGBoost model forecasts near-term pickup demand, and a mixed-integer network-flow model decides how to reposition the current vehicle fleet. I then evaluate that policy in a rolling simulator using realized origin-destination flows, so the optimizer has to live with the vehicle distribution created by previous decisions.

## What makes it operations research?

The machine-learning model does not choose the action. The action is produced by a constrained optimization model that explicitly trades off demand coverage against repositioning cost and respects vehicle conservation.

## Why not optimize directly on historical demand?

At decision time future demand is unknown. Using realized demand inside the optimizer would leak future information and create an unrealistic upper bound. The simulation therefore optimizes on forecasts but scores decisions against realized trips.

## Most important modeling tradeoff

Increasing the unmet-demand penalty improves coverage but can trigger longer or more frequent repositioning. The cost ratio functions like an operational policy knob. I would choose it using service-level targets or estimated economic costs rather than purely statistical tuning.

## Next technical extension

Move from one-step receding-horizon decisions to a multi-period time-expanded stochastic network model using multiple demand scenarios from probabilistic forecasts.
