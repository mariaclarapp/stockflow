# API - StockFlow

O contrato da analise administrativa esta detalhado em `analise-consumo.md`.

## Escopo ativo de importacao

As APIs ativas de importacao sao `POST /api/importacoes/estoque/` e
`POST /api/importacoes/movimentacoes/`. O inventario detalhado nao faz parte do
contrato ativo. A validacao usa somente estoque e movimentacoes.

Antes de persistir, `POST /api/importacoes/previsualizar/` identifica o tipo, a
competencia, a UPS, a quantidade de registros e os problemas globais do CSV sem gravar
dados. A exclusao exige `{ "confirmar": true }` e gera uma auditoria imutavel.

Este documento registra o estado atual implementado da API do StockFlow.

## Tecnologia

A API inicial foi implementada com Django REST Framework no backend Django.

O prefixo atual das rotas e:

```text
/api/
```

## Autenticacao e permissoes

Os endpoints administrativos utilizam a configuracao padrao definida em `REST_FRAMEWORK`.

Atualmente, a permissao padrao exige usuario Django ativo e administrativo
(`is_staff=True`):

```text
rest_framework.permissions.IsAdminUser
```

O endpoint `/api/publico/medicamentos/` usa `AllowAny` e nao exige autenticacao.
O endpoint `/api/auth/csrf/` tambem permanece anonimo. `is_superuser` nao e exigido
para acessar o modulo administrativo.

O fluxo administrativo usa sessao e cookies nativos do Django. Nao sao utilizados
JWT, tokens proprios ou senhas fora do mecanismo de autenticacao do framework.

O cadastro e a listagem segura de funcionarios administrativos possuem endpoint proprio,
restrito a superusers. O Django Admin permanece disponivel como mecanismo complementar;
usuarios staff comuns continuam autorizados a operar o StockFlow, mas nao administram
contas.

## Autenticacao administrativa por sessao

O frontend deve enviar requisicoes com credenciais, por exemplo usando
`credentials: "include"`. A origem permitida e configurada por `FRONTEND_URL`; nenhuma
URL de producao e fixada no codigo.

### Obter CSRF

```text
GET /api/auth/csrf/
```

O endpoint e anonimo, cria o cookie `csrftoken` e retorna o token que deve ser enviado
no cabecalho `X-CSRFToken` das requisicoes de escrita:

```json
{"csrfToken": "token-csrf"}
```

### Login

```text
POST /api/auth/login/
Content-Type: application/json
X-CSRFToken: token-csrf

{"username": "usuario", "password": "senha"}
```

Credenciais validas criam a sessao do Django e retornam somente:

```json
{
  "user": {
    "id": 1,
    "username": "usuario",
    "is_staff": true,
    "is_superuser": false
  }
}
```

Credenciais invalidas, usuarios inativos e usuarios sem `is_staff=True` recebem a
mesma resposta generica, sem indicar o motivo da recusa.

### Usuario atual

```text
GET /api/auth/me/
```

Exige uma sessao valida de usuario ativo com `is_staff=True` e retorna diretamente
`id`, `username`, `is_staff` e `is_superuser`.

### Logout

```text
POST /api/auth/logout/
X-CSRFToken: token-csrf
```

Exige sessao administrativa autorizada e protecao CSRF, encerra apenas a sessao atual
e retorna HTTP `204`.

### Funcionarios administrativos

```text
GET /api/usuarios/funcionarios/
POST /api/usuarios/funcionarios/
Content-Type: application/json
X-CSRFToken: token-csrf
```

As duas operacoes exigem `is_superuser=True`. O `POST` recebe `nome`, `username`,
`password` e `password_confirmation`. A senha passa pelos validadores nativos do Django,
nao e devolvida pela API e e armazenada somente como hash. A conta criada recebe
`is_active=True`, `is_staff=True` e `is_superuser=False`.

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

O campo `descricao` preserva o medicamento conforme identificado pelo G-MUS, incluindo
nome ou combinacao, apresentacao/dosagem, concentracao e, quando presentes no relatorio,
volume e forma. `unidade` complementa essa apresentacao. O contrato publico nao depende
nem expoe uma entidade separada de principio ativo.

