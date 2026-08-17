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

Nesta etapa, somente Login, protecao de rotas e a estrutura inicial da Visao geral
estao implementados. Os demais itens da sidebar sao destinos visuais desabilitados.
