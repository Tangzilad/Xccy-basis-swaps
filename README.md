# Xccy Basis Swaps — Educational Simulator

## Teaching objective
This project is designed to **teach the mechanics, intuition, and risk decomposition of cross-currency (XCCY) basis swaps** through a guided, interactive Streamlit experience.

By the end, learners should be able to:
- Explain what an XCCY basis swap does economically.
- Distinguish covered interest parity (CIP) identity mechanics from observed market pricing.
- Interpret why basis exists, why it can persist, and how it behaves across regimes.
- Connect market scenarios to valuation, carry, and hedge outcomes.
- Separate stylized educational assumptions from production pricing requirements.

## CIP and cross-currency basis: economic narrative
At core, CIP says that **FX forwards should align domestic and foreign money-market returns once hedged**, leaving no arbitrage wedge in a frictionless market.

In symbols (simplified):
- CIP-implied forward:
  \[
  F_{CIP} = S_0 \times \frac{(1+r_d T)}{(1+r_f T)}
  \]
- A non-zero cross-currency basis means the traded forward/funding package is not exactly at this frictionless parity level.

### Why the post-crisis wedge can persist (BIS-style interpretation)
A BIS-backed narrative (widely discussed in BIS Quarterly Reviews) is that persistent deviations are not just “free money left on the table,” but the outcome of **balance-sheet-constrained intermediation**:
- **Structural hedging demand** (e.g., institutions that must hedge foreign-currency assets/liabilities) can be one-sided and persistent.
- **Arbitrage capacity is costly and finite** because dealer balance sheets, leverage constraints, liquidity regulation, and internal risk limits bind.
- Therefore, the basis can be interpreted as a **market-clearing shadow price** for balance-sheet/funding capacity, not simply a temporary pricing error.

In this simulator, that intuition is encoded by allowing basis to move with stress, only partially mean-revert, and remain away from zero for extended periods.

## Exact learning sequence
The app is intentionally taught in this sequence:

1. **Mechanics**
   - Instrument anatomy: legs, notionals, reset/pay conventions, FX translation.
2. **Parity**
   - Build CIP intuition from spot/forward/rates and identify the no-arbitrage benchmark.
3. **Wedge**
   - Define basis as the observed wedge from frictionless parity and map its sign.
4. **Funding transformation**
   - Reframe the swap as synthetic term funding transformation across currencies.
5. **Persistence / frictions**
   - Introduce balance-sheet costs, regulation, and flow imbalances as persistence drivers.
6. **Hedge choice**
   - Compare hedge implementations (tenor, roll profile, sensitivity trade-offs).
7. **Stress lab**
   - Apply shocks/regimes and interpret PnL, carry, and hedge performance.

## Canonical market-state schema
To keep the pedagogy coherent, pages operate on a canonical market-state object. Conceptually:

```text
MarketState
  - pair: str                  # e.g., EUR/USD, USD/JPY
  - tenor_years: float         # hedge horizon / swap tenor
  - spot_fx: float             # domestic per unit foreign (or app convention)
  - fwd_fx: float              # implied/observed forward level
  - r_domestic: float          # domestic reference rate
  - r_foreign: float           # foreign reference rate
  - basis_bps: float           # cross-currency basis (signed)
  - curve_domestic: dict       # tenor -> rate
  - curve_foreign: dict        # tenor -> rate
  - vol_fx: float              # stylized FX volatility state
  - stress_regime: str         # baseline/stress/normalization/etc.
  - liquidity_score: float     # stylized intermediation capacity proxy
```

### How sidebar controls mutate state
Sidebar inputs are explicit state mutators:
- **Pair / tenor selectors** → update `pair`, `tenor_years`, and applicable curve templates.
- **Spot/rate sliders** → update `spot_fx`, `r_domestic`, `r_foreign`, and forward parity baseline.
- **Basis control** → directly shocks `basis_bps` around the parity anchor.
- **Regime selector** → updates `stress_regime`, volatility presets, persistence parameters, and scenario overlays.
- **Custom shock toggles** → apply additive or multiplicative deltas to rates/basis/FX before valuation.

