# Documentação — StockFlow

Esta pasta reúne a documentação técnica e os artefatos de engenharia de software do sistema StockFlow.

O objetivo é manter a modelagem, os requisitos e as decisões do projeto versionados junto ao código-fonte.

## Estrutura

### Requisitos

A pasta [`requisitos`](./requisitos/) contém a especificação funcional e as principais regras do sistema.

Arquivos:

- [`requisitos-funcionais.md`](./requisitos/requisitos-funcionais.md)
- [`requisitos-nao-funcionais.md`](./requisitos/requisitos-nao-funcionais.md)
- [`regras-de-negocio.md`](./requisitos/regras-de-negocio.md)

### API

A pasta [`api`](./api/) documenta o estado implementado da API do backend.

Arquivos:

- [`api.md`](./api/api.md)

### Banco de Dados

A pasta [`banco-de-dados`](./banco-de-dados/) documenta a configuração e a modelagem implementada no banco de dados.

Arquivos:

- [`banco-de-dados.md`](./banco-de-dados/banco-de-dados.md)

### Diagramas

A pasta [`diagramas`](./diagramas/) contém os artefatos de modelagem do StockFlow.

#### Diagrama Entidade-Relacionamento

Local:

`diagramas/der/`

Representa as principais entidades persistidas pelo sistema, seus atributos, chaves e relacionamentos.

#### Diagrama de Classes

Local:

`diagramas/classes/`

Representa as classes de domínio e os principais serviços responsáveis pelas regras de negócio da aplicação.

#### Diagramas de Casos de Uso

Local:

`diagramas/casos-de-uso/`

Representam as principais interações dos usuários administrativo e público com o StockFlow.

#### Diagramas de Sequência

Local:

`diagramas/sequencia/`

Atualmente estão documentados:

- fluxo de importação do relatório de inventário;
- fluxo de consulta pública de medicamentos.

#### Arquitetura

Local:

`diagramas/arquitetura/`

Apresenta a arquitetura geral da solução, incluindo:

- front-end React com JavaScript;
- back-end Django;
- API;
- serviços de negócio;
- banco de dados MySQL;
- origem dos relatórios CSV exportados do G-MUS.

## Dados

A pasta [`dados`](./dados/) deverá conter somente documentação sobre estruturas de dados e exemplos fictícios ou anonimizados.

Relatórios reais exportados da farmácia não devem ser versionados no repositório.

## Trabalho de Graduação

A pasta [`tg`](./tg/) poderá ser utilizada para materiais auxiliares relacionados à documentação acadêmica do projeto.

O documento oficial do Trabalho de Graduação poderá continuar sendo mantido no Overleaf.

## Observação

Nem todos os diagramas e artefatos mantidos neste repositório precisam necessariamente ser inseridos no documento final do TG.

O repositório funciona também como documentação técnica complementar do sistema.
