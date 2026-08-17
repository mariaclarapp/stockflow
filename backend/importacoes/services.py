from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from medicamentos.domain import (
    CLASSIFICACAO_MANIPULADO,
    descricao_possui_marcador_manipulado,
)
from medicamentos.models import Classificacao, Medicamento, SubgrupoGmus

from .models import Importacao


class InventoryPersistenceError(ValueError):
    pass


class DuplicateInventoryImportError(InventoryPersistenceError):
    pass


def persist_inventory_import(*, parsed_data, user, nome_arquivo):
    """Persist one new inventory import from normalized parser output."""
    with transaction.atomic():
        _validate_import_context(parsed_data, user, nome_arquivo)

        metadata = parsed_data["metadata"]
        competencia_data = metadata["competencia"]
        ups_data = metadata["ups"]
        report_type = parsed_data["tipo_relatorio"]
        file_hash = parsed_data["hash_arquivo"]
        divergencias = []

        competencia, competencia_criada = Competencia.objects.get_or_create(
            ano=competencia_data["ano"],
            mes=competencia_data["mes"],
        )
        ups, ups_criada = Ups.objects.get_or_create(
            codigo_gmus=ups_data["codigo_gmus"],
            id_unidade_gmus=ups_data["id_unidade_gmus"],
            defaults={"nome": ups_data["nome"]},
        )
        if not ups_criada and ups.nome != ups_data["nome"]:
            divergencias.append(
                {
                    "tipo": "ups_nome",
                    "severity": "warning",
                    "codigo_gmus": ups.codigo_gmus,
                    "valor_cadastrado": ups.nome,
                    "valor_relatorio": ups_data["nome"],
                }
            )

        if Importacao.objects.filter(
            competencia=competencia,
            ups=ups,
            tipo_relatorio=report_type,
        ).exists():
            raise DuplicateInventoryImportError(
                "Ja existe uma importacao para esta competencia, UPS e tipo de relatorio."
            )

        try:
            with transaction.atomic():
                importacao = Importacao.objects.create(
                    nome_arquivo=nome_arquivo,
                    hash_arquivo=file_hash,
                    tipo_relatorio=report_type,
                    data_importacao=timezone.now(),
                    status=Importacao.Status.CONCLUIDA,
                    usuario=user,
                    competencia=competencia,
                    ups=ups,
                )
        except IntegrityError as error:
            if Importacao.objects.filter(
                competencia=competencia,
                ups=ups,
                tipo_relatorio=report_type,
            ).exists():
                raise DuplicateInventoryImportError(
                    "Ja existe uma importacao para esta competencia, UPS e tipo de relatorio."
                ) from error
            raise

        parser_errors = list(parsed_data.get("inconsistencies", []))
        invalid_lines = {
            item.get("line")
            for item in parser_errors
            if item.get("severity", "error") == "error"
            and item.get("line") is not None
        }
        service_errors = []
        created_medicines = set()
        reused_medicines = set()
        created_lots = set()
        reused_lots = set()
        reported_divergences = set()
        stock_count = 0
        record_lines = {
            record.get("line") for record in parsed_data.get("records", [])
        }
        ignored_count = len(invalid_lines - record_lines)

        for record in parsed_data.get("records", []):
            line = record.get("line")
            if line in invalid_lines:
                ignored_count += 1
                continue

            try:
                medicine_data = _validate_record(record)
                subgroup = _get_or_create_subgroup(medicine_data.get("subgrupo"))
                _register_subgroup_divergence(
                    subgroup=subgroup,
                    subgroup_data=medicine_data.get("subgrupo"),
                    line=line,
                    divergences=divergencias,
                    reported=reported_divergences,
                )
                medicine, medicine_created = Medicamento.objects.get_or_create(
                    codigo_gmus=medicine_data["codigo_gmus"],
                    defaults={
                        "descricao": medicine_data["descricao"],
                        "unidade": medicine_data["unidade"],
                        "subgrupo_gmus": subgroup,
                    },
                )
                _register_medicine_divergences(
                    medicine=medicine,
                    medicine_data=medicine_data,
                    subgroup=subgroup,
                    line=line,
                    divergences=divergencias,
                    reported=reported_divergences,
                )
                _ensure_manipulated_classification(
                    medicine=medicine,
                    description=medicine_data["descricao"],
                )

                lot, lot_created = _get_or_create_lot(medicine, record.get("lote"))
            except InventoryPersistenceError as error:
                service_errors.append(
                    {
                        "line": line,
                        "type": "persistence_validation",
                        "severity": "error",
                        "message": str(error),
                    }
                )
                ignored_count += 1
                continue

            if medicine_created:
                created_medicines.add(medicine.pk)
            elif medicine.pk not in created_medicines:
                reused_medicines.add(medicine.pk)

            if lot is not None:
                if lot_created:
                    created_lots.add(lot.pk)
                elif lot.pk not in created_lots:
                    reused_lots.add(lot.pk)

            Estoque.objects.create(
                medicamento=medicine,
                ups=ups,
                competencia=competencia,
                lote=lot,
                importacao=importacao,
                quantidade=record["quantidade"],
            )
            stock_count += 1

        has_warnings = any(
            item.get("severity") == "warning" for item in parser_errors
        )
        if invalid_lines or service_errors:
            importacao.status = Importacao.Status.CONCLUIDA_PARCIAL
            importacao.save(update_fields=["status"])
        elif has_warnings or divergencias:
            importacao.status = Importacao.Status.CONCLUIDA_COM_ALERTAS
            importacao.save(update_fields=["status"])

        return {
            "importacao": importacao,
            "importacao_criada": True,
            "competencia_criada": competencia_criada,
            "ups_criada": ups_criada,
            "registros_recebidos": len(parsed_data.get("records", [])),
            "registros_processados": stock_count,
            "registros_ignorados": ignored_count,
            "medicamentos_criados": len(created_medicines),
            "medicamentos_reutilizados": len(reused_medicines),
            "lotes_criados": len(created_lots),
            "lotes_reutilizados": len(reused_lots),
            "estoques_criados": stock_count,
            "divergencias": divergencias,
            "erros": parser_errors + service_errors,
        }


