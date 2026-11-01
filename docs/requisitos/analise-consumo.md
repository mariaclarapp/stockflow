# Analise de consumo

Este documento registra a decisao de negocio vigente para os RF15 e RF16 e substitui
as observacoes anteriores que tratavam a fonte de consumo como indefinida.

## Fonte do consumo

O consumo mensal corresponde exclusivamente ao campo `saida` do relatorio G-MUS de
Movimentacao de Estoque - Sintetico. O valor permanece associado ao medicamento, a UPS
e a competencia de origem.

Compras, transferencias, devolucoes e acertos nao integram o consumo. Esses valores sao
preservados separadamente para validacao de estoque e contexto operacional. O consumo
nao deve ser inferido pela diferenca entre dois saldos mensais.

## Media mensal

A media mensal e calculada dividindo a soma do consumo pela quantidade de competencias
com importacoes concluidas para todas as UPS selecionadas. Competencias parciais ou sem
relatorio nao entram na soma nem no divisor e devem ser sinalizadas na interface.

Medicamentos presentes nos relatorios com `saida` igual a zero sao listados como itens
sem consumo no periodo.

## Comparacao entre periodos

Os dois periodos usam os mesmos filtros de UPS, medicamento e categoria. A variacao
percentual nao e calculada quando o periodo comparado possui consumo zero.

## Escopo implementado

- filtros por periodo, UPS, medicamento e categoria;
- consumo total e media mensal;
- evolucao por competencia;
- ranking e participacao por medicamento;
- distribuicao do consumo por UPS;
- comparacao entre periodos;
- listagem de medicamentos sem consumo;
- exportacao CSV do ranking.
- curva ABC por participacao acumulada no consumo;
- tendencia entre a primeira e a ultima competencia valida do periodo;
- cobertura estimada em dias quando o estoque final esta completo.

Necessidade de compra permanece fora do escopo ate a definicao de prazo de reposicao,
margem de seguranca e politica administrativa. A cobertura atual e informativa.
