# Xccy Basis Swaps — Educational Simulator

## Teaching objective
The project is designed to **teach the mechanics, intuition, and risk decomposition of cross-currency (XCCY) basis swaps** through a guided, interactive Streamlit experience.

Learners should finish the module able to:
- Explain what an XCCY basis swap does economically.
- Interpret why basis exists and how it moves.
- Connect market scenarios to valuation, carry, and hedge outcomes.
- Distinguish between stylized educational assumptions and production pricing requirements.

## Full pedagogy chain
1. **Context framing**
   - Introduce funding asymmetry across currencies, collateral conventions, and basis as a market-clearing spread.
2. **Instrument anatomy**
   - Walk through legs (floating/fixed where applicable), notionals, reset conventions, payment schedules, and FX translation.
3. **Curve and discounting intuition**
   - Explain domestic vs foreign discount factors and where basis enters the projected cashflows.
4. **Single-trade valuation**
   - Show mark-to-market construction from projected coupons + discounting + FX conversion.
5. **Risk decomposition**
   - Break PnL into rate move, basis move, FX move, and carry/roll components.
6. **Scenario-based interpretation**
   - Stress widening/tightening basis, steepening curves, and currency shocks.
7. **Reflection & transfer**
   - Prompt users to compare simulated outcomes with real market narratives and identify model simplifications.

## Page-by-page learning flow
The Streamlit app is intended to be consumed in a progressive sequence:

1. **Welcome / Learning Goals**
   - Defines prerequisites and expected outcomes.
2. **Market Setup**
   - Lets users pick currency pair, tenor, baseline curves, and initial basis level.
3. **Swap Construction**
   - Displays instrument terms and leg-level cashflow scaffolding.
4. **Valuation Dashboard**
   - Computes educational MTM and visualizes discounted cashflows.
5. **Risk & Sensitivities**
   - Shows directional deltas to basis, rates, and FX assumptions.
6. **Scenario Lab**
   - Runs predefined stress cases and custom user shocks.
7. **Synthetic Data Explorer**
   - Visualizes generated paths used to animate historical-like narratives.
8. **Quiz / Recap (optional)**
   - Reinforces concept checks and interpretation discipline.

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

## Synthetic generator logic
Synthetic data is pedagogical, not market-replay quality. The generator logic follows a reproducible pattern:

1. **Seed control**
   - Fixed random seed for deterministic teaching runs.
2. **Rates process**
   - Mean-reverting or random-walk-like short-rate path with bounded shocks.
3. **Basis process**
   - Regime-aware path (normal, stress-widening, normalization) around an anchor level.
4. **FX process**
   - Drift + volatility process with optional correlation to rates/basis shocks.
5. **Curve construction**
   - Convert simulated short-rate states into simple tenor points via smoothing/interpolation.
6. **Scenario overlays**
   - Deterministic shock templates applied on top of generated baseline paths.

## Scenario descriptions
The simulator should include stylized scenarios such as:

- **Baseline carry**
  - Stable rates, mild basis mean reversion, low FX volatility.
- **Funding stress (basis widener)**
  - Abrupt basis widening with partial persistence.
- **Policy divergence**
  - One currency’s front-end rates rise while the other remains anchored.
- **Risk-off FX shock**
  - FX gap move with spillover into basis and curve shape.
- **Normalization**
  - Post-stress basis tightening with declining realized volatility.

## Known limitations
- No production-grade multi-curve bootstrapping.
- Simplified day-count/business-day handling.
- Limited collateral/CSA and convexity treatment.
- Educational scenario assumptions may understate tail dependence.
- Synthetic histories are not calibrated to any specific live market dataset.
- Results are sensitive to user-selected parameters and should be interpreted directionally.

## Educational / stylized disclaimer
> **Important:** This repository is an **educational, stylized learning tool**.
> It is **not** execution infrastructure, **not** a pricing/risk system of record,
> and **not** suitable for live trading, valuation sign-off, treasury operations,
> or regulatory reporting. Any outputs are illustrative and must not be used as
> investment, accounting, legal, or risk-management advice.
