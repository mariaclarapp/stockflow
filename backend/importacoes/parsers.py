import csv
import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

from .report_types import REPORT_TYPE_INVENTORY, REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK


ENCODINGS = ("utf-8", "cp1252", "latin-1")
DELIMITERS = (",", ";", "\t")
INVENTORY_REQUIRED_HEADERS = {
    "Material / Apresentação",
    "Unidade",
    "Lote / Validade",
    "Qtde Virt.",
}
STOCK_REQUIRED_HEADERS = {"Material / Apresentação", "Unidade", "Quantidade"}
MOVEMENT_REQUIRED_HEADERS = {"Material", "Saldo Atual"}

FILTERS_RE = re.compile(
    r"Competência:\s*(?P<competencia>\d{6})\.\s*"
    r"UPS:\s*(?P<ups_nome>.+?)\s*/\s*(?P<ups_codigo>\d+)\s*"
    r"\((?P<ups_id>\d+)\)",
    re.IGNORECASE,
)
STOCK_FILTERS_RE = re.compile(
    r"Competência Inicial:\s*(?P<competencia_inicial>\d{6})\s*"
    r"Competência Final:\s*(?P<competencia_final>\d{6})\s*"
    r"UPS:\s*(?P<ups_nome>.+?)\s*/\s*(?P<ups_codigo>\d+)\s*"
    r"\((?P<ups_id>\d+)\)",
    re.IGNORECASE,
)
MOVEMENT_FILTERS_RE = re.compile(
    r"Data Inicial:\s*(?P<data_inicial>\d{2}/\d{2}/\d{4})\.\s*"
    r"Data Final:\s*(?P<data_final>\d{2}/\d{2}/\d{4})\.\s*"
    r"UPS:\s*(?P<ups_nome>.+?)\s*\((?P<ups_id>\d+)\)",
    re.IGNORECASE,
)
UNIDADE_RE = re.compile(r"Unidade:\s*(?P<id>\d+)\s*-\s*(?P<nome>.+)")
MATERIAL_RE = re.compile(r"^(?P<descricao>.+?)\s*\((?P<codigo>\d+(?:\.\d+)?)\)\s*$")
MATERIAL_CODE_ONLY_RE = re.compile(r"^\((?P<codigo>\d+(?:\.\d+)?)\)\s*$")
SUBGRUPO_RE = re.compile(r"^(?P<nome>.+?)\s*\((?P<codigo>\d+)\)\s*$")
LOTE_VALIDADE_RE = re.compile(
    r"^(?P<lote>.+?)\s*/\s*(?P<validade>\d{2}/\d{2}/\d{4})$"
)


class UnknownReportTypeError(ValueError):
    pass


def detect_report_type(source):
    raw_bytes = _read_source(source)
    text, _ = _decode(raw_bytes)
    delimiter = _detect_delimiter(text)
    rows = list(csv.reader(StringIO(text), delimiter=delimiter))

    has_title = False
    has_filters = False
    has_unit = False
    has_required_headers = False
    has_stock_title = False
    has_stock_headers = False
    has_movement_title = False
    has_movement_headers = False

    for row in rows:
        values = [value.strip() for value in row]
        has_title = has_title or any(
            value.casefold() == "inventário".casefold() for value in values
        )
        has_filters = has_filters or any(FILTERS_RE.search(value) for value in values)
        has_unit = has_unit or any(UNIDADE_RE.search(value) for value in values)
        has_required_headers = has_required_headers or INVENTORY_REQUIRED_HEADERS.issubset(
            set(values)
        )
        has_stock_title = has_stock_title or any(
            value.casefold() == "consulta de estoque".casefold() for value in values
        )
        has_stock_headers = has_stock_headers or STOCK_REQUIRED_HEADERS.issubset(
            set(values)
        )
        normalized_values = {_normalize_text(value) for value in values}
        has_movement_title = has_movement_title or any(
            "movimentacao de estoque" in value and "sintetico" in value
            for value in normalized_values
        )
        has_movement_headers = has_movement_headers or {
            "material", "saldo atual"
        }.issubset(normalized_values)

    if has_title and has_filters and has_unit and has_required_headers:
        return REPORT_TYPE_INVENTORY

    if has_stock_title and has_stock_headers and any(
        STOCK_FILTERS_RE.search(value)
        for row in rows
        for value in row
    ):
        return REPORT_TYPE_STOCK

    if has_movement_title and has_movement_headers and any(
        MOVEMENT_FILTERS_RE.search(value)
        for row in rows
        for value in row
    ):
        return REPORT_TYPE_MOVEMENT

    raise UnknownReportTypeError("Tipo de relatório não reconhecido.")


