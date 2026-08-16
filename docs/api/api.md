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
- `/api/localizacoes-estoque/`
- `/api/lotes/`
- `/api/estoques/`

O endpoint direto abaixo nao existe:

- `/api/importacoes/`

A importacao e exposta apenas de forma aninhada em estoque, para preservar a rastreabilidade do registro consultado.

## Metodos permitidos

Os endpoints administrativos atuais sao somente leitura.

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
- `LocalizacaoEstoqueSerializer`

Serializers de `medicamentos`:

- `SubgrupoGmusSerializer`
- `PrincipioAtivoSerializer`
- `ClassificacaoSerializer`
- `MedicamentoSerializer`

Serializers de `estoques`:

- `LoteSerializer`
- `EstoqueSerializer`

Serializer de `importacoes`:

- `ImportacaoSerializer`

`ImportacaoSerializer` nao possui endpoint direto nesta etapa. Ele e usado dentro de `EstoqueSerializer` para indicar a importacao responsavel pelo registro de estoque.

## Rastreabilidade em estoque

A representacao de estoque inclui dados aninhados de:

- medicamento;
- UPS;
- competencia;
- lote, quando houver;
- localizacao;
- importacao responsavel;
- quantidade.

A importacao aninhada inclui:

- arquivo importado;
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
- importacao de CSV;
- reimportacao;
- calculos de estoque;
- dashboard;
- endpoints de escrita;
- regras definitivas de disponibilidade publica.

## Separacao futura

O projeto possui dois contextos de acesso:

- modulo administrativo, autenticado;
- modulo publico, sem autenticacao.

A API atual cobre apenas a consulta administrativa inicial. A API publica devera ser criada separadamente, respeitando as regras de informacao publica: nao expor quantidade exata, lote, validade, localizacao ou informacoes administrativas internas.
