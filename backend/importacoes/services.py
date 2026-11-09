from datetime import date
import re
import unicodedata

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote, SaldoEstoque
from medicamentos.domain import (
    CLASSIFICACAO_MANIPULADO,
    descricao_possui_marcador_manipulado,
)
from medicamentos.models import Classificacao, Medicamento, SubgrupoGmus

from .models import (
    Importacao,
    ImportacaoExclusao,
    MovimentacaoEstoque,
    PendenciaImportacao,
)
from .report_types import (
    REPORT_TYPE_INVENTORY,
    REPORT_TYPE_MOVEMENT,
    REPORT_TYPE_STOCK,
)


class InventoryPersistenceError(ValueError):
    pass


class InventoryImportConflictError(InventoryPersistenceError):
    pass


class DuplicateInventoryImportError(InventoryImportConflictError):
    pass


class SameInventoryFileError(InventoryImportConflictError):
    pass


class ReimportationTargetNotFoundError(InventoryImportConflictError):
    pass


def find_existing_import(parsed_data):
    """Find the import matching a parsed report without changing the database."""
    metadata = parsed_data.get("metadata") or {}
    competence_data = metadata.get("competencia") or {}
    ups_data = metadata.get("ups") or {}
    report_type = parsed_data.get("tipo_relatorio")
    if not report_type or not competence_data or not ups_data.get("id_unidade_gmus"):
        return None

    competencia = Competencia.objects.filter(
        ano=competence_data.get("ano"),
        mes=competence_data.get("mes"),
    ).first()
    if competencia is None:
        return None

    ups_queryset = Ups.objects.filter(id_unidade_gmus=ups_data["id_unidade_gmus"])
    if ups_data.get("codigo_gmus"):
        ups = ups_queryset.filter(codigo_gmus=ups_data["codigo_gmus"]).first()
    else:
        matches = list(ups_queryset.order_by("id")[:2])
        ups = matches[0] if len(matches) == 1 else None
    if ups is None:
        return None
    return Importacao.objects.filter(
        competencia=competencia,
        ups=ups,
        tipo_relatorio=report_type,
    ).first()


def delete_importacao(*, importacao_id, deleted_by):
    """Delete one import and only the records that belong to it."""
    with transaction.atomic():
        importacao = Importacao.objects.select_for_update().get(pk=importacao_id)
        counts = {
            "estoques_excluidos": Estoque.objects.filter(importacao=importacao).count(),
            "saldos_excluidos": SaldoEstoque.objects.filter(importacao=importacao).count(),
            "movimentacoes_excluidas": MovimentacaoEstoque.objects.filter(importacao=importacao).count(),
            "pendencias_excluidas": importacao.pendencias.count(),
        }
        ImportacaoExclusao.objects.create(
            importacao_id_original=importacao.pk,
            nome_arquivo=importacao.nome_arquivo,
            hash_arquivo=importacao.hash_arquivo,
            tipo_relatorio=importacao.tipo_relatorio,
            status_original=importacao.status,
            competencia=importacao.competencia,
            ups=importacao.ups,
            usuario_importacao=importacao.usuario,
            excluida_por=deleted_by,
            contagens=counts,
        )
        Estoque.objects.filter(importacao=importacao).delete()
        SaldoEstoque.objects.filter(importacao=importacao).delete()
        MovimentacaoEstoque.objects.filter(importacao=importacao).delete()
        importacao.delete()
        return counts