def parse_report_csv(source):
    raw_bytes = _read_source(source)
    report_type = detect_report_type(raw_bytes)
    parsers = {
        REPORT_TYPE_INVENTORY: parse_inventory_csv,
        REPORT_TYPE_STOCK: parse_stock_csv,
        REPORT_TYPE_MOVEMENT: parse_movement_csv,
    }
    return parsers[report_type](raw_bytes)


def parse_stock_csv(source):
    """Parse a Consulta de Estoque report with one total per medicine."""
    raw_bytes = _read_source(source)
    text, encoding = _decode(raw_bytes)
    delimiter = _detect_delimiter(text)
    rows = list(csv.reader(StringIO(text), delimiter=delimiter))
    metadata = {
        "encoding": encoding,
        "delimiter": delimiter,
        "competencia": None,
        "ups": None,
        "unidade": None,
        "titulo": "Consulta de Estoque",
        "municipio": None,
        "sistema": None,
        "usuario_emissao": None,
        "data_emissao": None,
        "totais": {},
        "headers": [],
        "campo_quantidade_estoque": "Quantidade",
    }
    inconsistencies = []
    records = []

    for line_number, row in enumerate(rows, start=1):
        values = [value.strip() for value in row]
        non_empty = [(index, value) for index, value in enumerate(values) if value]
        if not non_empty:
            continue

        _extract_stock_metadata(line_number, values, non_empty, metadata, inconsistencies)
        if _is_stock_auxiliary_line(values, non_empty):
            continue

        material_index, material = _find_stock_material(values)
        if material_index is None:
            continue
        quantity_raw = _find_quantity_after(values, material_index)
        if quantity_raw == "":
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "invalid_quantity",
                    "severity": "error",
                    "message": "Quantidade em formato inesperado.",
                    "raw": _raw_row(row),
                }
            )
            continue
        quantity = _parse_quantity(quantity_raw)
        medicine = _parse_material(material)
        if not medicine:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "invalid_material",
                    "severity": "error",
                    "message": "Medicamento sem codigo G-MUS valido.",
                    "raw": _raw_row(row),
                    "fallback": {
                        "descricao": material,
                        "unidade": next(
                            (
                                value
                                for value in values[material_index + 1 :]
                                if value and not re.fullmatch(r"[0-9.]+", value)
                            ),
                            "",
                        ),
                        "quantidade": quantity,
                    },
                }
            )
            continue
        if quantity is None or quantity < 0:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "invalid_quantity",
                    "severity": "error",
                    "message": "Quantidade negativa ou em formato inesperado.",
                    "raw": _raw_row(row),
                }
            )
            continue

        unit = next(
            (
                value
                for value in values[material_index + 1 :]
                if value and not re.fullmatch(r"[0-9.]+", value)
            ),
            "",
        )
        records.append(
            {
                "line": line_number,
                "medicamento": {
                    **medicine,
                    "unidade": unit,
                    "subgrupo": None,
                },
                "lote": None,
                "quantidade": quantity,
                "raw": {"row": _raw_row(row), "quantidade": quantity_raw},
            }
        )

    metadata["total_linhas"] = len(rows)
    metadata["total_registros_extraidos"] = len(records)
    if metadata.get("competencia_inicial") != metadata.get("competencia_final"):
        inconsistencies.append(
            {
                "line": None,
                "type": "competencia_intervalo",
                "severity": "error",
                "message": "O relatorio de estoque deve ter competencia inicial e final iguais.",
            }
        )
    _validate_ups_metadata(metadata, inconsistencies)
    return {
        "tipo_relatorio": REPORT_TYPE_STOCK,
        "hash_arquivo": hashlib.sha256(raw_bytes).hexdigest(),
        "metadata": metadata,
        "records": records,
        "inconsistencies": inconsistencies,
    }