Nao sao expostos UPS, quantidades, lote, validade, competencia, importacao, usuario,
subgrupo, principios ativos ou classificacoes.

A consulta publica lista somente medicamentos presentes nos registros validos de estoque
da competencia completa mais recente. A disponibilidade e calculada internamente de
forma consolidada a partir das UPS configuradas para compor o estoque convencional, sem
revelar UPS de origem ou quantidades internas.

A competencia valida sera a competencia completa mais recente. Uma competencia somente
sera completa quando todas as UPS configuradas como participantes tiverem importacao de
Consulta de Estoque `concluida` ou `concluida_com_alertas`. Se a mais recente estiver incompleta,
sera usada a completa anterior. Sem competencia completa, o endpoint retorna uma lista
vazia; medicamentos que nao constam nos estoques validos da competencia tambem nao sao
exibidos.

O campo `disponibilidade` segue esta ordem:

1. com tag ativa `MANIPULADO`, independentemente do saldo:
   `Disponível sob manipulação, confirmar disponibilidade`;
2. sem tag ativa `MANIPULADO`, com competência completa e estoque convencional
   positivo: `Disponível`;
3. sem tag ativa `MANIPULADO`, com competência completa e sem estoque convencional
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

Os endpoints administrativos de medicamentos, subgrupos, princípios ativos, UPS,
competências, lotes e estoques permanecem somente leitura. Classificações possuem as
operações administrativas específicas descritas abaixo.

Rotas disponiveis:

- `/api/subgrupos-gmus/`
- `/api/principios-ativos/`
- `/api/classificacoes/`
- `/api/medicamentos/`
- `/api/ups/`
- `/api/competencias/`
- `/api/lotes/`
- `/api/estoques/`
- `/api/saldos-estoque/`
- `/api/movimentacoes/`
- `/api/estoques/comparacao/`
- `/api/estoques/validacao-movimentacoes/`

## Importacao de relatorios

Os uploads administrativos exigem sessão de usuário `is_staff` e proteção CSRF:

- `POST /api/importacoes/estoque/` — saldo total da Consulta de Estoque;
- `POST /api/importacoes/movimentacoes/` — movimentações sintéticas mensais;

A Consulta de Estoque aceita as duas formas de identificação exportadas pelo G-MUS:
com `UPS: nome / codigo_gmus (id_unidade_gmus)` ou somente `UPS: nome
(id_unidade_gmus)`. Quando o código não estiver presente, o backend somente associa o
arquivo se o identificador da unidade corresponder a uma única UPS já cadastrada.
- `POST /api/importacoes/previsualizar/` — valida metadados e estrutura sem persistir;
- `POST /api/importacoes/{id}/pendencias/{pendencia_id}/resolver/` — associa uma linha sem código ao código G-MUS correto;
- `DELETE /api/importacoes/{id}/` — com confirmação explícita, exclui os registros derivados e cria auditoria.

Todos recebem `multipart/form-data` no campo `arquivo`. O campo opcional
`reimportar=true` substitui a importação existente da mesma competência, UPS e tipo.
Uma reimportação explicitamente confirmada também pode reprocessar o mesmo arquivo, o
que permite aplicar novas regras de conciliação sem editar o CSV original.

Uma linha de estoque com descrição, unidade e quantidade, mas sem código identificável,
fica registrada como pendência corrigível quando não existe correspondência única no
cadastro. A resolução recebe `codigo_gmus`, reutiliza o medicamento desse código ou cria
um cadastro com a descrição e unidade preservadas, incorpora a quantidade ao saldo e
registra usuário e data da resolução. Enquanto houver pendência aberta, a importação
permanece `concluida_parcial`. Códigos vazios ou genéricos são rejeitados.

Quando descrição e unidade encontram uma única correspondência segura no cadastro, a
conciliação é automática e tratada como informação interna: a linha é processada, não é
exibida como alerta e não altera sozinha o status da importação.

`GET /api/estoques/validacao-movimentacoes/` recebe `competencia` e `ups`, exige estoque
anterior, movimentações e estoque final concluídos e calcula o saldo esperado a partir
das entradas e saídas importadas.

A exclusão é transacional e não remove medicamentos, lotes ou classificações
compartilhados. Ela pode deixar uma competência incompleta, exigindo nova importação.

