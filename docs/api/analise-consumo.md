# API de analise de consumo

```text
GET /api/analises/consumo/
```

Exige usuario administrativo com `is_staff=True`.

## Parametros

- `competencia_inicial` e `competencia_final`: obrigatorios;
- `ups`, `busca`, `subgrupo` e `classificacao`: opcionais;
- `comparacao_inicial` e `comparacao_final`: opcionais, mas devem ser enviados juntos.

O consumo corresponde somente ao campo `saida` do relatorio sintetico de movimentacoes.
A resposta apresenta `resumo`, `qualidade`, `evolucao`, `ranking`, `por_ups`,
`sem_consumo` e, quando solicitado, `comparacao`.

Competencias sem relatorio sao informadas em `qualidade.competencias_sem_dados` e nao
entram no divisor de `resumo.media_mensal`.