def _validate_import_context(parsed_data, user, nome_arquivo):
    if not getattr(user, "is_authenticated", False):
        raise InventoryPersistenceError("Um usuario autenticado e obrigatorio.")
    if not nome_arquivo:
        raise InventoryPersistenceError("O nome do arquivo e obrigatorio.")

    metadata = parsed_data.get("metadata") or {}
    competencia = metadata.get("competencia") or {}
    ups = metadata.get("ups") or {}
    if competencia.get("ano") is None or competencia.get("mes") is None:
        raise InventoryPersistenceError("Competencia ausente nos metadados.")
    if (
        not ups.get("codigo_gmus")
        or not ups.get("id_unidade_gmus")
        or not ups.get("nome")
    ):
        raise InventoryPersistenceError("UPS ausente nos metadados.")
    if not parsed_data.get("tipo_relatorio"):
        raise InventoryPersistenceError("Tipo de relatorio ausente no parser.")
    file_hash = parsed_data.get("hash_arquivo") or ""
    if len(file_hash) != 64:
        raise InventoryPersistenceError("Hash SHA-256 do arquivo invalido.")
    try:
        int(file_hash, 16)
    except ValueError as error:
        raise InventoryPersistenceError("Hash SHA-256 do arquivo invalido.") from error


def _validate_record(record):
    medicine = record.get("medicamento") or {}
    if not medicine.get("codigo_gmus"):
        raise InventoryPersistenceError("Codigo G-MUS do medicamento ausente.")
    if not medicine.get("descricao"):
        raise InventoryPersistenceError("Descricao do medicamento ausente.")
    if record.get("quantidade") is None:
        raise InventoryPersistenceError("Qtde Virt. ausente.")
    if record["quantidade"] < 0:
        raise InventoryPersistenceError(
            "Qtde Virt. negativa nao representa estoque valido."
        )
    return {
        **medicine,
        "unidade": medicine.get("unidade") or "",
    }


