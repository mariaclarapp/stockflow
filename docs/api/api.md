# API - StockFlow

Este documento registra o estado atual implementado da API do StockFlow.

## Tecnologia

A API inicial foi implementada com Django REST Framework no backend Django.

O prefixo atual das rotas e:

```text
/api/
```

## Autenticacao e permissoes

Os endpoints administrativos utilizam a configuracao padrao definida em `REST_FRAMEWORK`.

Atualmente, a permissao padrao exige usuario autenticado:

```text
rest_framework.permissions.IsAuthenticated
```

Nao existem endpoints publicos anonimos implementados nesta etapa.

## Endpoints administrativos de leitura

Os endpoints atuais usam `ReadOnlyModelViewSet`, permitindo consulta por lista e detalhe.

Rotas disponiveis:

- `/api/subgrupos-gmus/`
- `/api/principios-ativos/`
- `/api/classificacoes/`
- `/api/medicamentos/`
- `/api/ups/`
- `/api/competencias/`
- `/api/lotes/`
- `/api/estoques/`

O endpoint direto abaixo nao existe:

- `/api/importacoes/`
- `/api/localizacoes-estoque/`

Nao existe uma listagem direta de importacoes. A importacao e exposta de forma aninhada
em estoque, para preservar a rastreabilidade do registro consultado, e possui uma rota
administrativa especifica para envio de inventario.

## Upload administrativo de inventario

Rota:

```text
POST /api/importacoes/inventario/
```

A rota exige usuario autenticado e recebe `multipart/form-data`. O arquivo deve ser
enviado no campo `arquivo`, possuir conteudo e usar a extensao `.csv`.

Exemplo do corpo:

```text
Content-Type: multipart/form-data
arquivo: inventario.csv
```

O endpoint executa o parser de inventario e usa o nome original e o hash SHA-256 do
arquivo na persistencia. Erros `error` associados a uma linha rejeitam somente aquela
linha. Erros globais sem linha, ou um arquivo sem registros processaveis, bloqueiam a
importacao antes da persistencia.

Uma resposta de sucesso usa HTTP `201` e possui esta estrutura:

```json
{
  "importacao_id": 1,
  "status": "concluida",
  "tipo_relatorio": "inventario",
  "hash_arquivo": "sha256-do-arquivo",
  "competencia": {"ano": 2026, "mes": 8},
  "ups": {"codigo_gmus": "1234567", "nome": "UPS DO RELATORIO"},
  "registros_processados": 1,
  "registros_ignorados": 0,
  "medicamentos_criados": 1,
  "medicamentos_reutilizados": 0,
  "lotes_criados": 1,
  "lotes_reutilizados": 0,
  "estoques_criados": 1,
  "divergencias": [],
  "warnings": [],
  "erros": []
}
```

Os itens de divergencia, warning ou erro nao incluem as linhas brutas do CSV.

Respostas de erro:

- `400 Bad Request`: arquivo ausente, extensao invalida, falha de parsing ou contexto invalido;
- `401 Unauthorized` ou `403 Forbidden`: usuario nao autenticado;
- `409 Conflict`: ja existe importacao para a mesma competencia, UPS e tipo de relatorio;
- `422 Unprocessable Entity`: erro global do parser ou ausencia de registros processaveis;
- `500 Internal Server Error`: falha inesperada, com mensagem generica e rollback da persistencia.

## Metodos permitidos

Os endpoints administrativos de consulta sao somente leitura. A unica operacao de
escrita exposta nesta etapa e o `POST /api/importacoes/inventario/`.

Permitidos:

- `GET`
- `HEAD`
- `OPTIONS`

Nao permitidos:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`

## Serializers existentes

Serializers de `core`:

- `UpsSerializer`
- `CompetenciaSerializer`

Serializers de `medicamentos`:

- `SubgrupoGmusSerializer`
- `PrincipioAtivoSerializer`
- `ClassificacaoSerializer`
- `MedicamentoSerializer`

Serializers de `estoques`:

- `LoteSerializer`
- `EstoqueSerializer`

Serializer de `importacoes`:

- `InventoryUploadSerializer`
- `ImportacaoSerializer`

`ImportacaoSerializer` nao possui endpoint direto nesta etapa. Ele e usado dentro de `EstoqueSerializer` para indicar a importacao responsavel pelo registro de estoque.

## Rastreabilidade em estoque

A representacao de estoque inclui dados aninhados de:

- medicamento;
- UPS;
- competencia;
- lote, quando houver;
- importacao responsavel;
- quantidade.

A UPS representa a localizacao e a origem do estoque no relatorio de inventario. Nao existe serializer ou campo separado de localizacao.

A importacao aninhada inclui:

- arquivo importado;
- hash SHA-256 do arquivo;
- tipo de relatorio;
- data da importacao;
- status;
- usuario responsavel;
- competencia;
- UPS.

## Ainda nao implementado

Nao foram implementados nesta etapa:

- endpoints publicos anonimos;
- filtros;
- paginacao customizada;
- reimportacao;
- calculos de estoque;
- dashboard;
- outros endpoints de escrita;
- regras definitivas de disponibilidade publica.

## Separacao futura

O projeto possui dois contextos de acesso:

- modulo administrativo, autenticado;
- modulo publico, sem autenticacao.

A API atual cobre apenas a consulta administrativa inicial. A API publica devera ser criada separadamente, respeitando as regras de informacao publica: nao expor quantidade exata, lote, validade, UPS de origem ou informacoes administrativas internas.