@transaction.atomic
def resolver_pendencia_importacao(
    *, importacao_id, pendencia_id, codigo_gmus, resolvida_por
):
    codigo_gmus = (codigo_gmus or "").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", codigo_gmus):
        raise InventoryPersistenceError(
            "Informe um codigo G-MUS numerico valido, como 184.1."
        )

    pendencia = (
        PendenciaImportacao.objects.select_for_update()
        .select_related("importacao", "medicamento")
        .get(pk=pendencia_id, importacao_id=importacao_id)
    )
    if pendencia.status != PendenciaImportacao.Status.PENDENTE:
        raise InventoryPersistenceError("Esta pendencia ja foi resolvida.")
    importacao = Importacao.objects.select_for_update().get(pk=importacao_id)
    if importacao.tipo_relatorio != REPORT_TYPE_STOCK:
        raise InventoryPersistenceError(
            "Somente pendencias de Consulta de Estoque podem ser associadas."
        )

    medicamento, criado = Medicamento.objects.get_or_create(
        codigo_gmus=codigo_gmus,
        defaults={
            "descricao": pendencia.descricao,
            "unidade": pendencia.unidade,
        },
    )
    if (
        pendencia.unidade
        and medicamento.unidade
        and _normalize_match_text(pendencia.unidade)
        != _normalize_match_text(medicamento.unidade)
    ):
        raise InventoryPersistenceError(
            "O medicamento informado possui uma unidade diferente da linha pendente."
        )

    saldo, saldo_criado = SaldoEstoque.objects.select_for_update().get_or_create(
        medicamento=medicamento,
        ups=importacao.ups,
        competencia=importacao.competencia,
        importacao=importacao,
        defaults={"quantidade": pendencia.quantidade},
    )
    if not saldo_criado:
        saldo.quantidade += pendencia.quantidade
        saldo.save(update_fields=["quantidade"])

    pendencia.status = PendenciaImportacao.Status.RESOLVIDA
    pendencia.medicamento = medicamento
    pendencia.resolvida_por = resolvida_por
    pendencia.resolvida_em = timezone.now()
    pendencia.save(
        update_fields=["status", "medicamento", "resolvida_por", "resolvida_em"]
    )

    pendencias_abertas = importacao.pendencias.filter(
        status=PendenciaImportacao.Status.PENDENTE
    )
    importacao.quantidade_nao_associada = sum(
        (item.quantidade for item in pendencias_abertas),
        start=0,
    )
    if not pendencias_abertas.exists() and importacao.erros_nao_corrigiveis == 0:
        importacao.status = (
            Importacao.Status.CONCLUIDA_COM_ALERTAS
            if importacao.alertas_relevantes
            else Importacao.Status.CONCLUIDA
        )
    importacao.save(update_fields=["quantidade_nao_associada", "status"])

    return {
        "importacao": importacao,
        "pendencia": pendencia,
        "medicamento_criado": criado,
        "saldo_criado": saldo_criado,
        "saldo": saldo,
    }


