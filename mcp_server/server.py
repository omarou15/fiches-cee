from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastmcp import FastMCP  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

from mcp_server.tools.calcul import compute_kwh_cumac as compute_kwh_cumac_tool  # noqa: E402
from mcp_server.tools.chronology import check_chronology as check_chronology_tool  # noqa: E402
from mcp_server.tools.dossier import generate_dossier as generate_dossier_tool  # noqa: E402
from mcp_server.tools.dossier import get_annexe6_row as get_annexe6_row_tool  # noqa: E402
from mcp_server.tools.dossier import get_cadre_contribution as get_cadre_contribution_tool  # noqa: E402
from mcp_server.tools.eligibility import (  # noqa: E402
    check_eligibility as check_eligibility_tool,
    find_control_risks as find_control_risks_tool,
    list_required_documents as list_required_documents_tool,
)
from mcp_server.tools.fiches import get_cee_fiche as get_cee_fiche_tool  # noqa: E402
from mcp_server.tools.fiches import list_cee_fiches as list_cee_fiches_tool  # noqa: E402
from mcp_server.tools.search import search_cee as search_cee_tool  # noqa: E402
from mcp_server.utils.loader import all_codes, support_level  # noqa: E402


mcp = FastMCP(
    name="CEE Open Toolkit",
    instructions=(
        "Expose official CEE fiches, curated rules, eligibility checks, kWh cumac "
        "calculations and draft dossier generation. Never invent missing regulatory values."
    ),
)


def health_payload() -> dict[str, Any]:
    codes = all_codes()
    return {
        "status": "ok",
        "fiches_count": len(codes),
        "supported_full": sum(1 for code in codes if support_level(code) == "supported_full"),
    }


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse(health_payload())


@mcp.tool
def list_cee_fiches(
    sector: str | None = None,
    support_level: str | None = None,
    family: str | None = None,
) -> dict[str, Any]:
    """List available CEE fiches with optional sector/support/family filters."""
    return list_cee_fiches_tool(sector=sector, support_level=support_level, family=family)


@mcp.tool
def get_cee_fiche(code: str, level: str = "curated") -> dict[str, Any]:
    """Return a CEE fiche as curated JSON, extracted JSON, or extracted text."""
    return get_cee_fiche_tool(code=code, level=level)


@mcp.tool
def check_eligibility(code: str, operation: dict[str, Any]) -> dict[str, Any]:
    """Check an operation against the available CEE rules for a fiche."""
    return check_eligibility_tool(code=code, operation=operation)


@mcp.tool
def compute_kwh_cumac(code: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Compute kWh cumac from structured fiche tables and provided variables."""
    return compute_kwh_cumac_tool(code=code, variables=variables)


@mcp.tool
def find_control_risks(code: str, severity: str = "all") -> dict[str, Any]:
    """Return PNCEE rejection/control risks for a fiche."""
    return find_control_risks_tool(code=code, severity=severity)


@mcp.tool
def list_required_documents(code: str) -> dict[str, Any]:
    """List supporting documents required by a fiche."""
    return list_required_documents_tool(code=code)


@mcp.tool
def search_cee(query: str, sector: str | None = None, max_results: int = 10) -> dict[str, Any]:
    """Search CEE fiches by keyword."""
    return search_cee_tool(query=query, sector=sector, max_results=max_results)


@mcp.tool
def generate_dossier(
    code: str,
    operation: dict[str, Any],
    company: dict[str, Any],
    mode: str = "draft",
) -> dict[str, Any]:
    """Generate an inline CEE dossier pack from operation and company data."""
    return generate_dossier_tool(code=code, operation=operation, company=company, mode=mode)


@mcp.tool
def check_chronology(code: str, dates: dict[str, Any]) -> dict[str, Any]:
    """Validate the documentary chronology of a CEE operation."""
    return check_chronology_tool(code=code, dates=dates)


@mcp.tool
def get_cadre_contribution(code: str, operation: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    """Generate the annexe 8 contribution frame as Markdown."""
    return get_cadre_contribution_tool(code=code, operation=operation, company=company)


@mcp.tool
def get_annexe6_row(code: str, operation: dict[str, Any]) -> dict[str, Any]:
    """Generate the annexe 6 recap row for one operation."""
    return get_annexe6_row_tool(code=code, operation=operation)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        path="/mcp",
        stateless_http=True,
    )
