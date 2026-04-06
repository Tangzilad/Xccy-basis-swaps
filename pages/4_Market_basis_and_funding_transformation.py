from __future__ import annotations

from src.analytics.funding import (
    build_tenor_funding_table,
    funding_calculation_windows_payload,
    funding_role_interpretation,
    issuance_choice,
)


def _as_decimal(v: float) -> float:
    return v / 100.0 if v > 1 else v


def _get_market_state(session_state: dict) -> dict:
    ms = session_state.get("market_state")
    if isinstance(ms, dict):
        return ms
    ms = {
        "usd_rate": _as_decimal(float(session_state.get("base_rate", 4.25))),
        "huf_rate": _as_decimal(float(session_state.get("quote_rate", 5.0))),
        "basis_bps": float(session_state.get("cross_currency_basis_bps", -22)),
        "extra_spread_bps": 12.0,
    }
    session_state["market_state"] = ms
    return ms


def render_page() -> None:
    import streamlit as st
    from streamlit_calc_helpers import CalculationWindow, render_calculation_windows
    from ui_shell import LEARNING_PATH, learning_hint, render_global_shell

    st.set_page_config(page_title="4. Market basis and funding transformation", page_icon="📘", layout="wide")
    render_global_shell()
    st.session_state.suggested_page = LEARNING_PATH[3]

    m = _get_market_state(st.session_state)
    usd = _as_decimal(float(m["usd_rate"]))
    huf = _as_decimal(float(m["huf_rate"]))
    basis = float(m["basis_bps"]) / 10_000.0
    extra = float(m["extra_spread_bps"]) / 10_000.0

    tenors = ("3M", "6M", "1Y", "2Y", "5Y")
    scales = (0.9, 1.0, 1.05, 1.1, 1.2)
    rows = build_tenor_funding_table(
        domestic_label="HUF",
        foreign_label="USD",
        domestic_curve_rate=huf,
        foreign_curve_rate=usd,
        basis_spread=basis,
        extra_spread=extra,
        tenors=tenors,
        tenor_scales=scales,
        domestic_curve_slope=0.0008,
        foreign_curve_slope=0.0005,
    )
    one = next(r for r in rows if r["Tenor"] == "1Y")

    huf_choice = issuance_choice(
        issue_currency="HUF",
        direct_rate=float(one["HUF direct"]),
        swapped_rate=float(one["HUF synthetic"]),
    )
    usd_choice = issuance_choice(
        issue_currency="USD",
        direct_rate=float(one["USD direct"]),
        swapped_rate=float(one["USD synthetic"]),
    )

    st.title("4. Market basis and funding transformation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("1Y HUF direct", f"{float(one['HUF direct']):.3%}")
    c2.metric("1Y HUF synthetic", f"{float(one['HUF synthetic']):.3%}")
    c3.metric("1Y USD direct", f"{float(one['USD direct']):.3%}")
    c4.metric("1Y USD synthetic", f"{float(one['USD synthetic']):.3%}")

    st.subheader("Tenor-by-tenor funding table (both currencies)")
    st.dataframe(rows, use_container_width=True)
    st.line_chart(
        {
            "Tenor": [r["Tenor"] for r in rows],
            "HUF delta": [r["HUF delta"] for r in rows],
            "USD delta": [r["USD delta"] for r in rows],
        },
        x="Tenor",
    )

    st.subheader("Role interpretation")
    active_role = str(st.session_state.get("active_role", "issuer"))
    st.info(f"**{active_role.title()} lens:** {funding_role_interpretation(active_role)}")

    st.subheader("Issuance choice panels")
    p1, p2 = st.columns(2)
    p1.markdown("#### HUF funding decision")
    p1.metric("Direct HUF", f"{huf_choice.direct_rate:.3%}")
    p1.metric("Issue USD + swap to HUF", f"{huf_choice.swapped_rate:.3%}")
    p1.metric("Delta (swapped-direct)", f"{huf_choice.delta * 10_000:.2f} bps")
    p1.success(f"{huf_choice.preferred_route} (edge: {huf_choice.savings_bp:.2f} bps)")

    p2.markdown("#### USD funding decision")
    p2.metric("Direct USD", f"{usd_choice.direct_rate:.3%}")
    p2.metric("Issue HUF + swap to USD", f"{usd_choice.swapped_rate:.3%}")
    p2.metric("Delta (swapped-direct)", f"{usd_choice.delta * 10_000:.2f} bps")
    p2.success(f"{usd_choice.preferred_route} (edge: {usd_choice.savings_bp:.2f} bps)")

    st.write("Funding transformation compares direct and synthetic issuance in both directions.")
    learning_hint("Negative delta means swapped issuance is cheaper than direct issuance for that currency.")

    windows_payload = funding_calculation_windows_payload(
        domestic_label="HUF",
        foreign_label="USD",
        domestic_curve_rate=float(one["HUF direct"]) - extra,
        foreign_curve_rate=float(one["USD direct"]) - extra,
        basis_spread=float(one["basis"]),
        extra_spread=float(one["extra_spread"]),
    )
    render_calculation_windows(
        [
            CalculationWindow(
                title=str(w["title"]),
                formula=str(w["formula"]),
                substituted_values=str(w["substituted_values"]),
                sign_convention_notes=tuple(w["sign_notes"]),
                assumptions=tuple(w["assumptions"]),
                result=str(w["result"]),
            )
            for w in windows_payload
        ]
    )
