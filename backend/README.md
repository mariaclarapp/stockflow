# StockFlow Backend

Estrutura inicial do back-end do StockFlow usando Python, Django, Django REST Framework e MySQL.

## Configuracao local

1. Crie e ative um ambiente virtual.
2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` a partir de `.env.example` e preencha as variaveis locais.
4. Execute as verificacoes do Django:

```bash
python manage.py check
```

5. Execute as migracoes:

```powershell
.\.venv\Scripts\python manage.py migrate
```

## Testes

Os testes automatizados usam SQLite em memoria e nao alteram o banco MySQL local:

```powershell
.\.venv\Scripts\python manage.py test --settings=stockflow.test_settings
```

## Observacoes

- O fluxo ativo importa Consulta de Estoque e Movimentacao de Estoque - Sintetico.
- Reimportacao, exclusao auditada, validacao mensal e analise de consumo estao implementadas.
- O contrato atual da API esta documentado em [`docs/api/api.md`](../docs/api/api.md).
- As configuracoes sensiveis devem permanecer em variaveis de ambiente.
- O banco configurado e MySQL, conforme definido na documentacao do projeto.