def parse_movement_csv(source):
    """Parse a synthetic movement report aggregated by medicine and UPS."""
    raw_bytes = _read_source(source)
    text, encoding = _decode(raw_bytes)
    delimiter = _detect_delimiter(text)
    rows = list(csv.reader(StringIO(text), delimiter=delimiter))
    metadata = {
        "encoding": encoding,
        "delimiter": delimiter,
        "competencia": None,
        "ups": None,
        "data_inicial": None,
        "data_final": None,
        "titulo": "Movimentação de Estoque - Sintético",
        "headers": [],
    }
    inconsistencies = []
    records = []
    pending_movement = None
    for line_number, row in enumerate(rows, start=1):
        values = [value.strip() for value in row]
        if not any(values):
            continue
        _extract_movement_metadata(line_number, values, metadata)
        if _is_movement_auxiliary_line(values):
            continue
        if len(values) <= 20:
            continue

        material_raw = values[1]
        movement_values, has_movement_values = _extract_movement_values(values)

        if not material_raw:
            continue

        if pending_movement and material_raw and not has_movement_values:
            combined_material = (
                f"{pending_movement['material']} {material_raw}"
            ).strip()
            medicine = _parse_material(combined_material)
            if medicine:
                records.append(
                    _build_movement_record(
                        line_number=pending_movement["line"],
                        medicine=medicine,
                        fields=pending_movement["fields"],
                        raw={
                            "material_linha_anterior": pending_movement["raw"],
                            "continuacao_linha_atual": _raw_row(row),
                        },
                    )
                )
                pending_movement = None
                continue

        if not has_movement_values:
            continue

        medicine = _parse_material(material_raw)
        if not medicine:
            if pending_movement:
                inconsistencies.append(
                    _movement_material_incomplete_issue(pending_movement)
                )
            pending_movement = {
                "line": line_number,
                "material": material_raw,
                "fields": movement_values,
                "raw": _raw_row(row),
            }
            continue

        fields = movement_values
        if any(value is None or value < 0 for value in fields.values()):
            inconsistencies.append({
                "line": line_number,
                "type": "invalid_quantity",
                "severity": "error",
                "message": "Movimentação com quantidade inválida.",
                "raw": _raw_row(row),
            })
            continue
        records.append(
            _build_movement_record(
                line_number=line_number,
                medicine=medicine,
                fields=fields,
                raw={"row": _raw_row(row)},
            )
        )

    if pending_movement:
        inconsistencies.append(_movement_material_incomplete_issue(pending_movement))

    metadata["total_linhas"] = len(rows)
    metadata["total_registros_extraidos"] = len(records)
    _validate_movement_metadata(metadata, inconsistencies)
    return {
        "tipo_relatorio": REPORT_TYPE_MOVEMENT,
        "hash_arquivo": hashlib.sha256(raw_bytes).hexdigest(),
        "metadata": metadata,
        "records": records,
        "inconsistencies": inconsistencies,
    }


