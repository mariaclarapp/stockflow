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
- arquitetura da solução;
- [API](docs/api/api.md);
- [banco de dados](docs/banco-de-dados/banco-de-dados.md).

## Módulos

### Administrativo

Destinado aos usuários autorizados da farmácia para importação dos relatórios, gerenciamento e consulta dos estoques.

Usuários Django ativos com `is_staff=True` podem operar esse módulo sem precisar de
`is_superuser`. O gerenciamento das contas administrativas é realizado separadamente
pelo Django Admin, em `http://127.0.0.1:8000/admin/` no ambiente local, e é restrito a
superusers. A criação controlada do primeiro superuser utiliza `python manage.py
createsuperuser`; credenciais não devem ser incluídas em arquivos versionados.

O frontend React também utiliza rotas iniciadas por `/admin`, porém em outra origem no
ambiente local. Uma implantação futura deverá manter o roteamento do frontend e do
Django Admin sem colisões.

### Público

Destinado à consulta pública de medicamentos, sem necessidade de autenticação.

## Status

Em desenvolvimento.

## Execucao local

Inicie o backend Django:

```powershell
cd backend
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

Em outro terminal, instale e inicie o frontend:

```powershell
cd frontend
npm install
npm run dev
```

O frontend usa `VITE_API_URL`, configurada em `frontend/.env`, para localizar a API.
O valor local padrao e `http://127.0.0.1:8000`. O backend deve possuir
`FRONTEND_URL=http://127.0.0.1:5173` para permitir cookies de sessao e CSRF durante o
desenvolvimento.

Mais detalhes estao em [`frontend/README.md`](frontend/README.md).