def persist_inventory_import(*, parsed_data, user, nome_arquivo, reimportar=False):
    """Persist a new inventory or atomically replace an existing one."""
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
        ups, ups_criada = _get_or_create_ups(ups_data)
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

        importacao = (
            Importacao.objects.select_for_update()
            .filter(
                competencia=competencia,
                ups=ups,
                tipo_relatorio=report_type,
            )
            .first()
        )
        reimportacao = importacao is not None

        if importacao is not None and not reimportar:
            raise DuplicateInventoryImportError(
                "Ja existe uma importacao para esta competencia, UPS e tipo de relatorio."
            )
        if (
            importacao is not None
            and importacao.hash_arquivo == file_hash
            and not reimportar
        ):
            raise SameInventoryFileError(
                "Este mesmo arquivo ja foi processado para esta competencia e UPS."
            )
        if importacao is None and reimportar:
            raise ReimportationTargetNotFoundError(
                "Nao existe importacao para substituir com a competencia e UPS do arquivo."
            )

        if importacao is not None:
            Estoque.objects.filter(importacao=importacao).delete()
        else:
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
        _raise_on_duplicate_records(
            parsed_data.get("records", []),
            invalid_lines=invalid_lines,
            report_type=report_type,
        )
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
                _enrich_medicine_from_inventory(
                    medicine=medicine,
                    medicine_data=medicine_data,
                    subgroup=subgroup,
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

        if reimportacao and stock_count == 0:
            raise InventoryPersistenceError(
                "A reimportacao nao gerou registros de estoque validos."
            )

        has_warnings = any(
            item.get("severity") == "warning" for item in parser_errors
        )
        import_status = Importacao.Status.CONCLUIDA
        if invalid_lines or service_errors:
            import_status = Importacao.Status.CONCLUIDA_PARCIAL
        elif has_warnings or divergencias:
            import_status = Importacao.Status.CONCLUIDA_COM_ALERTAS

        if reimportacao:
            importacao.nome_arquivo = nome_arquivo
            importacao.hash_arquivo = file_hash
            importacao.tipo_relatorio = report_type
            importacao.data_importacao = timezone.now()
            importacao.status = import_status
            importacao.usuario = user
            importacao.competencia = competencia
            importacao.ups = ups
            importacao.save(
                update_fields=[
                    "nome_arquivo",
                    "hash_arquivo",
                    "tipo_relatorio",
                    "data_importacao",
                    "status",
                    "usuario",
                    "competencia",
                    "ups",
                ]
            )
        elif importacao.status != import_status:
            importacao.status = import_status
            importacao.save(update_fields=["status"])

        return {
            "importacao": importacao,
            "importacao_criada": not reimportacao,
            "reimportacao": reimportacao,
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


def persist_stock_import(*, parsed_data, user, nome_arquivo, reimportar=False):
    """Persist a Consulta de Estoque separately from lot-level inventory."""
    with transaction.atomic():
        _validate_import_context(parsed_data, user, nome_arquivo)
        metadata = parsed_data["metadata"]
        competencia_data = metadata["competencia"]
        ups_data = metadata["ups"]
        report_type = parsed_data["tipo_relatorio"]
        file_hash = parsed_data["hash_arquivo"]
        divergencias = []
        competencia, competencia_criada = Competencia.objects.get_or_create(
            ano=competencia_data["ano"], mes=competencia_data["mes"]
        )
        ups, ups_criada = _resolve_stock_ups(ups_data)
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

        importacao = (
            Importacao.objects.select_for_update()
            .filter(competencia=competencia, ups=ups, tipo_relatorio=report_type)
            .first()
        )
        reimportacao = importacao is not None
        if importacao is not None and not reimportar:
            raise DuplicateInventoryImportError(
                "Ja existe uma importacao para esta competencia, UPS e tipo de relatorio."
            )
        if importacao is None and reimportar:
            raise ReimportationTargetNotFoundError(
                "Nao existe importacao para substituir com a competencia e UPS do arquivo."
            )

        if importacao is not None:
            SaldoEstoque.objects.filter(importacao=importacao).delete()
            importacao.pendencias.all().delete()
        else:
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

        parser_errors = list(parsed_data.get("inconsistencies", []))
        records = list(parsed_data.get("records", []))
        for issue in parser_errors:
            if issue.get("type") != "invalid_material" or not issue.get("fallback"):
                continue
            fallback = issue["fallback"]
            matches = _find_existing_medicine_matches(
                descricao=fallback["descricao"], unidade=fallback["unidade"]
            )
            if len(matches) != 1:
                continue
            medicine = matches[0]
            records.append({
                "line": issue["line"],
                "medicamento": {
                    "codigo_gmus": medicine.codigo_gmus,
                    "descricao": medicine.descricao,
                    "descricao_original": medicine.descricao,
                    "unidade": medicine.unidade,
                    "subgrupo": None,
                },
                "quantidade": fallback["quantidade"],
                "lote": None,
                "raw": issue.get("raw"),
            })
            issue["severity"] = "info"
            issue["type"] = "material_reconciliado"
            issue["message"] = "Material sem codigo foi associado a um medicamento cadastrado por correspondencia unica."
            issue["codigo_gmus"] = medicine.codigo_gmus
        for issue in parser_errors:
            fallback = issue.get("fallback") or {}
            if (
                issue.get("severity", "error") == "error"
                and fallback
                and fallback.get("quantidade") == 0
            ):
                issue["severity"] = "info"
                issue["type"] = "material_sem_saldo"
                issue["message"] = (
                    "Material sem codigo foi ignorado porque a quantidade informada e zero."
                )
        quantidade_nao_associada = sum(
            item.get("fallback", {}).get("quantidade", 0)
            for item in parser_errors
            if item.get("severity", "error") == "error" and item.get("fallback")
        )
        pendencias_corrigiveis = [
            item
            for item in parser_errors
            if item.get("severity", "error") == "error"
            and item.get("type") == "invalid_material"
            and item.get("fallback")
            and item["fallback"].get("quantidade", 0) > 0
            and item.get("line") is not None
        ]
        invalid_lines = {
            item.get("line")
            for item in parser_errors
            if item.get("severity", "error") == "error" and item.get("line") is not None
        }
        _raise_on_duplicate_records(
            parsed_data.get("records", []),
            invalid_lines=invalid_lines,
            report_type=report_type,
        )
        service_errors = []
        created_medicines = set()
        reused_medicines = set()
        reported_divergences = set()
        saldo_count = 0
        ignored_count = len(
            invalid_lines
            - {record.get("line") for record in records}
        )

        for record in records:
            line = record.get("line")
            if line in invalid_lines:
                ignored_count += 1
                continue
            try:
                medicine_data = _validate_record(record)
                subgroup = _get_or_create_subgroup(medicine_data.get("subgrupo"))
                if report_type == REPORT_TYPE_INVENTORY:
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
            SaldoEstoque.objects.create(
                medicamento=medicine,
                ups=ups,
                competencia=competencia,
                importacao=importacao,
                quantidade=record["quantidade"],
            )
            saldo_count += 1

        if reimportacao and saldo_count == 0:
            raise InventoryPersistenceError(
                "A reimportacao nao gerou registros de saldo validos."
            )

        PendenciaImportacao.objects.bulk_create(
            [
                PendenciaImportacao(
                    importacao=importacao,
                    linha=item["line"],
                    descricao=item["fallback"].get("descricao", ""),
                    unidade=item["fallback"].get("unidade", ""),
                    quantidade=item["fallback"]["quantidade"],
                    raw=str(item.get("raw") or ""),
                )
                for item in pendencias_corrigiveis
            ]
        )
        erros_nao_corrigiveis = (
            sum(
                1
                for item in parser_errors
                if item.get("severity", "error") == "error"
            )
            - len(pendencias_corrigiveis)
            + len(service_errors)
        )

        has_warnings = any(
            item.get("severity") == "warning" for item in parser_errors
        )
        alertas_relevantes = sum(
            1 for item in parser_errors if item.get("severity") == "warning"
        ) + len(divergencias)
        import_status = Importacao.Status.CONCLUIDA
        if invalid_lines or service_errors:
            import_status = Importacao.Status.CONCLUIDA_PARCIAL
        elif has_warnings or divergencias:
            import_status = Importacao.Status.CONCLUIDA_COM_ALERTAS

        importacao.nome_arquivo = nome_arquivo
        importacao.hash_arquivo = file_hash
        importacao.data_importacao = timezone.now()
        importacao.status = import_status
        importacao.quantidade_nao_associada = quantidade_nao_associada
        importacao.erros_nao_corrigiveis = erros_nao_corrigiveis
        importacao.alertas_relevantes = alertas_relevantes
        importacao.usuario = user
        importacao.save(
            update_fields=[
                "nome_arquivo",
                "hash_arquivo",
                "data_importacao",
                "status",
                "quantidade_nao_associada",
                "erros_nao_corrigiveis",
                "alertas_relevantes",
                "usuario",
            ]
        )
        return {
            "importacao": importacao,
            "importacao_criada": not reimportacao,
            "reimportacao": reimportacao,
            "competencia_criada": competencia_criada,
            "ups_criada": ups_criada,
            "registros_recebidos": len(records),
            "registros_processados": saldo_count,
            "registros_ignorados": ignored_count,
            "medicamentos_criados": len(created_medicines),
            "medicamentos_reutilizados": len(reused_medicines),
            "lotes_criados": 0,
            "lotes_reutilizados": 0,
            "estoques_criados": saldo_count,
            "saldos_criados": saldo_count,
            "quantidade_nao_associada": quantidade_nao_associada,
            "divergencias": divergencias,
            "erros": parser_errors + service_errors,
        }


def persist_movement_import(*, parsed_data, user, nome_arquivo, reimportar=False):
    """Persist one monthly synthetic movement report per medicine and UPS."""
    with transaction.atomic():
        _validate_import_context(parsed_data, user, nome_arquivo)
        metadata = parsed_data["metadata"]
        competencia_data = metadata["competencia"]
        ups_data = metadata["ups"]
        report_type = parsed_data["tipo_relatorio"]
        file_hash = parsed_data["hash_arquivo"]
        competencia, competencia_criada = Competencia.objects.get_or_create(
            ano=competencia_data["ano"], mes=competencia_data["mes"]
        )
        ups, ups_criada = _resolve_stock_ups(ups_data)
        importacao = Importacao.objects.select_for_update().filter(
            competencia=competencia, ups=ups, tipo_relatorio=report_type
        ).first()
        reimportacao = importacao is not None
        if importacao is not None and not reimportar:
            raise DuplicateInventoryImportError("Ja existe uma importacao para esta competencia, UPS e tipo de relatorio.")
        if (
            importacao is not None
            and importacao.hash_arquivo == file_hash
            and not reimportar
        ):
            raise SameInventoryFileError("Este mesmo arquivo ja foi processado para esta competencia e UPS.")
        if importacao is None and reimportar:
            raise ReimportationTargetNotFoundError("Nao existe importacao para substituir com a competencia e UPS do arquivo.")
        if importacao is not None:
            MovimentacaoEstoque.objects.filter(importacao=importacao).delete()
        else:
            importacao = Importacao.objects.create(
                nome_arquivo=nome_arquivo, hash_arquivo=file_hash,
                tipo_relatorio=report_type, data_importacao=timezone.now(),
                status=Importacao.Status.CONCLUIDA, usuario=user,
                competencia=competencia, ups=ups,
            )

        parser_errors = list(parsed_data.get("inconsistencies", []))
        invalid_lines = {
            item.get("line") for item in parser_errors
            if item.get("severity", "error") == "error" and item.get("line") is not None
        }
        _raise_on_duplicate_records(
            parsed_data.get("records", []),
            invalid_lines=invalid_lines,
            report_type=report_type,
        )
        created_medicines = set()
        reused_medicines = set()
        count = 0
        start_date = date.fromisoformat(metadata["data_inicial"])
        end_date = date.fromisoformat(metadata["data_final"])
        for record in parsed_data.get("records", []):
            if record.get("line") in invalid_lines:
                continue
            medicine_data = _validate_record(record)
            medicine, created = Medicamento.objects.get_or_create(
                codigo_gmus=medicine_data["codigo_gmus"],
                defaults={"descricao": medicine_data["descricao"], "unidade": medicine_data["unidade"]},
            )
            _ensure_manipulated_classification(medicine=medicine, description=medicine_data["descricao"])
            if created:
                created_medicines.add(medicine.pk)
            else:
                reused_medicines.add(medicine.pk)
            MovimentacaoEstoque.objects.create(
                importacao=importacao, medicamento=medicine, ups=ups,
                competencia=competencia, data_inicial=start_date, data_final=end_date,
                **record["movimentacoes"],
            )
            count += 1
        if not count:
            raise InventoryPersistenceError("A importacao nao gerou movimentacoes validas.")
        importacao.nome_arquivo = nome_arquivo
        importacao.hash_arquivo = file_hash
        importacao.data_importacao = timezone.now()
        if invalid_lines:
            importacao.status = Importacao.Status.CONCLUIDA_PARCIAL
        elif any(
            item.get("severity") == "warning" for item in parser_errors
        ):
            importacao.status = Importacao.Status.CONCLUIDA_COM_ALERTAS
        else:
            importacao.status = Importacao.Status.CONCLUIDA
        importacao.usuario = user
        importacao.save(update_fields=["nome_arquivo", "hash_arquivo", "data_importacao", "status", "usuario"])
        return {
            "importacao": importacao, "importacao_criada": not reimportacao,
            "reimportacao": reimportacao, "competencia_criada": competencia_criada,
            "ups_criada": ups_criada, "registros_recebidos": len(parsed_data.get("records", [])),
            "registros_processados": count, "registros_ignorados": len(invalid_lines),
            "medicamentos_criados": len(created_medicines), "medicamentos_reutilizados": len(reused_medicines),
            "lotes_criados": 0, "lotes_reutilizados": 0, "estoques_criados": 0,
            "saldos_criados": 0, "divergencias": [], "erros": parser_errors,
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
    report_type = parsed_data.get("tipo_relatorio")
    if (
        not ups.get("id_unidade_gmus")
        or not ups.get("nome")
        or (
            report_type not in (REPORT_TYPE_STOCK, REPORT_TYPE_MOVEMENT)
            and not ups.get("codigo_gmus")
        )
    ):
        raise InventoryPersistenceError("UPS ausente nos metadados.")
    if not report_type:
        raise InventoryPersistenceError("Tipo de relatorio ausente no parser.")
    file_hash = parsed_data.get("hash_arquivo") or ""
    if len(file_hash) != 64:
        raise InventoryPersistenceError("Hash SHA-256 do arquivo invalido.")
    try:
        int(file_hash, 16)
    except ValueError as error:
        raise InventoryPersistenceError("Hash SHA-256 do arquivo invalido.") from error


def _find_existing_medicine_matches(*, descricao, unidade):
    normalized_description = _normalize_match_text(descricao)
    normalized_unit = _normalize_match_text(unidade)
    exact_matches = []
    prefix_matches = []
    for medicine in Medicamento.objects.all().only("id", "codigo_gmus", "descricao", "unidade"):
        normalized_medicine_description = _normalize_match_text(medicine.descricao)
        if normalized_unit and _normalize_match_text(medicine.unidade) != normalized_unit:
            continue
        if normalized_medicine_description == normalized_description:
            exact_matches.append(medicine)
        elif (
            normalized_medicine_description.startswith(normalized_description)
            or normalized_description.startswith(normalized_medicine_description)
        ):
            prefix_matches.append(medicine)
    if exact_matches:
        return exact_matches
    if len(prefix_matches) == 1:
        return prefix_matches
    return []


def _get_or_create_ups(ups_data):
    return Ups.objects.get_or_create(
        codigo_gmus=ups_data["codigo_gmus"],
        id_unidade_gmus=ups_data["id_unidade_gmus"],
        defaults={"nome": ups_data["nome"]},
    )


def _raise_on_duplicate_records(records, *, invalid_lines, report_type):
    seen = {}
    duplicates = []
    for record in records:
        if record.get("line") in invalid_lines:
            continue
        medicine = record.get("medicamento") or {}
        code = medicine.get("codigo_gmus")
        if not code:
            continue
        if report_type == REPORT_TYPE_STOCK:
            key = (code,)
        else:
            lot = record.get("lote") or {}
            key = (code, lot.get("codigo_lote"), lot.get("validade"))
        if key in seen:
            duplicates.append((seen[key], record.get("line")))
        else:
            seen[key] = record.get("line")
    if duplicates:
        lines = ", ".join(
            f"{first}/{second}" for first, second in duplicates[:5]
        )
        raise InventoryPersistenceError(
            "O arquivo possui registros duplicados para a mesma chave "
            f"de estoque (linhas {lines}). Corrija o relatório antes de importar."
        )


def _resolve_stock_ups(ups_data):
    """Resolve Consulta de Estoque UPS metadata, including exports without code."""
    unit_id = ups_data.get("id_unidade_gmus")
    codigo_gmus = ups_data.get("codigo_gmus")
    if codigo_gmus:
        return Ups.objects.get_or_create(
            codigo_gmus=codigo_gmus,
            id_unidade_gmus=unit_id,
            defaults={"nome": ups_data["nome"]},
        )

    matches = list(
        Ups.objects.filter(id_unidade_gmus=unit_id).order_by("id")[:2]
    )
    if len(matches) != 1:
        raise InventoryPersistenceError(
            "Nao foi possivel identificar a UPS: o relatorio nao informa o codigo G-MUS "
            "e o id_unidade_gmus nao corresponde a uma unica UPS cadastrada."
        )
    return matches[0], False


def _normalize_match_text(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", normalized.casefold())


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
    ]
    if subgroup is not None:
        comparisons.append(
            (
                "medicamento_subgrupo",
                medicine.subgrupo_gmus_id,
                subgroup.pk,
            )
        )
    for divergence_type, stored_value, report_value in comparisons:
        key = (medicine.pk, divergence_type, str(report_value))
        equivalent_text = (
            divergence_type in {"medicamento_descricao", "medicamento_unidade"}
            and _normalize_match_text(stored_value) == _normalize_match_text(report_value)
        )
        if stored_value == report_value or equivalent_text or key in reported:
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


def _enrich_medicine_from_inventory(*, medicine, medicine_data, subgroup):
    updates = []
    if not medicine.descricao and medicine_data.get("descricao"):
        medicine.descricao = medicine_data["descricao"]
        updates.append("descricao")
    if not medicine.unidade and medicine_data.get("unidade"):
        medicine.unidade = medicine_data["unidade"]
        updates.append("unidade")
    if medicine.subgrupo_gmus_id is None and subgroup is not None:
        medicine.subgrupo_gmus = subgroup
        updates.append("subgrupo_gmus")
    if updates:
        medicine.save(update_fields=updates)


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