def parse_inventory_csv(source):
    """Parse an inventory whose report-level UPS applies to every stock record."""
    raw_bytes = _read_source(source)
    text, encoding = _decode(raw_bytes)
    delimiter = _detect_delimiter(text)
    rows = list(csv.reader(StringIO(text), delimiter=delimiter))

    metadata = {
        "encoding": encoding,
        "delimiter": delimiter,
        "competencia": None,
        "ups": None,
        "unidade": None,
        "titulo": None,
        "municipio": None,
        "sistema": None,
        "usuario_emissao": None,
        "data_emissao": None,
        "totais": {},
        "headers": [],
        "campo_quantidade_estoque": "Qtde Virt.",
    }
    inconsistencies = []
    records = []
    current_medicine = None
    pending_material = None

    for line_number, row in enumerate(rows, start=1):
        values = [value.strip() for value in row]
        non_empty = [(index, value) for index, value in enumerate(values) if value]

        if not non_empty:
            continue

        _extract_metadata(line_number, values, non_empty, metadata)

        if _is_auxiliary_line(values, non_empty):
            continue

        material_raw = values[1] if len(values) > 1 else ""
        lote_index, lote_raw = _find_lote_validade(values)
        quantity_raw = _find_virtual_quantity_after_lote(values, lote_index)
        unit = _find_unit(values)
        subgrupo = _find_subgrupo(values)

        if material_raw and not lote_raw and not quantity_raw:
            code_only_match = MATERIAL_CODE_ONLY_RE.match(material_raw)
            if code_only_match and pending_material:
                current_medicine = {
                    "codigo_gmus": code_only_match.group("codigo"),
                    "descricao": pending_material["descricao"],
                    "descricao_original": f"{pending_material['descricao']} ({code_only_match.group('codigo')})",
                    "unidade": pending_material.get("unidade") or unit,
                    "subgrupo": pending_material.get("subgrupo") or subgrupo,
                    "raw": {
                        "material_linha_anterior": pending_material["raw"],
                        "codigo_linha_atual": material_raw,
                    },
                }
                pending_material = None
            continue

        medicine = _parse_material(material_raw)
        if medicine:
            current_medicine = {
                **medicine,
                "unidade": unit,
                "subgrupo": subgrupo,
                "raw": {"material": material_raw},
            }
            pending_material = None
        elif material_raw and lote_raw and quantity_raw:
            pending_material = {
                "descricao": material_raw.strip(),
                "unidade": unit,
                "subgrupo": subgrupo,
                "raw": material_raw,
            }
            medicine = None

        if not lote_raw and not quantity_raw:
            continue

        if not current_medicine and not pending_material:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "orphan_lot",
                    "severity": "error",
                    "message": "Linha de lote sem medicamento associado.",
                    "raw": _raw_row(row),
                }
            )
            continue

        lot = _parse_lote_validade(lote_raw)
        quantity = _parse_quantity(quantity_raw)

        if not lot:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "invalid_lot_validity",
                    "severity": "error",
                    "message": "Lote/validade em formato inesperado.",
                    "raw": {"lote_validade": lote_raw, "row": _raw_row(row)},
                }
            )
            continue

        if quantity is None:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "invalid_quantity",
                    "severity": "error",
                    "message": "Qtde Virt. em formato inesperado.",
                    "raw": {
                        "quantidade_virtual": quantity_raw,
                        "row": _raw_row(row),
                    },
                }
            )
            continue

        if quantity < 0:
            inconsistencies.append(
                {
                    "line": line_number,
                    "type": "negative_quantity",
                    "severity": "error",
                    "message": "Qtde Virt. negativa nao representa estoque valido.",
                    "raw": {
                        "quantidade_virtual": quantity_raw,
                        "row": _raw_row(row),
                    },
                }
            )
            continue

        if pending_material:
            pending_material["pending_lot"] = {
                "line": line_number,
                "lote": lot,
                "quantity": quantity,
                "quantity_raw": quantity_raw,
                "lote_raw": lote_raw,
                "row": _raw_row(row),
            }
            continue

        records.append(
            _build_record(
                line_number=line_number,
                medicine=current_medicine,
                lot=lot,
                quantity=quantity,
                quantity_raw=quantity_raw,
                lote_raw=lote_raw,
                row=row,
            )
        )

        if pending_material is None and current_medicine and "pending_lot" in current_medicine:
            current_medicine.pop("pending_lot", None)

        if current_medicine and pending_material is None:
            pass

        if (
            current_medicine
            and isinstance(current_medicine.get("raw"), dict)
            and "material_linha_anterior" in current_medicine["raw"]
        ):
            # A split material line can carry the stock data before the code-only line.
            pass

        if pending_material is None:
            continue

    # Second pass is avoided for normal records, but split material/code rows need to emit
    # the pending stock row after the code-only line is read.
    rejected_lines = {
        item["line"]
        for item in inconsistencies
        if item.get("severity") == "error" and item.get("line") is not None
    }
    records, split_inconsistencies = _resolve_split_records(
        rows,
        records,
        rejected_lines,
    )
    inconsistencies.extend(split_inconsistencies)

    metadata["total_linhas"] = len(rows)
    metadata["total_registros_extraidos"] = len(records)
    _validate_ups_metadata(metadata, inconsistencies)

    return {
        "tipo_relatorio": REPORT_TYPE_INVENTORY,
        "hash_arquivo": hashlib.sha256(raw_bytes).hexdigest(),
        "metadata": metadata,
        "records": records,
        "inconsistencies": inconsistencies,
    }


def _read_source(source):
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        path = Path(source)
        if path.exists():
            return path.read_bytes()
        return source.encode("utf-8")
    if isinstance(source, Path):
        return source.read_bytes()
    return source.read()


def _decode(raw_bytes):
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return raw_bytes.decode("utf-8-sig"), "utf-8-sig"
    for encoding in ENCODINGS:
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8"


def _detect_delimiter(text):
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        counts = {delimiter: sample.count(delimiter) for delimiter in DELIMITERS}
        return max(counts, key=counts.get)


