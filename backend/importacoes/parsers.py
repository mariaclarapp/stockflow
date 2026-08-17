import csv
import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path


ENCODINGS = ("utf-8", "cp1252", "latin-1")
DELIMITERS = (",", ";", "\t")

FILTERS_RE = re.compile(
    r"Competência:\s*(?P<competencia>\d{6})\.\s*"
    r"UPS:\s*(?P<ups_nome>.+?)\s*/\s*(?P<ups_codigo>\d+)\s*"
    r"\((?P<ups_id>\d+)\)",
    re.IGNORECASE,
)
UNIDADE_RE = re.compile(r"Unidade:\s*(?P<id>\d+)\s*-\s*(?P<nome>.+)")
MATERIAL_RE = re.compile(r"^(?P<descricao>.+?)\s*\((?P<codigo>\d+(?:\.\d+)?)\)\s*$")
MATERIAL_CODE_ONLY_RE = re.compile(r"^\((?P<codigo>\d+(?:\.\d+)?)\)\s*$")
SUBGRUPO_RE = re.compile(r"^(?P<nome>.+?)\s*\((?P<codigo>\d+)\)\s*$")
LOTE_VALIDADE_RE = re.compile(
    r"^(?P<lote>.+?)\s*/\s*(?P<validade>\d{2}/\d{2}/\d{4})$"
)


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
        "tipo_relatorio": "inventario",
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
