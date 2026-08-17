# StockFlow Frontend

Frontend administrativo do StockFlow desenvolvido com React e Vite, em JavaScript.

## Configuracao local

1. Instale as dependencias:

```bash
npm install
```

2. Crie `frontend/.env` a partir de `.env.example` quando precisar alterar a URL
   padrao da API:

```env
VITE_API_URL=http://127.0.0.1:8000
```

3. Inicie o servidor de desenvolvimento:

```bash
npm run dev
```

O frontend fica disponivel em `http://127.0.0.1:5173`.

## Backend local

O Django deve estar em execucao em `http://127.0.0.1:8000` e o arquivo
`backend/.env` deve permitir a origem do frontend:

```env
FRONTEND_URL=http://127.0.0.1:5173
```

Para iniciar o backend, em outro terminal:

```powershell
cd backend
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

## Autenticacao

O frontend usa a sessao nativa do Django:

1. solicita o token e o cookie CSRF em `GET /api/auth/csrf/`;
2. envia usuario, senha e `X-CSRFToken` em `POST /api/auth/login/`;
3. valida a sessao inicial em `GET /api/auth/me/`;
4. encerra a sessao com CSRF em `POST /api/auth/logout/`.

Todas as requisicoes usam `credentials: "include"`. Senha e tokens de autenticacao
nao sao armazenados em `localStorage`.

Somente sessoes de usuarios Django ativos com `is_staff=True` sao aceitas pela area
administrativa. `is_superuser` nao e necessario.

## Comandos

```bash
npm run dev
npm run build
npm run lint
npm run preview
```

## Importacao de inventario

A rota administrativa `/admin/importacoes` permite selecionar e enviar um relatorio
CSV de inventario para `POST /api/importacoes/inventario/`. O envio usa
`multipart/form-data`, no campo `arquivo`, e preserva o fluxo de sessao e CSRF da
aplicacao.

A tela apresenta o resumo retornado pela API e trata importacoes concluidas, concluidas
com alertas e parciais. Reimportacao e historico de importacoes ainda nao fazem parte
deste fluxo.

## Consulta administrativa de medicamentos

A rota `/admin/medicamentos` consulta `GET /api/medicamentos/` e preserva cada codigo
G-MUS como uma apresentacao independente. A tela oferece busca textual por descricao ou
codigo (`search`) e filtro pelos subgrupos reais fornecidos por
`GET /api/subgrupos-gmus/` (`subgrupo`).

Nesta etapa, Login, protecao de rotas, a estrutura inicial da Visao geral, Importacoes e
a consulta de Medicamentos estao implementados. Os demais itens da sidebar continuam
desabilitados.
