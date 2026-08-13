# StockFlow

Sistema web desenvolvido como Trabalho de Graduação do curso de Análise e Desenvolvimento de Sistemas da Fatec Ourinhos.

O StockFlow tem como objetivo auxiliar a gestão de estoque de medicamentos da Farmácia Municipal de Ribeirão Claro, automatizando a importação, organização e consolidação dos relatórios exportados pelo sistema G-MUS, além de disponibilizar um módulo público para consulta de medicamentos.

## Tecnologias

### Back-end
- Python
- Django
- MySQL

### Front-end
- React
- JavaScript

## Estrutura do projeto

- `backend/`: aplicação Django e regras de negócio.
- `frontend/`: aplicação React.
- `docs/`: documentação de engenharia de software e materiais do projeto.

## Documentação

A documentação técnica está organizada em `docs/`, incluindo:

- requisitos funcionais e não funcionais;
- regras de negócio;
- DER;
- diagrama de classes;
- casos de uso;
- diagramas de sequência;
- arquitetura da solução.

## Módulos

### Administrativo

Destinado aos usuários autorizados da farmácia para importação dos relatórios, gerenciamento e consulta dos estoques.

### Público

Destinado à consulta pública de medicamentos, sem necessidade de autenticação.

## Status

Em desenvolvimento.