### Gerenciamento administrativo de classificacoes

```text
GET /api/classificacoes/
POST /api/classificacoes/
GET /api/classificacoes/{id}/
PATCH /api/classificacoes/{id}/
DELETE /api/classificacoes/{id}/
```

Todos exigem usuário ativo com `is_staff=True`. Os campos aceitos são `nome`, `cor`,
`descricao` e `ativo`. `nome` permanece único sem diferenciar maiúsculas de minúsculas;
`cor` aceita valor hexadecimal CSS (`#RGB`, `#RGBA`, `#RRGGBB` ou `#RRGGBBAA`) ou vazio.
Não há `PUT`. A desativação usa `PATCH` com `ativo=false`.

Uma classificação comum sem associações pode ser excluída e retorna HTTP `204`. Se
existirem medicamentos associados, a API retorna HTTP `409` e preserva a classificação
e todas as associações. A classificação canônica `MANIPULADO` também retorna HTTP `409`
e nunca pode ser excluída.

A classificação canônica `MANIPULADO` não pode ser renomeada ou desativada, e uma
segunda classificação com esse nome não pode ser criada. Sua cor e descrição podem ser
editadas.

Associação de uma classificação ativa ao medicamento:

```text
POST /api/medicamentos/{id}/classificacoes/
Content-Type: application/json

{"classificacao_id": 12}
```

A operação é idempotente e retorna HTTP `200` com a representação administrativa
atualizada do medicamento. Classificações inativas são rejeitadas.

Classificação manual em lote:

```text
POST /api/medicamentos/classificacoes/lote/
Content-Type: application/json

{
  "medicamento_ids": [12, 25, 48],
  "classificacao_id": 7
}
```

O endpoint exige `is_staff=True`, aceita no máximo 50 IDs e remove repetições. A
classificação precisa estar ativa e não pode ser `MANIPULADO`. A operação transacional
associa a categoria somente a medicamentos sem subgrupo G-MUS e sem categoria manual
comum preexistente. Itens com subgrupo, já classificados ou inexistentes são ignorados
de forma explícita, sem impedir o processamento dos elegíveis:

```json
{
  "selecionados": 4,
  "classificados": 2,
  "ignorados_subgrupo": 1,
  "ignorados_ja_classificados": 1,
  "ignorados_inexistentes": 0
}
```

O fluxo é idempotente e não altera associações da tag especial `MANIPULADO`.

Desclassificação manual em lote:

```text
POST /api/medicamentos/classificacoes/lote/remover/
Content-Type: application/json

{
  "medicamento_ids": [12, 25, 48],
  "classificacao_id": 7
}
```

O endpoint também exige `is_staff=True`, aceita no máximo 50 IDs e remove repetições.
A classificação escolhida pode estar inativa, para permitir a remoção de associações
anteriores, mas não pode ser `MANIPULADO`. A operação transacional remove somente essa
associação muitos-para-muitos dos medicamentos sem subgrupo G-MUS que a possuam. Outras
classificações, a tag `MANIPULADO`, o subgrupo e o próprio cadastro da classificação
permanecem inalterados:

```json
{
  "selecionados": 4,
  "desclassificados": 1,
  "ignorados_subgrupo": 1,
  "ignorados_sem_classificacao": 1,
  "ignorados_inexistentes": 1
}
```

Como um medicamento pode possuir mais de uma classificação comum, o cliente deve
informar explicitamente qual associação será removida. Itens inelegíveis não bloqueiam
o processamento dos demais. Depois da remoção da última categoria comum, um medicamento
sem subgrupo volta a atender ao filtro `sem_categoria=true`; a presença isolada de
`MANIPULADO` não altera esse comportamento.

Remoção de uma associação:

```text
DELETE /api/medicamentos/{id}/classificacoes/{classificacao_id}/
```

O sucesso retorna HTTP `204`. A associação canônica `MANIPULADO` é protegida enquanto
a descrição do medicamento contiver o marcador explícito `(MANIPULADO)`. Esses
endpoints não alteram o contrato da API pública.

### Resumo administrativo do Dashboard

```text
GET /api/dashboard/resumo/
```