def _extract_metadata(line_number, values, non_empty, metadata):
    first_value = values[0] if values else ""

    if len(values) > 3 and values[3] and not metadata["municipio"]:
        metadata["municipio"] = values[3]

    if any(value == "Inventário" for value in values):
        metadata["titulo"] = "Inventário"

    filters_match = FILTERS_RE.search(first_value)
    if filters_match:
        raw_competencia = filters_match.group("competencia")
        metadata["competencia"] = {
            "raw": raw_competencia,
            "ano": int(raw_competencia[:4]),
            "mes": int(raw_competencia[4:]),
        }
        metadata["ups"] = {
            "nome": filters_match.group("ups_nome").strip(),
            "codigo_gmus": filters_match.group("ups_codigo"),
            "id_unidade_gmus": filters_match.group("ups_id"),
        }

    unidade_match = UNIDADE_RE.search(first_value)
    if unidade_match:
        metadata["unidade"] = {
            "id": unidade_match.group("id"),
            "nome": unidade_match.group("nome").strip(),
        }

    if first_value.startswith("Total de Registros da UPS:"):
        metadata["totais"]["registros_ups"] = _parse_int(first_value.rsplit(":", 1)[1])
    elif first_value.startswith("Total de Registros:"):
        metadata["totais"]["registros"] = _parse_int(first_value.rsplit(":", 1)[1])
    elif first_value.startswith("Registros impressos:"):
        printed = next((value for _, value in non_empty[1:]), None)
        metadata["totais"]["registros_impressos"] = _parse_int(printed)

    if any("Material / Apresentação" == value for value in values):
        header = {value: index for index, value in enumerate(values) if value}
        metadata["headers"].append({"line": line_number, "columns": header})

    if any(value.startswith("Relatório emitido pelo sistema") for value in values):
        metadata["sistema"] = next(
            value for value in values if value.startswith("Relatório emitido pelo sistema")
        )
        if "Usuário:" in values:
            user_index = values.index("Usuário:")
            if user_index + 1 < len(values):
                metadata["usuario_emissao"] = values[user_index + 1]

    for value in values:
        if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", value):
            metadata["data_emissao"] = value


def _extract_stock_metadata(line_number, values, non_empty, metadata, inconsistencies):
    first_value = values[0] if values else ""
    if len(values) > 3 and values[3] and not metadata["municipio"]:
        metadata["municipio"] = values[3]

    filters_match = STOCK_FILTERS_RE.search(first_value)
    if filters_match:
        competencia_inicial = filters_match.group("competencia_inicial")
        competencia_final = filters_match.group("competencia_final")
        metadata["competencia_inicial"] = competencia_inicial
        metadata["competencia_final"] = competencia_final
        metadata["competencia"] = {
            "raw": competencia_final,
            "ano": int(competencia_final[:4]),
            "mes": int(competencia_final[4:]),
        }
        metadata["ups"] = {
            "nome": filters_match.group("ups_nome").strip(),
            "codigo_gmus": filters_match.group("ups_codigo"),
            "id_unidade_gmus": filters_match.group("ups_id"),
        }

    unidade_value = next(
        (value for value in values if value.casefold().startswith("unidade:")),
        "",
    )
    unidade_match = re.search(
        r"Unidade:\s*(?P<nome>.+?)\s*\((?P<id>\d+)\)\s*$",
        unidade_value,
        re.IGNORECASE,
    )
    if unidade_match:
        metadata["unidade"] = {
            "id": unidade_match.group("id"),
            "nome": unidade_match.group("nome").strip(),
        }

    total_value = next(
        (value for value in values if value.startswith("Total de Registros da UPS:")),
        "",
    )
    if total_value:
        metadata["totais"]["registros_ups"] = _parse_int(
            total_value.rsplit(":", 1)[1]
        )
    competencia_total = next(
        (
            value
            for value in values
            if value.startswith("Total de Registros da Competência:")
        ),
        "",
    )
    if competencia_total:
        metadata["totais"]["registros_competencia"] = _parse_int(
            next((value for _, value in non_empty[1:]), "")
        )
    relatorio_total = next(
        (
            value
            for value in values
            if value.startswith("Total de Registros do relatório:")
        ),
        "",
    )
    if relatorio_total:
        metadata["totais"]["registros"] = _parse_int(
            next((value for _, value in non_empty[1:]), "")
        )

    if any("Relatório emitido pelo sistema" in value for value in values):
        metadata["sistema"] = next(
            value
            for value in values
            if value.startswith("Relatório emitido pelo sistema")
        )
    for value in values:
        if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", value):
            metadata["data_emissao"] = value

    if any(value == "Material / Apresentação" for value in values):
        metadata["headers"].append(
            {"line": line_number, "columns": {value: index for index, value in enumerate(values) if value}}
        )


