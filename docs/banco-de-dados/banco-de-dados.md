# Banco de Dados - StockFlow

Este documento registra o estado atual implementado do banco de dados local do StockFlow.

## Tecnologia

O projeto utiliza MySQL.

No ambiente local atual, o servidor usado pelo StockFlow e MySQL 8.4.x.

O banco local da aplicacao e:

```text
stockflow
```

## Configuracao local

A conexao do Django com o banco e configurada por variaveis de ambiente em `backend/.env`.

Variaveis usadas:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

Senhas reais nao devem ser versionadas.

O usuario da aplicacao deve ser separado do usuario administrativo `root`.

Neste ambiente local, `DB_PORT` foi configurada como `3307` porque o MariaDB do XAMPP ocupa a porta `3306`. Essa porta e uma configuracao local, nao uma regra fixa do projeto.

## Apps e models existentes

App `core`:

- `Ups`
- `Competencia`

App `medicamentos`:

- `SubgrupoGmus`
- `PrincipioAtivo`
- `Classificacao`
- `Medicamento`

App `importacoes`:

- `Importacao`

App `estoques`:

- `Lote`
- `Estoque`

## Relacionamentos principais

- `Medicamento` pode pertencer a um `SubgrupoGmus`.
- `Medicamento` possui relacao muitos-para-muitos com `PrincipioAtivo`.
- `Medicamento` possui relacao muitos-para-muitos com `Classificacao`.
- `Lote` pertence a um `Medicamento`.
- `Importacao` referencia usuario autenticado, `Competencia` e `Ups`.
- `Importacao.hash_arquivo` preserva o SHA-256 do CSV, sem armazenar seu conteudo completo.
- `Estoque` referencia `Medicamento`, `Ups`, `Competencia`, `Lote` e `Importacao`.
- `Estoque.lote` e opcional.

`PrincipioAtivo` e sua relacao muitos-para-muitos permanecem descritos porque ainda
existem no schema atual. Os relatorios de inventario nao fornecem uma coluna separada
nem alimentam essa estrutura. A consulta publica usa `Medicamento.descricao` e
`Medicamento.unidade`; portanto, `PrincipioAtivo` nao e obrigatorio para o RF22. Sua
permanencia ou remocao sera avaliada posteriormente como limpeza de modelagem, sem
representar funcionalidade futura obrigatoria.
- `Ups` representa a localizacao e a origem do estoque no relatorio de inventario.
- `Ups.codigo_gmus` preserva o codigo do estabelecimento, que pode ser compartilhado.
- `Ups.id_unidade_gmus` preserva o identificador especifico da unidade no G-MUS.
- `Ups.participa_competencia` configura se a unidade precisa de inventario valido para
  completar uma competencia.
- `Ups.compoe_estoque_convencional` configura se seus estoques participam da futura
  consolidacao convencional.

## Classificacao MANIPULADO

A estrutura atual ja permite representar `MANIPULADO` como uma `Classificacao`
associada ao medicamento pela relacao muitos-para-muitos existente.
`Classificacao.nome` e unico e possui tamanho suficiente para armazenar o nome
canonico `MANIPULADO`. Nenhuma alteracao de model ou migration e necessaria para essa
representacao.

Somente a associacao com a classificacao canonica `MANIPULADO` que esteja com
`Classificacao.ativo=True` acionara a regra publica especial.

Na disponibilidade publica, um servico de dominio centralizado consulta a associacao do
medicamento com a classificacao canonica. A condicao nao e inferida pelo nome da UPS,
por lotes ou por historico de estoque.

## Migrations aplicadas

As migrations padrao do Django foram aplicadas para:

- `admin`
- `auth`
- `contenttypes`
- `sessions`

As migrations iniciais do dominio foram aplicadas para:

- `core.0001_initial`
- `medicamentos.0001_initial`
- `importacoes.0001_initial`
- `estoques.0001_initial`

As migrations abaixo foram aplicadas para usar a UPS como unica localizacao/origem do estoque:

- `estoques.0002_remove_estoque_localizacao`
- `core.0002_delete_localizacaoestoque`

A primeira removeu a FK de `Estoque`; a segunda depende dela e removeu a tabela antiga.

A migration abaixo ja foi aplicada ao banco local:

- `importacoes.0002_importacao_hash_arquivo_alter_importacao_status_and_more`