Exige usuario administrativo com `is_staff=True`. O endpoint utiliza a competencia
mais recente que possui ao menos uma Consulta de Estoque registrada e retorna em uma unica
resposta apenas os dados necessarios para a Visao Geral:

```json
{
  "competencia_atual": {
    "id": 8,
    "ano": 2026,
    "mes": 8,
    "completa": true
  },
  "ups": {
    "participantes": 3,
    "importadas": 3
  },
  "importacoes": [
    {
      "importacao_id": 42,
      "ups": {
        "id": 2,
        "codigo_gmus": "2780046",
        "id_unidade_gmus": "9",
        "nome": "UPS EXEMPLO"
      },
      "usuario": "Maria da Silva",
      "status": "concluida",
      "data_importacao": "2026-08-17T10:00:00-03:00",
      "registros_estoque": 100,
      "alertas_relevantes": 0,
      "erros_nao_corrigiveis": 0,
      "pendencias_abertas": 0
    }
  ],
  "totais": {
    "medicamentos": 333,
    "estoques": 716
  }
}
```

`importadas` conta somente Consultas de Estoque com status `concluida` ou
`concluida_com_alertas` das UPS participantes. `estoques` e `medicamentos` contam apenas
registros associados a importacoes validas da competencia selecionada. O campo
`competencia_atual.completa` indica se todas as UPS participantes ja importaram um
estoque valido. Assim, a Visao Geral tambem exibe importacoes parciais e o andamento de
uma competencia incompleta, sem incorporar seus registros aos totais oficiais nem
misturar dados de outras competencias. Cada importacao informa o nome completo do
usuario responsavel, com fallback para o username.

O endpoint fornece os indicadores operacionais previstos no RF19. Ele nao calcula
consumo medio, comparacao, tendencia, curva ABC e cobertura sao expostos pela API de
analise. Necessidade de compra continua fora do escopo.

### Acompanhamento administrativo de competencias

```text
GET /api/competencias/acompanhamento/
```

Exige usuario administrativo com `is_staff=True`. O endpoint retorna todas as
competencias, da mais recente para a mais antiga, e explicita a situacao de cada UPS
configurada com `participa_competencia=True`:

```json
{
  "competencia_completa_mais_recente": {
    "id": 8,
    "ano": 2026,
    "mes": 8
  },
  "competencias": [
    {
      "id": 8,
      "ano": 2026,
      "mes": 8,
      "completa": true,
      "ups": {
        "esperadas": 3,
        "importadas_validas": 3,
        "situacoes": [
          {
            "id": 2,
            "codigo_gmus": "2780046",
            "id_unidade_gmus": "9",
            "nome": "UPS EXEMPLO",
            "importada": true,
            "status": "concluida",
            "data_importacao": "2026-08-17T10:00:00-03:00",
            "registros_estoque": 100
          }
        ]
      }
    }
  ]
}
```

Somente importacoes de Consulta de Estoque `concluida` ou `concluida_com_alertas` contam em
`importadas_validas` e podem completar a competencia. Uma importacao
`concluida_parcial` e exibida com seu status, mas nao conta como valida. Quando uma UPS
participante ainda nao possui importacao, `importada` e `false` e os campos `status`,
`data_importacao` e `registros_estoque` sao `null`.

O contrato inclui competencias incompletas e informa separadamente a competencia
completa mais recente. A resposta e montada com quantidade constante de consultas e
nao exige uma chamada adicional por competencia ou UPS.

### Pesquisa de medicamentos

O endpoint administrativo de medicamentos aceita o parametro opcional `search`:

```text
GET /api/medicamentos/?search=dipirona
```

A pesquisa e parcial e nao diferencia maiusculas de minusculas. Os campos pesquisados
sao `Medicamento.descricao` e `Medicamento.codigo_gmus`.

As representações administrativas de medicamento incluem
`quantidade_estoque_total`. O valor é uma string decimal com três casas e corresponde à
competência completa mais recente, somando todos os lotes de todas as UPS participantes,
inclusive a UPS de manipulação. Com competência completa e medicamento sem registro, o campo é
`"0.000"`; quando não existe competência completa, ele é `null`. O campo não integra a
API pública. A flag `compoe_estoque_convencional` não limita esse total administrativo.