def _is_stock_auxiliary_line(values, non_empty):
    first = values[0] if values else ""
    if any(
        value in {"Material / Apresentação", "Unidade", "Quantidade", "Conferência"}
        for value in values
    ):
        return True
    if any(
        value.startswith(
            (
                "Filtros:",
                "Competência:",
                "Unidade:",
                "Total de Registros",
                "Registros impressos:",
            )
        )
        for value in values
    ):
        return True
    if any(value.startswith("Relatório emitido pelo sistema") for value in values):
        return True
    if any(value.startswith("Página:") for value in values):
        return True
    if any("Inovadora Sistemas" in value for value in values):
        return True
    if len(non_empty) == 1 and non_empty[0][1] in {
        "RIBEIRAO CLARO - PR",
        "Secretaria de Desenvolvimento",
        "Consulta de Estoque",
    }:
        return True
    if len(non_empty) == 1 and re.match(
        r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", non_empty[0][1]
    ):
        return True
    return False


def _find_stock_material(values):
    for index, value in enumerate(values):
        if MATERIAL_RE.match(value):
            return index, value
    for index, value in enumerate(values):
        if value and (" - " in value or " + " in value):
            if _find_quantity_after(values, index) != "":
                return index, value
    return None, ""


def _find_quantity_after(values, material_index):
    for value in values[material_index + 1 :]:
        if re.fullmatch(r"[0-9.]+", value):
            return value
    return ""


def _extract_movement_metadata(line_number, values, metadata):
    for value in values:
        match = MOVEMENT_FILTERS_RE.search(value)
        if match:
            start = datetime.strptime(match.group("data_inicial"), "%d/%m/%Y").date()
            end = datetime.strptime(match.group("data_final"), "%d/%m/%Y").date()
            metadata["data_inicial"] = start.isoformat()
            metadata["data_final"] = end.isoformat()
            metadata["competencia"] = {
                "raw": end.strftime("%Y%m"),
                "ano": end.year,
                "mes": end.month,
            }
            metadata["ups"] = {
                "nome": match.group("ups_nome").strip(),
                "codigo_gmus": match.group("ups_id"),
                "id_unidade_gmus": match.group("ups_id"),
            }
        if _normalize_text(value).startswith("ups:") and metadata["ups"] is None:
            ups_match = re.search(r"UPS:\s*(?P<nome>.+?)\s*\((?P<id>\d+)\)", value, re.IGNORECASE)
            if ups_match:
                metadata["ups"] = {
                    "nome": ups_match.group("nome").strip(),
                    "codigo_gmus": ups_match.group("id"),
                    "id_unidade_gmus": ups_match.group("id"),
                }
    if "Material" in values and "Saldo Atual" in values:
        metadata["headers"].append({"line": line_number, "columns": values})


def _is_movement_auxiliary_line(values):
    normalized = [_normalize_text(value) for value in values if value]
    if not normalized:
        return True
    if any(
        value.startswith(prefix)
        for value in normalized
        for prefix in (
            "filtros:", "ups:", "relatorio emitido pelo sistema", "pagina:",
            "total :", "total de registros", "registros impressos:",
        )
    ):
        return True
    if "material" in normalized or "saldo atual" in normalized:
        return True
    return False


def _extract_movement_values(values):
    if len(values) >= 23:
        indexes = (7, 8, 9, 14, 15, 16, 18, 19, 22)
    else:
        indexes = (6, 7, 8, 13, 14, 15, 16, 17, 20)
    raw_values = [values[index] if index < len(values) else "" for index in indexes]
    fields = dict(
        zip(
            (
                "saida",
                "devolucao_saida",
                "compra",
                "transferencia_devolucao",
                "transferencia_entrada",
                "transferencia_saida",
                "acerto_entrada",
                "acerto_saida",
                "saldo_atual",
            ),
            (_parse_movement_quantity(value) for value in raw_values),
        )
    )
    return fields, any(raw_values)