Ela adiciona o SHA-256 do arquivo, os status iniciais e a restricao de unicidade por competencia, UPS e tipo de relatorio.

As migrations abaixo tambem foram aplicadas ao banco local:

- `core.0003_ups_compoe_estoque_convencional_and_more`
- `importacoes.0003_alter_importacao_status`

Elas adicionam as duas configuracoes booleanas de `Ups` e registram
`concluida_parcial` entre as opcoes de status da importacao.

As migrations de identificacao das unidades G-MUS tambem foram aplicadas:

- `core.0004_ups_id_unidade_gmus_alter_ups_codigo_gmus_and_more`
- `core.0005_alter_ups_id_unidade_gmus`

A primeira adiciona temporariamente o identificador como anulavel, remove a unicidade
isolada do codigo compartilhado e cria a restricao composta. O dado local existente foi
corrigido de forma controlada antes da segunda migration, que torna
`id_unidade_gmus` obrigatorio.

## Tabelas de dominio

Tabelas criadas pelos apps de dominio:

- `core_competencia`
- `core_ups`
- `medicamentos_subgrupogmus`
- `medicamentos_principioativo`
- `medicamentos_classificacao`
- `medicamentos_medicamento`
- `importacoes_importacao`
- `estoques_lote`
- `estoques_estoque`

Tabelas muitos-para-muitos automaticas do Django:

- `medicamentos_medicamento_principios_ativos`
- `medicamentos_medicamento_classificacoes`

## Autenticacao e sessoes

O StockFlow utiliza a autenticacao e as sessoes nativas do Django.

Nao existem models proprios `Usuario` ou `Sessao`.

`Importacao.usuario` referencia `settings.AUTH_USER_MODEL`.

## Restricoes implementadas

- `SubgrupoGmus.codigo_gmus` e unico quando informado.
- `Classificacao.nome` e unico.
- `Medicamento.codigo_gmus` e unico.
- `Ups` possui unicidade composta para `(codigo_gmus, id_unidade_gmus)`; o codigo
  G-MUS isolado pode pertencer a varias unidades.
- `Competencia` possui unicidade para a combinacao `(ano, mes)`.
- `Competencia.mes` possui validacao e restricao de banco para ficar entre 1 e 12.
- `Estoque.quantidade` usa `DecimalField(max_digits=14, decimal_places=3)`.
- `Importacao` impede duplicidade da combinacao `(competencia, ups, tipo_relatorio)`.
- `Ups.participa_competencia` e `Ups.compoe_estoque_convencional` usam `True` como
  padrao e permitem configurar as unidades sem inferencia por nome.
- `Importacao.status` utiliza `concluida`, `concluida_com_alertas` e
  `concluida_parcial`.

## Quantidades do inventario

- `Qtde Virt.` e a fonte da quantidade de estoque utilizada pelo StockFlow.
- `Qtde Virt.` negativa e um erro de linha e nao gera estoque valido.
- `Qtde R.` nao e utilizada pelo StockFlow, nao integra o registro normalizado e nao e persistida.

## Competencia completa e consolidacao publica

Uma competencia sera completa quando houver importacao de inventario `concluida` ou
`concluida_com_alertas` para cada UPS com `participa_competencia=True`. UPS adicionais
nao impedem a completude. A soma convencional usa somente estoques de UPS com
`compoe_estoque_convencional=True` e agrega todas as linhas e lotes por
medicamento.

Se a competencia mais recente estiver incompleta, a disponibilidade usa a
competencia completa anterior mais recente. Sem competencia completa, medicamentos sem
tag ativa `MANIPULADO` terao `Disponibilidade nao informada`. Em uma competencia
completa, medicamento sem registro convencional sera tratado como saldo convencional
zero, pois o G-MUS pode omitir saldos zerados.

A identificacao de competencias completas e centralizada em um servico de dominio
compartilhado pela disponibilidade publica e pelo historico administrativo. O historico
e derivado de `Estoque`, `Competencia`, `Ups`, `Lote` e `Importacao`; nao existe tabela
de historico ou de estoque consolidado. As somas preservam os registros individuais e
nao utilizam `distinct` sobre quantidade.

## Decisoes ainda pendentes

Ainda nao foram fechadas:

- unicidade definitiva de `Lote`;
- restricao composta definitiva de `Estoque`;
- estrategia definitiva de reimportacao;
- fonte definitiva para consumo mensal.
