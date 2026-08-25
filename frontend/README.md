# StockFlow Frontend

Frontend web do StockFlow desenvolvido com React e Vite, em JavaScript. A aplicacao
reune a consulta publica de medicamentos e o modulo administrativo autenticado.

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

A rota inicial redireciona para a consulta publica em `/medicamentos`. O acesso ao
modulo administrativo permanece disponivel em `/login`.

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

A consulta publica nao depende de sessao e envia suas requisicoes sem credenciais.

Somente sessoes de usuarios Django ativos com `is_staff=True` sao aceitas pela area
administrativa. `is_superuser` nao e necessario.

O gerenciamento de contas nao possui tela React e ocorre oficialmente no Django Admin,
por superusers. Usuarios staff comuns operam o StockFlow, mas nao recebem permissoes de
administracao de `User` ou `Group`. A opcao Configuracoes permanece desabilitada e nao
oferece link para o Django Admin nesta etapa.

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
com alertas e parciais. Quando a API informa conflito para uma competencia/UPS ja
importada, a tela oferece a acao explicita `Reimportar e substituir` e solicita
confirmacao em um modal antes de reenviar o mesmo arquivo com o campo multipart
`reimportar=true`. A substituicao e transacional no backend e o resumo indica quando o
processamento foi uma reimportacao. Arquivos identicos, com o mesmo SHA-256, nao sao
processados novamente. Historico de versoes de importacao nao faz parte deste fluxo.

## Consulta administrativa de medicamentos

A rota `/admin/medicamentos` consulta `GET /api/medicamentos/` e preserva cada codigo
G-MUS como uma apresentacao independente. A tela oferece busca textual por descricao ou
codigo (`search`) e um filtro visual único de Categoria. O seletor agrupa subgrupos
oficiais de `GET /api/subgrupos-gmus/` e classificações ativas de
`GET /api/classificacoes/`, traduzindo a seleção para `subgrupo` ou `classificacao` na
API. Os badges interativos da listagem também aplicam o filtro correspondente. A listagem apresenta o estoque total
consolidado informado pelo backend, somando todas as UPS participantes. Sem competência completa, exibe
`Não informado` em vez de assumir saldo zero.

A listagem permite selecionar até 50 medicamentos visíveis por checkboxes no desktop e
no mobile. A seleção é limpa quando a busca ou a Categoria muda. A ação `Visualizar
selecionados` abre `/admin/medicamentos/comparar?ids=1,2,3`, permitindo recarregar a
página sem perder a composição. A comparação usa uma única chamada a
`GET /api/medicamentos/comparacao/?ids=...` e mostra somente os IDs informados, com
código G-MUS, descrição, unidade, badges, estoque total e distribuição agregada por UPS
participante. Não carrega lotes, histórico combinado ou indicadores.

Com itens selecionados, a barra compacta também oferece `Classificar`. O modal resume
quantos medicamentos serão classificados, quantos possuem subgrupo e quantos já têm
categoria manual. Apenas classificações comuns ativas são oferecidas; `MANIPULADO` não
participa desse fluxo. A confirmação faz uma única requisição a
`POST /api/medicamentos/classificacoes/lote/`, recarrega os badges, limpa a seleção e
exibe o total classificado.

A mesma barra oferece `Desclassificar`. Nesse modo, o usuário escolhe explicitamente
qual categoria manual associada será removida, pois o modelo admite múltiplas
classificações comuns. O modal informa os itens elegíveis e os ignorados, e envia uma
única requisição a `POST /api/medicamentos/classificacoes/lote/remover/`. Subgrupos e a
tag `MANIPULADO` são preservados; após o sucesso, a listagem e os badges são atualizados
e a seleção é limpa.

O seletor de Categoria oferece `Sem categoria`, traduzido para
`GET /api/medicamentos/?sem_categoria=true`. A condição inclui medicamentos sem
subgrupo e sem categoria manual comum; a tag `MANIPULADO`, sozinha, não os exclui.

A rota `/admin/medicamentos/:id` apresenta os dados cadastrais, o estoque da competencia
completa mais recente e o historico mensal. A tela consulta em paralelo
`GET /api/medicamentos/{id}/` e `GET /api/medicamentos/{id}/historico/`; consolidacao,
completude e totais por UPS permanecem sob responsabilidade do backend. O destaque de
estoque atual usa `quantidade_estoque_total`, considerando todas as UPS participantes; o
histórico preserva a distribuição por UPS e seu consolidado especificamente convencional.

O detalhe também possui uma área administrativa de classificações. Nela, o usuário pode
associar classificações ativas, remover associações permitidas e abrir um modal compacto
para listar, criar, editar, ativar ou desativar classificações. Não existe uma página
geral de Configurações para esse fluxo. A classificação canônica `MANIPULADO` mantém o
nome e o estado ativo protegidos; sua associação também não pode ser removida enquanto
a descrição do medicamento contiver `(MANIPULADO)`. Classificações comuns podem ser
excluídas após confirmação somente quando não possuem associações; `MANIPULADO` não
oferece essa ação. Quando o medicamento já possui subgrupo oficial, a interface de
associação oferece apenas `MANIPULADO`; categorias manuais comuns continuam disponíveis
para medicamentos sem subgrupo.

## Consulta publica de medicamentos

A rota publica `/medicamentos` permite pesquisar apresentacoes por descricao ou codigo
G-MUS sem autenticacao. A busca e enviada somente ao confirmar o formulario e consulta
`GET /api/publico/medicamentos/?search=<termo>`.

Cada apresentacao permanece em um resultado separado. A interface exibe exclusivamente
codigo G-MUS, descricao, unidade e a situacao textual de disponibilidade calculada pelo
backend. Quantidades, UPS, competencia, lotes, validade, importacao, classificacoes e
demais informacoes administrativas nao sao expostas.

## Acompanhamento de competencias

A rota `/admin/competencias` consulta `GET /api/competencias/acompanhamento/` uma unica
vez e apresenta competencias completas e incompletas, da mais recente para a mais
antiga. Os filtros de ano e situacao sao aplicados localmente. Cada item pode ser
expandido para mostrar o inventario de todas as UPS participantes, incluindo as que
ainda estao pendentes, e oferece acesso direto a `/admin/importacoes` quando a
competencia esta incompleta.

Nesta etapa, consulta publica, Login, protecao de rotas, Visao geral, Importacoes,
consulta administrativa de Medicamentos e acompanhamento de Competencias estao
implementados. Analises e Configuracoes continuam desabilitadas.
