# Requisitos Funcionais — StockFlow

Este documento apresenta os requisitos funcionais atualmente definidos para o sistema StockFlow.

| ID | Requisito Funcional | Módulo |
|---|---|---|
| RF01 | Fazer login no sistema | Administrativo |
| RF02 | Gerenciar usuários administrativos | Administrativo |
| RF03 | Fazer upload de arquivo CSV | Administrativo |
| RF04 | Identificar automaticamente o tipo de relatório importado | Administrativo |
| RF05 | Realizar limpeza e padronização dos dados do CSV | Administrativo |
| RF06 | Agrupar os dados importados por medicamento, UPS e competência | Administrativo |
| RF07 | Permitir reimportação e atualização dos dados de um relatório | Administrativo |
| RF08 | Consolidar automaticamente os dados das três UPS | Administrativo |
| RF09 | Manter a identificação da UPS, que representa a localização/origem, e do lote de cada medicamento | Administrativo |
| RF10 | Gerenciar classificações e categorias dos medicamentos | Administrativo |
| RF11 | Filtrar medicamentos por diferentes características | Administrativo |
| RF12 | Selecionar múltiplos medicamentos para visualização | Administrativo |
| RF13 | Visualizar os medicamentos conforme sua UPS de estoque | Administrativo |
| RF14 | Consultar histórico de estoque por medicamento | Administrativo |
| RF15 | Calcular a média de consumo dos medicamentos | Administrativo |
| RF16 | Comparar médias de consumo de diferentes períodos | Administrativo |
| RF17 | Calcular a estimativa de duração do estoque | Administrativo |
| RF18 | Calcular a quantidade necessária para compra | Administrativo |
| RF19 | Exibir indicadores de situação do estoque | Administrativo |
| RF20 | Consultar medicamentos | Público |
| RF21 | Consultar disponibilidade dos medicamentos | Público |
| RF22 | Exibir princípio ativo, apresentação/dosagem e disponibilidade | Público |

## Observações

- O módulo administrativo exige autenticação.
- O módulo público não exige autenticação.
- A seleção de múltiplos medicamentos é destinada ao módulo administrativo.
- No módulo público, a consulta será individual por medicamento.
- O processamento dos relatórios deverá preservar competência, UPS, lote, validade e demais informações disponíveis no arquivo importado. No inventário, a UPS representa a localização/origem do estoque.
- Alguns requisitos relacionados aos cálculos de consumo dependem da definição definitiva da fonte utilizada para obtenção do consumo mensal.