Cada apresentacao permanece como um medicamento separado na resposta, preservando seu
codigo G-MUS, descricao e unidade. Uma consulta sem `search` continua retornando a
listagem administrativa normal.

A listagem tambem aceita uma competencia e uma UPS especificas. O saldo retornado passa
a representar exatamente esse recorte e inclui `competencia_estoque`,
`estoque_por_ups`, `situacao_estoque` e `situacao_validacao`. As situacoes de estoque possiveis sao `disponivel`,
`sem_estoque` e `sem_dados`; esta ultima e usada quando a combinacao de competencia e
UPS nao possui relatorio de estoque, sem confundir ausencia de dados com saldo zero.
O indicador de validacao usa `validado`, `divergente` ou `nao_validado` e agrega o
resultado da conferencia mensal das UPS selecionadas.

As opcoes da tela administrativa podem ser obtidas em:

```text
GET /api/medicamentos/opcoes/
```

O contrato retorna competencias e UPS que possuem importacao registrada, inclusive
parcial, alem das unidades presentes em dados validos e do ID da competencia padrao. A
listagem aceita ainda `unidade`, `situacao`, `validacao` e
`ordenacao`. Os
valores de ordenacao sao `descricao`, `codigo`, `maior_estoque` e `menor_estoque`.

Para filtros administrativos em lote, o endpoint de listagem aceita `ids` com até 50
IDs inteiros positivos separados por vírgula:

```text
GET /api/medicamentos/?ids=42,18,73
```

IDs repetidos são removidos e a resposta preserva a ordem informada. IDs inexistentes
são omitidos de forma controlada. Formato inválido ou mais de 50 IDs únicos retornam
HTTP `400`. O filtro exige usuário `is_staff=True`, não adiciona consultas por
medicamento e pode ser combinado com `search`, `subgrupo` e `classificacao`.

A visualização conjunta usa um contrato específico, também limitado a 50 IDs:

```text
GET /api/medicamentos/comparacao/?ids=42,18,73
```

A resposta contém `competencia`, a lista das UPS participantes e somente os medicamentos
solicitados que existem. Cada medicamento inclui seus dados cadastrais, badges,
`quantidade_estoque_total` e `estoque_por_ups`. A distribuição agrega todos os lotes por
medicamento e UPS na competência completa mais recente e preenche `"0.000"` quando não
há registro em uma UPS participante. Sem competência completa, `competencia` é `null`,
`ups` e `estoque_por_ups` são vazios e o total é `null`. O endpoint não retorna lotes,
histórico ou importações e executa quantidade constante de consultas.

### Filtros administrativos

Os filtros usam igualdade exata e podem ser combinados na mesma consulta.
Como `codigo_gmus` pode ser compartilhado por varias UPS, a selecao de uma unidade
especifica deve usar `ups`, com o ID interno retornado pela API administrativa. O
parametro legado `ups_codigo` e rejeitado com HTTP `400` para evitar resultados
ambiguos.

Medicamentos:

- `ids`: até 50 IDs de `Medicamento`, separados por vírgula;
- `sem_categoria`: booleano; quando `true`, exige subgrupo nulo e ausência de categoria
  manual comum. A tag `MANIPULADO` não descaracteriza essa condição;
- `subgrupo`: ID de `SubgrupoGmus`.
- `classificacao`: ID de `Classificacao`, incluindo a tag `MANIPULADO`;
- `tag`: ID de `Classificacao` usado como tag; pode ser combinado com `classificacao`;
- `competencia`: ID da competencia usada para calcular o saldo;
- `ups`: ID da UPS; quando omitido, soma todas as UPS participantes;
- `unidade`: unidade de apresentacao do medicamento;
- `situacao`: `disponivel`, `sem_estoque` ou `sem_dados`;
- `validacao`: `validado`, `divergente` ou `nao_validado`;
- `ordenacao`: `descricao`, `codigo`, `maior_estoque` ou `menor_estoque`.

Estoques:

- `medicamento`: ID de `Medicamento`;
- `ups`: ID de `Ups`;
- `competencia`: ID de `Competencia`;
- `subgrupo`: ID do `SubgrupoGmus` associado ao medicamento do estoque.

