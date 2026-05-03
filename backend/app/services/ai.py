from __future__ import annotations
from typing import Any


def build_portfolio_context(
    positions: list[Any],
    transactions: list[Any],
    labels: list[Any],
) -> str:
    lines: list[str] = []

    lines.append("Positions:")
    if not positions:
        lines.append("  No positions found.")
    else:
        total_value = sum(float(p.quantity) * float(p.current_price) for p in positions)
        for p in positions:
            value = float(p.quantity) * float(p.current_price)
            pct = (value / total_value * 100) if total_value else 0.0
            if p.avg_cost is not None:
                gain_pct = (float(p.current_price) - float(p.avg_cost)) / float(p.avg_cost) * 100
                gain_str = f"{gain_pct:+.1f}%"
            else:
                gain_str = "N/A"
            lines.append(
                f"  {p.ticker} | {p.name} | "
                f"{p.currency} {value:,.2f} | {pct:.1f}% of total | gain/loss: {gain_str}"
            )

    lines.append("")

    lines.append("Recent transactions (last 30 days):")
    if not transactions:
        lines.append("  No recent transactions.")
    else:
        for t in transactions:
            # Use .executed_at (actual Transaction model column) not .date
            ts = t.executed_at
            date_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            # Use .type (actual Transaction model column) not .action
            txn_type = str(t.type)
            lines.append(
                f"  {date_str} | {t.ticker} | {txn_type} | "
                f"qty {t.quantity} | price {t.price}"
            )

    lines.append("")

    lines.append("Label groups:")
    if not labels:
        lines.append("  No label groups defined.")
    else:
        for lbl in labels:
            tickers_str = ", ".join(lbl.tickers) if lbl.tickers else "none"
            lines.append(f"  {lbl.name}: {tickers_str}")

    return "\n".join(lines)


def build_system_prompt(portfolio_context: str) -> str:
    return (
        "You are a portfolio analyst assistant. "
        "Answer questions about the user's holdings, performance, and allocation. "
        "Do not suggest specific trades or provide financial advice.\n\n"
        "PORTFOLIO CONTEXT\n"
        "================\n"
        + portfolio_context
    )
