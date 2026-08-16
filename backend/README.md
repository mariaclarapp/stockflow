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

## Observacoes

- O backend possui models de dominio, API administrativa de leitura e upload autenticado
  do relatorio CSV de inventario.
- A estrategia definitiva de reimportacao e os calculos de estoque ainda nao foram implementados.
- O contrato atual da API esta documentado em [`docs/api/api.md`](../docs/api/api.md).
- As configuracoes sensiveis devem permanecer em variaveis de ambiente.
- O banco configurado e MySQL, conforme definido na documentacao do projeto.