def _build_movement_record(*, line_number, medicine, fields, raw):
    return {
        "line": line_number,
        "medicamento": {**medicine, "unidade": "", "subgrupo": None},
        "quantidade": Decimal("0"),
        "movimentacoes": fields,
        "raw": raw,
    }


def _movement_material_incomplete_issue(pending_movement):
    return {
        "line": pending_movement["line"],
        "type": "movement_material_incomplete",
        "severity": "error",
        "message": "Material da movimentacao sem codigo G-MUS identificavel.",
        "raw": pending_movement["raw"],
    }


def _parse_movement_quantity(value):
    if not value:
        return Decimal("0")
    return _parse_quantity(value)


def _validate_movement_metadata(metadata, inconsistencies):
    if not metadata.get("data_inicial") or not metadata.get("data_final"):
        inconsistencies.append({
            "line": None,
            "type": "movement_period_missing",
            "severity": "error",
            "message": "Período da movimentação não identificado.",
        })
        return
    start = date.fromisoformat(metadata["data_inicial"])
    end = date.fromisoformat(metadata["data_final"])
    if start > end or start.month != end.month or start.year != end.year:
        inconsistencies.append({
            "line": None,
            "type": "movement_period_invalid",
            "severity": "error",
            "message": "O relatório deve representar um único mês de movimentação.",
        })
    _validate_ups_metadata(metadata, inconsistencies)


