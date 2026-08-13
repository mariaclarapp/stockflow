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

- Este backend ainda nao implementa models, endpoints de dominio, importacao de CSV ou calculos de estoque.
- As configuracoes sensiveis devem permanecer em variaveis de ambiente.
- O banco configurado e MySQL, conforme definido na documentacao do projeto.
