"""Declared sector-to-sector A2A dependencies.

Only relationships listed here are accepted between sector agents. Each edge
names the capability exposed by the provider, so coupling stays explicit and
reviewable. The orchestrator is not restricted.
"""
from __future__ import annotations

from dataclasses import dataclass

UNRESTRICTED_SENDERS = frozenset({"orchestrator", "gateway"})


@dataclass(frozen=True)
class SectorDependency:
    consumer: str
    provider: str
    task: str
    rationale: str


CROSS_SECTOR_DEPENDENCIES: tuple[SectorDependency, ...] = (
    SectorDependency(
        "finance_sector", "monetary_sector", "repo_rate",
        "Lending-rate transmission (WALR/MCLR spreads) is measured against the policy repo rate, "
        "which only the Monetary agent owns.",
    ),
    SectorDependency(
        "finance_sector", "prices_sector", "cpi_headline",
        "Real lending and deposit rates require headline CPI, owned by the Prices agent.",
    ),
    SectorDependency(
        "fiscal_sector", "monetary_sector", "repo_rate",
        "Interest cost of government borrowing and debt-service sustainability depend on the policy rate.",
    ),
    SectorDependency(
        "fiscal_sector", "prices_sector", "cpi_headline",
        "Nominal-to-real deficit and revenue buoyancy analysis needs headline inflation.",
    ),
    SectorDependency(
        "fiscal_sector", "finance_sector", "bank_credit_growth",
        "Government borrowing can crowd out private credit; the Finance agent owns bank credit growth.",
    ),
    SectorDependency(
        "external_sector", "monetary_sector", "repo_rate",
        "Policy-rate differentials drive capital flows and rupee pressure.",
    ),
    SectorDependency(
        "external_sector", "prices_sector", "cpi_headline",
        "Imported-inflation pass-through and real exchange rate analysis need domestic CPI.",
    ),
)


def is_allowed(sender: str, receiver: str, task: str) -> bool:
    """True when `sender` may ask `receiver` for `task`."""
    if sender in UNRESTRICTED_SENDERS:
        return True
    return any(
        d.consumer == sender and d.provider == receiver and d.task == task
        for d in CROSS_SECTOR_DEPENDENCIES
    )


def dependencies_for(consumer: str) -> list[SectorDependency]:
    return [d for d in CROSS_SECTOR_DEPENDENCIES if d.consumer == consumer]
