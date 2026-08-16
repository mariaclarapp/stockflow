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
- `Estoque` referencia `Medicamento`, `Ups`, `Competencia`, `Lote` e `Importacao`.
- `Estoque.lote` e opcional.
- `Ups` representa a localizacao e a origem do estoque no relatorio de inventario.

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
- `Ups.codigo_gmus` e unico.
- `Competencia` possui unicidade para a combinacao `(ano, mes)`.
- `Competencia.mes` possui validacao e restricao de banco para ficar entre 1 e 12.
- `Estoque.quantidade` usa `DecimalField(max_digits=14, decimal_places=3)`.

## Quantidades do inventario

- `Qtde Virt.` e a fonte da quantidade de estoque utilizada pelo StockFlow.
- `Qtde R.`, quando preenchida no CSV, e preservada separadamente pelo parser para rastreabilidade e nao substitui automaticamente `Qtde Virt.`.

## Decisoes ainda pendentes

Ainda nao foram fechadas:

- unicidade definitiva de `Lote`;
- restricao composta definitiva de `Estoque`;
- estrategia definitiva de reimportacao;
- valores definitivos de `Importacao.status`;
- valores definitivos de `Importacao.tipo_relatorio`;
- regras finais de disponibilidade publica;
- fonte definitiva para consumo mensal.
