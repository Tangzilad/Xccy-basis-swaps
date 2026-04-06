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

## Exact learning sequence (current pages)
The app is intentionally taught in this sequence, matching the current Streamlit page files and the HUF/USD-focused lab progression:

1. **Start here** (`app.py`)
   - Shared state orientation, scenario status, and base-vs-stressed snapshot comparison.
2. **XCCY mechanics** (`pages/2_XCCY_mechanics.py`)
   - Instrument anatomy and leg-level intuition.
3. **Parity lab** (`pages/3_Parity_lab.py`)
   - CIP benchmark construction from spot and curves.
4. **Market basis and funding transformation** (`pages/4_Market_basis_and_funding_transformation.py`)
   - Wedge interpretation and synthetic funding translation.
5. **Persistence / XVA / arbitrage limits** (`pages/5_Persistence_XVA_arbitrage_limits.py`)
   - Balance-sheet constraints, frictions, and persistence channels.
6. **Hedged pickup and hedge choice** (`pages/6_Hedged_pickup_and_hedge_choice.py`)
   - Strategy trade-offs across carry, risk, and implementation.
7. **HUF/USD strategy and stress lab** (`pages/7_HUF_USD_strategy_and_stress_lab.py`)
   - End-to-end scenario stress exercise on the canonical HUF/USD state.

## Canonical market-state contract (real implementation)
All pages consume a shared canonical object in `st.session_state["market_state"]`.

### Top-level keys in session canonical state
The required top-level keys are:

```text
market_state
  - seed: int
  - regime: dict[str, Any]  # name, level, slope, curvature, noise_scale
  - base_snapshot: dict[str, Any]
  - stressed_snapshot: dict[str, Any]
  - scenario: str
```

Notes:
- `base_snapshot` is the anchor state used for "current market".
- `stressed_snapshot` is scenario-adjusted while preserving the same schema.
- `scenario` is `"none"` unless a scenario is applied via shell controls.

### Snapshot dataframe structure
Each snapshot (`base_snapshot` and `stressed_snapshot`) includes:

- `tenors: list[str]`
- `spot_fx: float`
- `regime_summary: dict`
- `usd_curve_df` columns:
  - `tenor`, `years`, `usd_zero_rate`, `discount_factor`
- `huf_curve_df` columns:
  - `tenor`, `years`, `huf_zero_rate`, `discount_factor`
- `theoretical_forward_df` columns:
  - `tenor`, `years`, `theoretical_forward`
- `market_forward_df` columns:
  - `tenor`, `years`, `market_forward`
- `basis_curve_df` columns:
  - `tenor`, `years`, `basis_bps`, `implied_basis_decimal`
- `credit_assumptions` columns:
  - `tenor`, `years`, `credit_spread_bps`, `credit_spread_decimal`
- `friction_assumptions` columns:
  - `tenor`, `years`, `funding_friction_bps`, `funding_friction_decimal`

### Controller responsibilities
`src/controllers/market_state_controller.py` owns mutation and validation of canonical state:

- **Initialization / canonicalization**
  - `ensure_market_state(...)` guarantees required top-level keys and snapshots.
  - `regenerate_market_state(...)` refreshes base snapshot from seed/regime and resets stress.
- **Scenario pipeline**
  - `build_custom_scenario(...)` maps custom UI choices to scenario definitions.
  - `apply_state_scenario(...)` transforms only the stressed snapshot and records scenario name.
- **Invariant enforcement**
  - `clip_regime(...)` bounds regime parameters.
  - `_validate_snapshot(...)` clips spot/rates/spreads/forwards and recomputes market forwards.
- **Shell-facing summary**
  - `summarize_for_shell(...)` exports 1Y controls (rates, spot, basis) for UI display.
  - `make_stress_table(...)` builds base-vs-stressed basis deltas.

### Shell mutation flow
The global shell (`ui_shell.py`) mutates state through an explicit flow:

1. `ensure_market_state_initialized()` seeds defaults and hydrates canonical state.
2. `get_canonical_market_context(...)` normalizes legacy payloads to canonical shape.
3. Scenario selection is captured in `selected_scenario`.
4. **Regenerate market** button:
   - calls `regenerate_market_state(...)`
   - resets scenario to `"none"`.
5. **Apply scenario** button:
   - builds scenario (library or custom),
   - calls `apply_state_scenario(...)`,
   - updates `stressed_snapshot` and `scenario`.
6. `_sync_sidebar_fields()` mirrors canonical 1Y summary into sidebar convenience fields:
   - `base_rate`, `quote_rate`, `spot_fx`, `cross_currency_basis_bps`
   - plus legacy convenience keys retained for backward page compatibility.

Every page reads from the same canonical context, so pedagogy and calculations stay coherent while moving from mechanics to the HUF/USD stress lab.

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