Exemplos:

```text
GET /api/medicamentos/?subgrupo=10
GET /api/medicamentos/?search=dipirona&subgrupo=10
GET /api/medicamentos/?classificacao=4
GET /api/medicamentos/?search=duloxetina&classificacao=2
GET /api/medicamentos/?sem_categoria=true
GET /api/medicamentos/?sem_categoria=true&search=duloxetina
GET /api/medicamentos/?competencia=8&ups=1&situacao=disponivel
GET /api/medicamentos/?competencia=8&unidade=COMPR&ordenacao=maior_estoque
GET /api/estoques/?ups=1
GET /api/estoques/?medicamento=42
GET /api/estoques/?competencia=8
GET /api/estoques/?ups=1&competencia=8&subgrupo=10
```

`sem_categoria=true` é incompatível com `subgrupo`, `classificacao` e `tag`; essas combinações
retornam HTTP `400` em vez de aplicar precedência silenciosa.

### Historico administrativo de medicamento

```text
GET /api/medicamentos/{id}/historico/
```

Exige usuario administrativo. O endpoint retorna a competencia completa mais recente
como `estoque_atual`, com totais por UPS e registros/lotes separados. Competencias
incompletas podem aparecer em `historico` com `completa=false`; importacoes
`concluida_parcial` nao completam uma competencia.

`quantidade_consolidada_convencional` soma todas as linhas e lotes somente das UPS com
`compoe_estoque_convencional=True`. UPS nao convencionais permanecem visiveis no
detalhamento administrativo. As quantidades sao representadas como strings decimais.
Esse campo do histórico mantém sua semântica convencional e é independente de
`quantidade_estoque_total` da listagem.

No detalhe administrativo, o destaque de estoque atual utiliza
`quantidade_estoque_total` retornado pela representação do medicamento. O campo
`quantidade_consolidada_convencional` permanece no contrato de histórico para os usos
explicitamente convencionais, e `por_ups` continua preservando a distribuição, os lotes
e as quantidades de cada unidade.

Formato resumido:

```json
{
  "medicamento_id": 42,
  "estoque_atual": {
    "competencia": {"id": 8, "ano": 2026, "mes": 8, "completa": true},
    "quantidade_consolidada_convencional": "125.000",
    "por_ups": [
      {
        "ups": {
          "id": 2,
          "codigo_gmus": "2780046",
          "id_unidade_gmus": "9",
          "nome": "UPS EXEMPLO",
          "compoe_estoque_convencional": true
        },
        "quantidade_total": "100.000",
        "registros": [
          {
            "estoque_id": 901,
            "quantidade": "60.000",
            "lote": {
              "id": 18,
              "codigo_lote": "LOTE-A",
              "data_validade": "2027-05-31"
            }
          }
        ]
      }
    ]
  },
  "historico": [
    {
      "competencia": {"id": 7, "ano": 2026, "mes": 7, "completa": false},
      "quantidade_consolidada_convencional": "110.000",
      "por_ups": [
        {
          "ups": {"id": 2, "codigo_gmus": "2780046", "id_unidade_gmus": "9", "nome": "UPS EXEMPLO"},
          "quantidade_total": "85.000"
        }
      ]
    }
  ]
}
```

Se nao houver competencia completa, `estoque_atual` sera `null`. Se houver competencia
completa, mas o medicamento estiver ausente nela, o consolidado sera `"0.000"` e
`por_ups` sera vazio. A competencia apresentada em `estoque_atual` nao e repetida em
`historico`; as demais competencias com registros sao ordenadas da mais recente para a
mais antiga.

O endpoint direto abaixo nao existe:

- `/api/importacoes/`
- `/api/localizacoes-estoque/`

Existe listagem administrativa em `GET /api/importacoes/`, além da importação aninhada
nos registros de estoque para preservar a rastreabilidade.

## Apêndice legado: inventário detalhado

