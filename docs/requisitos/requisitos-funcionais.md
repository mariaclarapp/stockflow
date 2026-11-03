# Requisitos Funcionais - StockFlow

> Decisao vigente para RF15 e RF16: consulte `analise-consumo.md`. O consumo utiliza
> somente o campo `saida` do relatorio sintetico de movimentacoes.

## Decisao de escopo vigente

O fluxo operacional usa a Consulta de Estoque como fonte oficial do saldo mensal
e as movimentacoes para validar estoque anterior + entradas - saidas = estoque
atual. O inventario detalhado nao e necessario para concluir uma competencia.

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
| RF12 | Comparar múltiplos medicamentos (evolução futura; removido da listagem atual) | Administrativo |
| RF13 | Visualizar os medicamentos conforme sua UPS de estoque | Administrativo |
| RF14 | Consultar histórico de estoque por medicamento | Administrativo |
| RF15 | Calcular a média de consumo dos medicamentos | Administrativo |
| RF16 | Comparar médias de consumo de diferentes períodos | Administrativo |
| RF17 | Calcular a estimativa informativa de duração do estoque | Administrativo |
| RF18 | Calcular a quantidade necessária para compra | Administrativo |
| RF19 | Exibir indicadores operacionais da situação do estoque e das importações | Administrativo |
| RF20 | Consultar medicamentos | Público |
| RF21 | Consultar disponibilidade dos medicamentos | Público |
| RF22 | Exibir o medicamento conforme identificado pelo G-MUS, sua apresentação/dosagem, unidade e disponibilidade | Público |
| RF23 | Importar o relatório sintético de Consulta de Estoque, preservando competência, UPS e saldo total por medicamento | Administrativo |
| RF24 | Preservar dados legados de inventário sem utilizá-los no fluxo ativo | Administrativo |
| RF25 | Importar o relatório sintético de movimentações mensais por medicamento e UPS | Administrativo |
| RF26 | Validar o saldo final com base no estoque anterior e nas entradas e saídas do mês | Administrativo |
| RF27 | Corrigir manualmente uma divergência de validação, com justificativa, usuário e rastreabilidade das fontes | Administrativo |
| RF28 | Resolver linhas de estoque sem código G-MUS, preservando a pendência e a auditoria da associação | Administrativo |

## Observações

- O módulo administrativo exige autenticação.
- O RF02 permite que o superusuário cadastre funcionários pela tela própria do StockFlow.
  O Django Admin permanece disponível como mecanismo administrativo complementar. As
  contas criadas são ativas e staff, mas não recebem privilégio de superusuário.
- O módulo público não exige autenticação.
- A seleção múltipla deixou de fazer parte da listagem atual; cada medicamento possui consulta individual e a análise oferece comparação por período.
- No módulo público, a consulta será individual por medicamento e exibirá somente itens
  presentes no estoque válido da competência completa mais recente.
- O fluxo ativo preserva competência, UPS, apresentação, unidade, saldo e movimentações disponíveis nos relatórios oficiais.
- Dados históricos do antigo Inventário permanecem separados e não são somados à Consulta de Estoque.
- O RF25 preserva separadamente compras, devoluções, transferências, acertos, saídas e saldo atual do relatório de movimentação.
- No RF26, a ausência de uma linha no relatório sintético de movimentações representa
  movimento zero quando o medicamento existe nos estoques anterior e final. Medicamentos
  novos, presentes no estoque final e no relatório de movimentações, usam saldo anterior
  zero. A validação continua indisponível quando não existe saldo final.
- O RF27 não altera os relatórios nem o saldo originalmente importado. A correção só é
  aceita quando o saldo informado fecha a equação da competência e deixa de valer se
  alguma das importações usadas na validação for substituída.
- O RF15 depende de uma fonte confiável e validada de consumo mensal. Os inventários
  atualmente importados são fotografias do saldo de estoque e não fornecem consumo.
- O RF16 depende diretamente do RF15 e de consumo válido em múltiplos períodos.
- O RF17 apresenta cobertura estimada somente quando existem estoque final completo e
  média calculada a partir de competências completas.
- O RF18 é preservado para rastreabilidade do planejamento original, mas fica definido
  como evolução futura. Seu cálculo depende de consumo válido, regra de cobertura e
  parâmetros administrativos ainda não definidos.
- O RF19 corresponde aos indicadores operacionais e analíticos disponíveis sobre competência,
  UPS esperadas e importadas, status das importações, medicamentos e registros de
  estoque. Não representa níveis de cobertura, giro ou consumo.
