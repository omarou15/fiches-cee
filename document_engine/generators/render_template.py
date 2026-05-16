from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_.]+)\s*}}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: dict[str, Any], dotted_path: str) -> Any:
    value: Any = data
    for part in dotted_path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def format_money(value: Any) -> str:
    if value is None or value == "":
        return "A COMPLETER"
    try:
        return f"{float(value):,.2f} EUR".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)


def markdown_list(values: Any, field: str | None = None) -> str:
    if not values:
        return "- A COMPLETER"
    lines: list[str] = []
    for item in values:
        if isinstance(item, dict):
            text = item.get(field or "label") or item.get("description") or item.get("name") or json.dumps(item, ensure_ascii=False)
        else:
            text = str(item)
        lines.append(f"- {text}")
    return "\n".join(lines)


def evidence_list(values: Any) -> str:
    if not values:
        return "- A COMPLETER"
    lines: list[str] = []
    for item in values:
        if isinstance(item, dict):
            text = item.get("text") or item.get("quote") or item.get("label") or json.dumps(item, ensure_ascii=False)
            source = item.get("source_file")
            page = item.get("page")
            suffix = ""
            if source:
                suffix += f" Source: {source}"
            if page:
                suffix += f" page {page}"
            lines.append(f"- {text}{suffix}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def format_quote_lines(lines: Any) -> str:
    if not lines:
        return "| Designation | Quantite | Prix unitaire HT | Total HT |\n|---|---:|---:|---:|\n| A COMPLETER |  |  |  |"
    table = ["| Designation | Quantite | Prix unitaire HT | Total HT |", "|---|---:|---:|---:|"]
    for line in lines:
        qty = line.get("quantity", 1)
        unit = format_money(line.get("unit_price_ht"))
        total = format_money(line.get("total_ht"))
        table.append(f"| {line.get('description', 'A COMPLETER')} | {qty} | {unit} | {total} |")
    return "\n".join(table)


def stringify(value: Any) -> str:
    if value is None or value == "":
        return "A COMPLETER"
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return markdown_list(value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_context(company: dict[str, Any], operation: dict[str, Any], code: str | None = None, fiche: dict[str, Any] | None = None) -> dict[str, Any]:
    quote = operation.get("quote", {})
    invoice = operation.get("invoice", {})
    documents = operation.get("documents", {})
    compliance = operation.get("compliance", {})
    operation_block = dict(operation.get("operation", {}))
    if code and not operation_block.get("cee_code"):
        operation_block["cee_code"] = code

    enriched_company = dict(company)
    if "company_name" not in enriched_company and enriched_company.get("name"):
        enriched_company["company_name"] = enriched_company["name"]
    if "name" not in enriched_company and enriched_company.get("company_name"):
        enriched_company["name"] = enriched_company["company_name"]
    if "logo_path" not in enriched_company and enriched_company.get("logo"):
        enriched_company["logo_path"] = enriched_company["logo"]

    fiche = fiche or {}
    calculation = fiche.get("calculation", {}) if isinstance(fiche.get("calculation"), dict) else {}
    sections = fiche.get("sections") or []
    amount_section = next((section for section in sections if str(section.get("number")) == "5"), {})
    return {
        "company": enriched_company,
        "operation": operation_block,
        "client": operation.get("client", {}),
        "site": operation.get("site", {}),
        "technical": operation.get("technical", {}),
        "calculation": operation.get("calculation", {}),
        "quote": {
            **quote,
            "lines_markdown": format_quote_lines(quote.get("lines")),
            "total_ht_formatted": format_money(quote.get("total_ht")),
            "total_ttc_formatted": format_money(quote.get("total_ttc")),
        },
        "invoice": {
            **invoice,
            "lines_markdown": format_quote_lines(invoice.get("lines") or quote.get("lines")),
            "total_ht_formatted": format_money(invoice.get("total_ht")),
            "total_ttc_formatted": format_money(invoice.get("total_ttc")),
        },
        "documents": {
            **documents,
            "available_markdown": markdown_list(documents.get("available")),
            "missing_markdown": markdown_list(documents.get("missing")),
            "non_compliant_markdown": markdown_list(documents.get("non_compliant")),
        },
        "compliance": {
            **compliance,
            "risks_markdown": markdown_list(compliance.get("risks")),
            "blocking_points_markdown": markdown_list(compliance.get("blocking_points")),
        },
        "fiche": {
            "code": fiche.get("code") or code or operation_block.get("cee_code"),
            "title": fiche.get("title") or "A COMPLETER",
            "sector": fiche.get("sector") or "A COMPLETER",
            "family": fiche.get("family") or "A COMPLETER",
            "version": fiche.get("version") or fiche.get("document_version") or "A COMPLETER",
            "effective_date": fiche.get("effective_date") or "A COMPLETER",
            "required_documents_markdown": evidence_list(fiche.get("required_documents")),
            "technical_requirements_markdown": evidence_list(fiche.get("technical_requirements")),
            "eligibility_conditions_markdown": evidence_list(fiche.get("eligibility_conditions")),
            "control_points_markdown": evidence_list(fiche.get("control_points")),
            "compliance_risks_markdown": evidence_list(fiche.get("compliance_risks") or fiche.get("risks")),
            "source_files_markdown": markdown_list(fiche.get("source_files"), "path"),
            "formula_text": calculation.get("formula_text") or fiche.get("formula_text") or "A COMPLETER",
            "amount_section_text": amount_section.get("text") or "A COMPLETER",
        },
    }


def render_string(template: str, context: dict[str, Any], *, strict: bool = False) -> str:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = get_path(context, name)
        if value is None:
            missing.append(name)
        return stringify(value)

    rendered = PLACEHOLDER_RE.sub(replace, template)
    if strict and missing:
        raise KeyError(f"Missing template placeholders: {', '.join(sorted(set(missing)))}")
    return rendered


def render_template_file(
    template_path: Path,
    company: dict[str, Any],
    operation: dict[str, Any],
    output_path: Path,
    *,
    code: str | None = None,
    fiche: dict[str, Any] | None = None,
    strict: bool = False,
) -> None:
    context = build_context(company, operation, code, fiche)
    rendered = render_string(template_path.read_text(encoding="utf-8"), context, strict=strict)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8", newline="\n")


def field_line(project: dict, name: str, label: str | None = None) -> str:
    item = project.get("fields", {}).get(name, {})
    value = item.get("value")
    status = item.get("status", "missing")
    confidence = item.get("confidence", "low")
    marker = "A VALIDER" if item.get("needs_human_validation") else "CONFIRME"
    return f"- {label or name}: {value} ({status}, {confidence}, {marker})"


def header(title: str, project: dict, company: dict) -> str:
    company_name = company.get("company_name") or company.get("name") or "A COMPLETER"
    return f"# {title}\n\n- Dossier: {project['case_id']}\n- Fiche: {project['code']}\n- Entreprise: {company_name}\n\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Markdown template with company and operation JSON files.")
    parser.add_argument("--template", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--code")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    render_template_file(
        Path(args.template),
        load_json(Path(args.company)),
        load_json(Path(args.operation)),
        Path(args.output),
        code=args.code,
        strict=args.strict,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
