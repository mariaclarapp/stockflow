# API de analise de consumo

```text
GET /api/analises/consumo/
```

Exige usuario administrativo com `is_staff=True`.

## Parametros

- `competencia_inicial` e `competencia_final`: obrigatorios;
- `ups`, `busca`, `subgrupo`, `classificacao` e `unidade`: opcionais;
- `comparacao_inicial` e `comparacao_final`: opcionais, mas devem ser enviados juntos.

O consumo corresponde somente ao campo `saida` do relatorio sintetico de movimentacoes.
A resposta apresenta `resumo`, `qualidade`, `evolucao`, `ranking`, `por_ups`,
`sem_consumo`, `curva_abc` e, quando solicitado, `comparacao`. Cada item do ranking
inclui media, estoque final, cobertura, classe ABC, tendencia e evolucao mensal.

Competencias sem relatorio concluido para todas as UPS selecionadas sao informadas em
`qualidade.competencias_sem_dados` e nao entram na soma nem no divisor da media.

A media mensal do periodo divide o consumo total pelas competencias completas do
intervalo, incluindo meses completos em que o medicamento teve saida zero. A resposta
tambem fornece a media calculada somente nos meses em que houve saida, para permitir a
comparacao entre regularidade e intensidade do consumo.