def _normalize_text(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _validate_ups_metadata(metadata, inconsistencies):
    ups = metadata.get("ups") or {}
    unidade = metadata.get("unidade") or {}
    id_cabecalho = ups.get("id_unidade_gmus")
    id_unidade = unidade.get("id")

    if id_cabecalho and id_unidade and id_cabecalho != id_unidade:
        inconsistencies.append(
            {
                "line": None,
                "type": "ups_unit_id_mismatch",
                "severity": "error",
                "message": (
                    "O identificador da UPS no filtro diverge da unidade do relatorio."
                ),
                "raw": {
                    "id_unidade_filtro": id_cabecalho,
                    "id_unidade_cabecalho": id_unidade,
                },
            }
        )


def _is_auxiliary_line(values, non_empty):
    first = values[0] if values else ""
    labels = {
        "Material / Apresentação",
        "Unidade",
        "Sub-Grupo",
        "Lote / Validade",
        "Qtde Virt.",
        "Qtde R.",
    }
    if any(value in labels for value in values):
        return True
    if first.startswith(("Filtros:", "Unidade:", "Total de Registros", "Registros impressos:")):
        return True
    if any(value.startswith("Relatório emitido pelo sistema") for value in values):
        return True
    if any(value.startswith("Página:") for value in values):
        return True
    if any("Inovadora Sistemas" in value for value in values):
        return True
    if len(non_empty) == 1 and non_empty[0][1] in {
        "RIBEIRAO CLARO - PR",
        "Secretaria de Desenvolvimento",
        "Inventário",
    }:
        return True
    if len(non_empty) == 1 and re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", non_empty[0][1]):
        return True
    return False


def _parse_material(value):
    match = MATERIAL_RE.match(value or "")
    if not match:
        return None
    return {
        "codigo_gmus": match.group("codigo"),
        "descricao": match.group("descricao").strip(),
        "descricao_original": value,
    }


def _find_lote_validade(values):
    for index, value in enumerate(values):
        if LOTE_VALIDADE_RE.match(value):
            return index, value
    return None, ""


def _find_virtual_quantity_after_lote(values, lote_index):
    if lote_index is None:
        return ""
    virtual_index = lote_index + 1
    return values[virtual_index] if virtual_index < len(values) else ""


def _find_unit(values):
    for index in (6, 7):
        if index < len(values) and values[index]:
            return values[index]
    return ""


def _find_subgrupo(values):
    for index in (9, 10):
        if index < len(values) and values[index]:
            match = SUBGRUPO_RE.match(values[index])
            if match:
                return {"nome": match.group("nome").strip(), "codigo_gmus": match.group("codigo")}
            return {"nome": values[index], "codigo_gmus": None}
    return None


def _parse_lote_validade(value):
    match = LOTE_VALIDADE_RE.match(value or "")
    if not match:
        return None
    return {
        "codigo_lote": match.group("lote").strip(),
        "validade": datetime.strptime(match.group("validade"), "%d/%m/%Y").date(),
    }


def _parse_quantity(value):
    raw = (value or "").strip()
    if not raw:
        return None
    if re.match(r"^\d{1,3}(\.\d{3})+$", raw):
        raw = raw.replace(".", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _parse_int(value):
    try:
        return int((value or "").strip())
    except ValueError:
        return None


def _build_record(
    line_number,
    medicine,
    lot,
    quantity,
    quantity_raw,
    lote_raw,
    row,
):
    return {
        "line": line_number,
        "medicamento": {
            "codigo_gmus": medicine["codigo_gmus"],
            "descricao": medicine["descricao"],
            "descricao_original": medicine["descricao_original"],
            "unidade": medicine.get("unidade") or "",
            "subgrupo": medicine.get("subgrupo"),
        },
        "lote": lot,
        "quantidade": quantity,
        "raw": {
            "row": _raw_row(row),
            "lote_validade": lote_raw,
            "quantidade_virtual": quantity_raw,
            "material": medicine.get("raw"),
        },
    }


def _raw_row(row):
    return [value for value in row]


def _resolve_split_records(rows, existing_records, rejected_lines):
    records = []
    inconsistencies = []
    current_medicine = None
    pending = None
    emitted_lines = {record["line"] for record in existing_records}

    for line_number, row in enumerate(rows, start=1):
        if line_number in emitted_lines:
            material = row[1].strip() if len(row) > 1 else ""
            parsed = _parse_material(material)
            if parsed:
                current_medicine = {
                    **parsed,
                    "unidade": _find_unit(row),
                    "subgrupo": _find_subgrupo(row),
                    "raw": {"material": material},
                }
            records.append(next(record for record in existing_records if record["line"] == line_number))
            continue

        values = [value.strip() for value in row]
        if _is_auxiliary_line(values, [(i, v) for i, v in enumerate(values) if v]):
            continue

        material = values[1] if len(values) > 1 else ""
        lote_index, lote_raw = _find_lote_validade(values)
        quantity_raw = _find_virtual_quantity_after_lote(values, lote_index)
        parsed_material = _parse_material(material)

        if parsed_material:
            current_medicine = {
                **parsed_material,
                "unidade": _find_unit(values),
                "subgrupo": _find_subgrupo(values),
                "raw": {"material": material},
            }
            continue

        if line_number in rejected_lines:
            continue

        if material and lote_raw and quantity_raw and not MATERIAL_CODE_ONLY_RE.match(material):
            pending = {
                "line": line_number,
                "descricao": material,
                "unidade": _find_unit(values),
                "subgrupo": _find_subgrupo(values),
                "lote_raw": lote_raw,
                "quantity_raw": quantity_raw,
                "row": row,
            }
            continue

        code_only = MATERIAL_CODE_ONLY_RE.match(material)
        if code_only and pending:
            lot = _parse_lote_validade(pending["lote_raw"])
            quantity = _parse_quantity(pending["quantity_raw"])
            medicine = {
                "codigo_gmus": code_only.group("codigo"),
                "descricao": pending["descricao"],
                "descricao_original": f"{pending['descricao']} ({code_only.group('codigo')})",
                "unidade": pending["unidade"],
                "subgrupo": pending["subgrupo"],
                "raw": {
                    "material_linha_anterior": pending["descricao"],
                    "codigo_linha_atual": material,
                },
            }
            records.append(
                _build_record(
                    pending["line"],
                    medicine,
                    lot,
                    quantity,
                    pending["quantity_raw"],
                    pending["lote_raw"],
                    pending["row"],
                )
            )
            current_medicine = medicine
            pending = None
            continue

        if lote_raw and quantity_raw and current_medicine:
            lot = _parse_lote_validade(lote_raw)
            quantity = _parse_quantity(quantity_raw)
            records.append(
                _build_record(
                    line_number,
                    current_medicine,
                    lot,
                    quantity,
                    quantity_raw,
                    lote_raw,
                    row,
                )
            )

    if pending:
        inconsistencies.append(
            {
                "line": pending["line"],
                "type": "pending_material_without_code",
                "severity": "error",
                "message": "Material com lote e quantidade, mas sem codigo G-MUS encontrado.",
                "raw": pending["row"],
            }
        )

    records.sort(key=lambda item: item["line"])
    return records, inconsistencies