> Esta seção descreve o contrato histórico preservado nos parsers e testes legados.
> A rota de inventário não faz parte do fluxo HTTP ativo. Use Consulta de Estoque e
> Movimentações conforme o escopo ativo no início deste documento.

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
reimportar: false
```

O campo multipart opcional `reimportar` aceita um booleano e assume `false`. Sem a
indicação explícita, uma importação existente para a combinação detectada de
competência, UPS e tipo de relatório permanece protegida e a API retorna `409`.
O frontend pode então solicitar confirmação e repetir o upload com
`reimportar=true`.

Historicamente, o backend detectava o inventário pelo conteúdo do CSV, executava o
parser específico e armazenava o nome original e o hash SHA-256. Erros de linha
rejeitavam somente aquela linha; erros globais ou a ausência de registros processáveis
bloqueavam a persistência.

O segmento `/inventario/` pertence ao contrato antigo e não está registrado nas URLs
atuais. A referência permanece somente para explicar registros legados.

Uma nova importação usa HTTP `201 Created`. Uma reimportação bem-sucedida usa HTTP
`200 OK`, pois atualiza a mesma `Importacao`. Ambas usam a mesma estrutura:

```json
{
  "importacao_id": 1,
  "reimportacao": false,
  "status": "concluida",
  "tipo_relatorio": "inventario",
  "hash_arquivo": "sha256-do-arquivo",
  "competencia": {"ano": 2026, "mes": 8},
  "ups": {
    "codigo_gmus": "2780046",
    "id_unidade_gmus": "9",
    "nome": "UPS DO RELATORIO"
  },
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

Na reimportação, `reimportacao` será `true` e `importacao_id` continuará sendo o ID do
registro original. O backend usa a competência, a UPS e o tipo detectados no próprio
CSV como chave; não aceita um alvo oculto indicado pelo frontend.

A substituição ocorre em uma transação atômica: somente os registros de `Estoque`
vinculados à importação encontrada são removidos, os novos estoques são persistidos e
os metadados (`nome_arquivo`, hash, data, status e usuário) são atualizados. Em caso de
falha, os estoques e metadados anteriores são restaurados pelo rollback. Medicamentos,
lotes e classificações não são removidos. No fluxo ativo de Consulta de Estoque, um
arquivo com SHA-256 igual poderá ser reprocessado quando `reimportar=true` for confirmado.

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
- `409 Conflict`: ja existe importacao sem confirmacao de reimportacao ou
  `reimportar=true` nao encontrou importacao para a chave detectada no CSV;
- `422 Unprocessable Entity`: tipo de relatorio desconhecido, erro global do parser ou ausencia de registros processaveis;
- `500 Internal Server Error`: falha inesperada, com mensagem generica e rollback da persistencia.

## Metodos permitidos

Os endpoints administrativos de consulta permanecem somente leitura, exceto pelas
operações explícitas de importação, classificação, associação e exclusão auditada
descritas acima. O upload de inventário não está disponível no fluxo atual.

Permitidos:

- `GET`
- `HEAD`
- `OPTIONS`
- `POST` para upload, criação de classificação e associação;
- `PATCH` para edição ou ativação/desativação de classificação;
- `DELETE` para remover uma associação entre medicamento e classificação ou excluir
  uma classificação comum sem associações.

Não permitidos para os recursos administrativos:

- `PUT`
- escrita nos demais viewsets de consulta.

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

## Fora do escopo implementado atual

Os contratos documentados acima ja incluem filtros administrativos, calculos e
agregacoes de estoque, comparacao de medicamentos, escrita de classificacoes e
classificacao/desclassificacao em lote.

Permanecem fora do escopo implementado atual:

- paginacao customizada;
- versionamento ou historico de versoes de uma importacao;
- limpeza automatica de lotes sem estoque apos reimportacao;
- consumo medio e comparacao de consumo;
- cobertura, giro e necessidade de compra;
- endpoints e tela especificos de analises baseados em consumo.

Os itens relacionados a consumo e compra dependem de dados e regras ainda nao
disponiveis; nao devem ser inferidos pela diferenca entre inventarios mensais.

## Separacao futura

O projeto possui dois contextos de acesso:

- modulo administrativo, autenticado;
- modulo publico, sem autenticacao.

A API publica inicial oferece somente a pesquisa de medicamentos e permanece separada
dos endpoints administrativos. Ela nao expoe quantidade, lote, validade, UPS de origem
ou outras informacoes administrativas internas.
