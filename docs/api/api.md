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

O endpoint `/api/publico/medicamentos/` usa `AllowAny` e nao exige autenticacao.

## Consulta publica de medicamentos

Rota:

```text
GET /api/publico/medicamentos/
```

A rota aceita o parametro opcional `search`, com busca parcial e sem diferenciar
maiusculas de minusculas em descricao e codigo G-MUS:

```text
GET /api/publico/medicamentos/?search=dipirona
```

Cada apresentacao e retornada separadamente. A resposta publica contem somente:

- `codigo_gmus`;
- `descricao`;
- `unidade`;
- `disponibilidade`.

Nao sao expostos UPS, quantidades, lote, validade, competencia, importacao, usuario,
subgrupo, principios ativos ou classificacoes.

A disponibilidade publica e calculada internamente de forma consolidada a partir dos
estoques das UPS configuradas
para compor o estoque convencional, sem revelar UPS de origem ou quantidades internas.

A competencia valida sera a competencia completa mais recente. Uma competencia somente
sera completa quando todas as UPS configuradas como participantes tiverem importacao de
inventario `concluida` ou `concluida_com_alertas`. Se a mais recente estiver incompleta,
sera usada a completa anterior; sem competencia completa, medicamentos sem a tag ativa
`MANIPULADO` terao `Disponibilidade não informada`.

O campo `disponibilidade` segue esta ordem:

1. com tag ativa `MANIPULADO`, independentemente do saldo:
   `Disponível sob manipulação, confirmar disponibilidade`;
2. sem tag ativa `MANIPULADO` e sem competência completa:
   `Disponibilidade não informada`;
3. sem tag ativa `MANIPULADO`, com competência completa e estoque convencional
   positivo: `Disponível`;
4. sem tag ativa `MANIPULADO`, com competência completa e sem estoque convencional
   positivo: `Indisponível`.

A tag, e nao saldo, lote ou historico da UPS de manipulacao, determina a mensagem
especial. Todo medicamento com a tag ativa recebe essa mensagem, mesmo com estoque
convencional positivo ou estoque registrado igual a zero.

Exemplo de item publico:

```json
{
  "codigo_gmus": "115.1",
  "descricao": "DIPIRONA / 500MG",
  "unidade": "COMPR",
  "disponibilidade": "Disponível"
}
```

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

### Pesquisa de medicamentos

O endpoint administrativo de medicamentos aceita o parametro opcional `search`:

```text
GET /api/medicamentos/?search=dipirona
```

A pesquisa e parcial e nao diferencia maiusculas de minusculas. Os campos pesquisados
sao `Medicamento.descricao` e `Medicamento.codigo_gmus`.

Cada apresentacao permanece como um medicamento separado na resposta, preservando seu
codigo G-MUS, descricao e unidade. Uma consulta sem `search` continua retornando a
listagem administrativa normal.

### Filtros administrativos

Os filtros usam igualdade exata e podem ser combinados na mesma consulta.

Medicamentos:

- `subgrupo`: ID de `SubgrupoGmus`.

Estoques:

- `ups`: ID de `Ups`;
- `ups_codigo`: codigo G-MUS de `Ups`;
- `competencia`: ID de `Competencia`;
- `subgrupo`: ID do `SubgrupoGmus` associado ao medicamento do estoque.

Exemplos:

```text
GET /api/medicamentos/?subgrupo=10
GET /api/medicamentos/?search=dipirona&subgrupo=10
GET /api/estoques/?ups=1
GET /api/estoques/?ups_codigo=2780046
GET /api/estoques/?competencia=8
GET /api/estoques/?ups=1&competencia=8&subgrupo=10
```

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

Os status de sucesso seguem estas regras:

- `concluida`: sem warnings ou registros rejeitados;
- `concluida_com_alertas`: com warnings, mas sem registros rejeitados;
- `concluida_parcial`: com uma ou mais linhas ou registros rejeitados.

Uma `Qtde Virt.` negativa e retornada como erro de linha, nao cria estoque para a linha
e torna a importacao `concluida_parcial` quando ainda houver registros processaveis.

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

- filtros administrativos adicionais;
- paginacao customizada;
- reimportacao;
- calculos de estoque;
- dashboard;
- outros endpoints de escrita.

## Separacao futura

O projeto possui dois contextos de acesso:

- modulo administrativo, autenticado;
- modulo publico, sem autenticacao.

A API publica inicial oferece somente a pesquisa de medicamentos e permanece separada
dos endpoints administrativos. Ela nao expoe quantidade, lote, validade, UPS de origem
ou outras informacoes administrativas internas.