Each page reads from the same state snapshot, then computes valuations/risk decomposition from that snapshot to maintain narrative consistency.

## Built-in scenarios and regime parameters
The simulator includes stylized regimes with compact parameter bundles and intuition:

- **Baseline carry**
  - Typical parameters: low FX vol, small basis drift, moderate mean reversion.
  - Intuition: calm conditions where carry and roll-down dominate incremental PnL.

- **Funding stress (basis widener)**
  - Typical parameters: negative liquidity shock, abrupt basis widening, slower reversion.
  - Intuition: hedging demand outstrips arbitrage balance-sheet capacity.

- **Policy divergence**
  - Typical parameters: domestic/foreign front-end rate gap widens; basis response moderate.
  - Intuition: rate differential drives forward mechanics while basis reflects funding imbalance.

- **Risk-off FX shock**
  - Typical parameters: one-step FX gap, elevated vol, correlated basis dislocation.
  - Intuition: macro risk event transmits through both currency and funding channels.

- **Normalization**
  - Typical parameters: positive liquidity repair, tighter basis, lower realized vol.
  - Intuition: post-stress repair, but not necessarily immediate return to zero basis.

## Calculation-window philosophy
The app displays calculations in an explicit “window” style so users can audit every step.

1. **Formula view**
   - Show the symbolic equation (parity, forward, coupon PV, MTM decomposition).
2. **Substituted-values view**
   - Replace symbols with current state values from controls.
3. **Numeric result view**
   - Show final outputs with units (bps, %, base-currency amount).

### Sign conventions (explicit)
- Positive basis means the quoted basis spread is added to the designated leg per app convention.
- PV/MTM signs are from the perspective of the selected role and leg orientation.
- FX quotes follow the app’s pair convention consistently across parity and valuation panes.
- All role views keep the same underlying math, changing only economic interpretation and narrative labels.

## Role-based interpretation modes
A shared calculation engine supports multiple interpretation lenses:

- **Issuer mode**
  - Focus: all-in synthetic funding cost versus direct issuance alternatives.
- **Investor mode**
  - Focus: hedged asset return pickup, carry profile, and mark-to-market sensitivity.
- **Treasury mode**
  - Focus: liquidity planning, rollover exposure, and policy/CSA constraints.
- **Arbitrageur mode**
  - Focus: parity wedge capture net of balance-sheet usage and execution frictions.

These modes do **not** change economic identities; they change which KPIs and commentary are emphasized.

## Architecture overview
A simple educational architecture is assumed:

- **UI layer (Streamlit)**
  - Page routing, controls, charts, and pedagogy text.
- **Domain/model layer**
  - Swap cashflow builder.
  - Discounting/projection utilities.
  - Basis/FX/rate scenario shock functions.
- **Synthetic data layer**
  - Reproducible generators for basis paths, short-rate paths, and FX trajectories.
- **Visualization layer**
  - Plotting components for term structures, path plots, waterfall/risk charts.
- **Validation/tests**
  - Unit tests for deterministic calculations and scenario transforms.

## Run instructions
### 1) Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Launch the app
```bash
streamlit run app.py
```

### 4) Run tests
```bash
pytest -q
```

## Educational boundaries and non-production disclaimer
### What this simulator is for
- Concept learning.
- Comparative scenario intuition.
- Role-based interpretation practice.

### What this simulator is not for
- Trade execution.
- Official pricing, reserves, or accounting sign-off.
- Treasury policy determination in live markets.
- Regulatory or financial reporting.

> **Important:** This repository is an **educational, stylized learning tool**.
> It is **not** execution infrastructure, **not** a pricing/risk system of record,
> and **not** suitable for live trading, valuation sign-off, treasury operations,
> or regulatory reporting. Any outputs are illustrative and must not be used as
> investment, accounting, legal, or risk-management advice.

## Stylized limitations
- No production-grade multi-curve bootstrapping.
- Simplified day-count/business-day handling.
- Limited collateral/CSA, margining dynamics, and convexity treatment.
- Regime templates are pedagogical abstractions, not full empirical calibrations.
- Synthetic histories are not calibrated to any specific live market dataset.
- Outputs are parameter-sensitive and should be interpreted directionally.
