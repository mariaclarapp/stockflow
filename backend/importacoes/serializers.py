from pathlib import Path

from rest_framework import serializers

from core.serializers import CompetenciaSerializer, UpsSerializer

from .models import Importacao, MovimentacaoEstoque, PendenciaImportacao


class InventoryUploadSerializer(serializers.Serializer):
    arquivo = serializers.FileField(allow_empty_file=False, write_only=True)
    reimportar = serializers.BooleanField(default=False, required=False, write_only=True)

    def validate_arquivo(self, arquivo):
        if Path(arquivo.name).suffix.lower() != ".csv":
            raise serializers.ValidationError(
                "Envie um arquivo com extensao .csv."
            )
        return arquivo


class PendenciaImportacaoSerializer(serializers.ModelSerializer):
    medicamento = serializers.SerializerMethodField()

    def get_medicamento(self, pendencia):
        if pendencia.medicamento_id is None:
            return None
        return {
            "id": pendencia.medicamento_id,
            "codigo_gmus": pendencia.medicamento.codigo_gmus,
            "descricao": pendencia.medicamento.descricao,
            "unidade": pendencia.medicamento.unidade,
        }

    class Meta:
        model = PendenciaImportacao
        fields = [
            "id",
            "linha",
            "tipo",
            "descricao",
            "unidade",
            "quantidade",
            "status",
            "medicamento",
            "resolvida_em",
        ]


class ResolverPendenciaImportacaoSerializer(serializers.Serializer):
    codigo_gmus = serializers.CharField(max_length=50, trim_whitespace=True)


class ImportacaoSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()
    competencia = CompetenciaSerializer(read_only=True)
    ups = UpsSerializer(read_only=True)
    pendencias = serializers.SerializerMethodField()

    def get_usuario(self, importacao):
        return importacao.usuario.get_full_name() or importacao.usuario.get_username()

    def get_pendencias(self, importacao):
        pendencias = getattr(importacao, "pendencias_abertas_prefetch", None)
        if pendencias is None:
            pendencias = importacao.pendencias.filter(
                status=PendenciaImportacao.Status.PENDENTE
            ).select_related("medicamento")
        return PendenciaImportacaoSerializer(pendencias, many=True).data

    class Meta:
        model = Importacao
        fields = [
            "id",
            "nome_arquivo",
            "hash_arquivo",
            "tipo_relatorio",
            "data_importacao",
            "status",
            "quantidade_nao_associada",
            "erros_nao_corrigiveis",
            "alertas_relevantes",
            "usuario",
            "competencia",
            "ups",
            "pendencias",
        ]


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    medicamento = serializers.StringRelatedField(read_only=True)
    ups = UpsSerializer(read_only=True)
    competencia = CompetenciaSerializer(read_only=True)
    importacao = ImportacaoSerializer(read_only=True)

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            "id", "medicamento", "ups", "competencia", "importacao",
            "data_inicial", "data_final", "saida", "devolucao_saida",
            "compra", "transferencia_devolucao", "transferencia_entrada",
            "transferencia_saida", "acerto_entrada", "acerto_saida", "saldo_atual",
        ]