def _get_or_create_subgroup(subgroup_data):
    if not subgroup_data:
        return None

    code = subgroup_data.get("codigo_gmus")
    name = subgroup_data.get("nome") or ""
    if code is not None and code != "":
        try:
            code = int(code)
        except (TypeError, ValueError) as error:
            raise InventoryPersistenceError("Codigo do subgrupo invalido.") from error
        subgroup, _ = SubgrupoGmus.objects.get_or_create(
            codigo_gmus=code,
            defaults={"nome": name},
        )
        return subgroup

    if not name:
        return None
    matches = list(
        SubgrupoGmus.objects.filter(codigo_gmus__isnull=True, nome=name)[:2]
    )
    if len(matches) > 1:
        raise InventoryPersistenceError(
            "Subgrupo sem codigo possui mais de uma correspondencia."
        )
    if matches:
        return matches[0]
    return SubgrupoGmus.objects.create(codigo_gmus=None, nome=name)


def _get_or_create_lot(medicine, lot_data):
    if not lot_data:
        return None, False

    code = lot_data.get("codigo_lote")
    if not code:
        raise InventoryPersistenceError("Codigo do lote ausente.")
    validity = lot_data.get("validade")
    matches = list(
        Lote.objects.filter(
            medicamento=medicine,
            codigo_lote=code,
            data_validade=validity,
        )[:2]
    )
    if len(matches) > 1:
        raise InventoryPersistenceError(
            "Lote possui mais de uma correspondencia para medicamento, codigo e validade."
        )
    if matches:
        return matches[0], False
    return (
        Lote.objects.create(
            medicamento=medicine,
            codigo_lote=code,
            data_validade=validity,
        ),
        True,
    )


def _ensure_manipulated_classification(*, medicine, description):
    if not descricao_possui_marcador_manipulado(description):
        return

    classification, _ = Classificacao.objects.get_or_create(
        nome=CLASSIFICACAO_MANIPULADO,
        defaults={"ativo": True},
    )
    if not classification.ativo:
        classification.ativo = True
        classification.save(update_fields=["ativo"])
    medicine.classificacoes.add(classification)


def _register_medicine_divergences(
    *, medicine, medicine_data, subgroup, line, divergences, reported
):
    comparisons = [
        ("medicamento_descricao", medicine.descricao, medicine_data["descricao"]),
        ("medicamento_unidade", medicine.unidade, medicine_data["unidade"]),
        (
            "medicamento_subgrupo",
            medicine.subgrupo_gmus_id,
            subgroup.pk if subgroup else None,
        ),
    ]
    for divergence_type, stored_value, report_value in comparisons:
        key = (medicine.pk, divergence_type, str(report_value))
        if stored_value == report_value or key in reported:
            continue
        divergences.append(
            {
                "line": line,
                "tipo": divergence_type,
                "severity": "warning",
                "codigo_gmus": medicine.codigo_gmus,
                "valor_cadastrado": stored_value,
                "valor_relatorio": report_value,
            }
        )
        reported.add(key)


def _register_subgroup_divergence(
    *, subgroup, subgroup_data, line, divergences, reported
):
    if not subgroup or not subgroup_data:
        return
    report_name = subgroup_data.get("nome") or ""
    key = (subgroup.pk, "subgrupo_nome", report_name)
    if subgroup.nome == report_name or key in reported:
        return
    divergences.append(
        {
            "line": line,
            "tipo": "subgrupo_nome",
            "severity": "warning",
            "codigo_gmus": subgroup.codigo_gmus,
            "valor_cadastrado": subgroup.nome,
            "valor_relatorio": report_name,
        }
    )
    reported.add(key)
