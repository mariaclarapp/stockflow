# Regras de Negócio — StockFlow

Este documento reúne as principais regras de negócio definidas para o sistema StockFlow. As regras descritas aqui orientam a modelagem, a implementação e os testes da aplicação.

## RN01 — Origem dos dados

O StockFlow não terá acesso direto ao banco de dados do sistema G-MUS.

Os dados serão obtidos por meio de relatórios exportados manualmente do G-MUS em formato CSV e posteriormente importados para o StockFlow.

## RN02 — Importação mensal

O controle de estoque será baseado em competências mensais.

Para que uma competência seja considerada completa, deverá existir uma importação de
inventário com status `concluida` ou `concluida_com_alertas` para cada UPS configurada
com `participa_competencia=True`.

UPS adicionais que não participam dessa configuração não impedirão que a competência
seja considerada completa. A identificação das UPS participantes deverá ser configurada
nos dados, sem nomes fixados no código-fonte.

As três UPS consideradas atualmente são:

- CAF — Centro de Abastecimento Farmacêutico;
- Farmácia Municipal de Ribeirão Claro;
- Farmácia de Manipulação.

## RN03 — Identificação automática da importação

Durante a importação, o sistema deverá identificar as informações disponíveis no próprio relatório, incluindo, quando presentes:

- competência;
- UPS;
- medicamento/apresentação;
- código do medicamento no G-MUS;
- unidade;
- subgrupo;
- lote;
- validade;
- quantidade.

No relatório de inventário, a UPS/unidade identificada nos metadados representa a localização e a origem de todos os registros do arquivo.

## RN04 — Reimportação

O sistema deverá permitir a reimportação de relatórios.

Quando uma nova importação corresponder a dados já existentes para a mesma competência e UPS, o sistema deverá atualizar ou reprocessar os registros relacionados, evitando duplicidades.

A estratégia técnica definitiva de identificação de uma importação repetida será definida durante a implementação do módulo de importação.

Enquanto essa estratégia não estiver implementada, uma segunda importação para a mesma combinação de competência, UPS e tipo de relatório deverá ser bloqueada, sem substituir ou duplicar estoques silenciosamente.

## RN05 — Preservação da origem

Todo registro de estoque deverá manter sua origem.

O sistema deverá preservar a relação do registro com:

- medicamento;
- UPS;
- competência;
- lote, quando disponível;
- importação responsável pelo registro.

A consolidação dos estoques não deverá eliminar essas informações individuais.

## RN06 — Consolidação das UPS

O estoque convencional de um medicamento será obtido pela consolidação dos registros
das UPS configuradas com `compoe_estoque_convencional=True`. A Farmácia de Manipulação
deverá ser configurada com esse indicador desativado, sem identificação por nome no
código-fonte.

O valor consolidado será calculado pelo sistema a partir dos registros individuais, sem necessidade de criar um estoque consolidado independente no banco de dados.

## RN07 — Medicamentos manipulados

Medicamento manipulado não constitui uma classe farmacológica independente.

A origem de um registro de estoque manipulado continua sendo representada
administrativamente pela UPS correspondente. Para a disponibilidade pública,
porém, a identificação de que o medicamento é manipulado será determinada pela
classificação/tag `MANIPULADO`, conforme a RN41, e não pela simples existência de saldo,
lote ou histórico na UPS de manipulação.

Um mesmo medicamento e uma mesma apresentação podem existir simultaneamente em estoque convencional e em estoque proveniente da Farmácia de Manipulação.

Essa situação não deverá ser considerada duplicidade ou erro.

## RN08 — Código do medicamento no G-MUS

O código do G-MUS deverá ser preservado como identificador externo do medicamento/apresentação.

Exemplo:

- `115.1` — Dipirona 500 mg;
- `115.2` — Dipirona 500 mg/ml;
- `115.3` — Dipirona 500 mg/ml, ampola de 2 ml.

O StockFlow não deverá depender exclusivamente da decomposição desse código para interpretar a apresentação do medicamento.

## RN09 — Apresentações dos medicamentos

A descrição original da apresentação fornecida pelo G-MUS deverá ser preservada.

O sistema deverá permitir medicamentos com apresentações complexas, incluindo:

- diferentes concentrações;
- diferentes formas farmacêuticas;
- diferentes volumes;
- combinações de dois ou mais princípios ativos.

## RN10 — Princípios ativos

Um medicamento poderá possuir um ou mais princípios ativos.

Um mesmo princípio ativo poderá estar relacionado a diferentes medicamentos/apresentações.

A relação entre medicamentos e princípios ativos deverá permitir associação muitos-para-muitos.

## RN11 — Subgrupos do G-MUS

Quando o relatório informar um subgrupo do G-MUS, essa informação deverá ser armazenada.

O subgrupo poderá estar ausente em determinados medicamentos.

O StockFlow não deverá criar automaticamente um subgrupo inexistente no relatório.

## RN12 — Classificações personalizáveis

O StockFlow permitirá classificações próprias e personalizáveis para os medicamentos.

As classificações serão independentes dos subgrupos provenientes do G-MUS.

Uma classificação poderá possuir, entre outras informações:

- nome;
- cor;
- descrição;
- estado ativo/inativo.

Um medicamento poderá possuir mais de uma classificação.

## RN13 — Uso das classificações

As classificações poderão ser utilizadas para organização e filtragem da interface administrativa.

A interface poderá apresentar uma legenda visual associando cores às classificações cadastradas.

## RN14 — Lotes

Um medicamento poderá possuir vários lotes simultaneamente.

Cada lote deverá preservar seu código e sua data de validade, quando disponíveis.

O mesmo código de lote poderá aparecer em diferentes registros de estoque, inclusive em diferentes UPS, sem que isso seja automaticamente considerado erro.

## RN15 — Quantidade por lote e UPS

A quantidade pertence ao registro de estoque, e não exclusivamente ao lote.

Isso permite que um mesmo lote esteja presente em mais de uma UPS com quantidades diferentes.

## RN16 — UPS como localização do estoque

A UPS/unidade fornecida nos metadados do relatório de inventário representa a localização e a origem do estoque e deverá ser preservada durante a importação.

Não existe uma entidade de localização separada nesse contexto. O sistema deverá permitir consultar o estoque por UPS.

## RN16-A — Quantidades do inventário

O campo `Qtde Virt.` do relatório de inventário representa a quantidade de estoque utilizada pelo StockFlow.

O campo `Qtde R.` não é utilizado pelo StockFlow. Ele poderá ser reconhecido pelo parser apenas para interpretar a estrutura do CSV, mas seu valor não deverá integrar os dados normalizados do domínio, gerar inconsistências ou ser persistido.

Como o inventário representa saldo de estoque, uma `Qtde Virt.` negativa deverá ser
classificada como inconsistência `error`. A linha correspondente não deverá gerar um
registro de estoque válido.

## RN17 — Competência

A competência do relatório representa o período de referência dos dados e deverá ser armazenada separadamente da data de importação.

Exemplo:

- competência: agosto de 2026;
- data de importação: setembro de 2026.

A data de importação não deverá ser utilizada como substituta da competência.

## RN18 — Histórico de estoque

O histórico mensal de estoque será obtido a partir dos registros armazenados por competência.

Não será necessária uma tabela independente apenas para histórico de estoque, pois os registros de estoque associados às competências já preservam essa evolução temporal.

## RN19 — Registros com quantidade zero

Medicamentos com quantidade igual a zero poderão ser armazenados quando forem apresentados dessa forma no relatório importado.

O relatório do G-MUS pode omitir itens com saldo zero quando gerado com `Imp. Zero? Não`.
Por isso, quando existir uma competência completa, a ausência de registro de estoque
convencional para um medicamento nessa competência representará saldo convencional zero
para a disponibilidade pública. Essa inferência não poderá ser aplicada quando
não existir competência completa.

A disponibilidade pública será determinada pelas regras de disponibilidade do StockFlow.

## RN20 — Registros incompletos ou inconsistentes

Caso o arquivo contenha linhas incompletas ou inconsistentes, o sistema não deverá criar silenciosamente registros inválidos.

Esses casos deverão ser identificados durante o processamento e tratados de forma controlada, permitindo registro do problema para análise administrativa.

Uma inconsistência em um registro não deverá necessariamente impedir o processamento de todo o arquivo, desde que seja possível realizar a importação dos demais registros com segurança.

As inconsistências relevantes deverão ser classificadas como `error` ou `warning`. Somente um `error` associado a uma linha deverá impedir a persistência daquela linha. Um `warning` deverá permitir o processamento e resultar em importação concluída com alertas.

## RN21 — Módulo administrativo

O módulo administrativo será restrito a usuários autenticados e autorizados.

Estão previstos poucos usuários administrativos, inicialmente vinculados principalmente às farmacêuticas responsáveis pelo estoque.

## RN22 — Sessões administrativas

O sistema deverá controlar sessões dos usuários administrativos.

As sessões deverão estar vinculadas ao usuário correspondente e possuir mecanismo de expiração ou encerramento.

## RN23 — Senhas

Senhas de usuários não poderão ser armazenadas em texto simples.

O armazenamento deverá utilizar mecanismo seguro de hash de senha disponibilizado pelo framework utilizado no back-end.

## RN24 — Módulo público

O módulo público não exigirá login.

O cidadão poderá realizar a consulta individual de medicamentos.

Não será disponibilizada ao público a seleção em massa de medicamentos existente no módulo administrativo.

## RN25 — Informações públicas

O módulo público deverá apresentar somente informações definidas como públicas.

Na API pública, deverão ser disponibilizados somente:

- código G-MUS;
- descrição/apresentação;
- unidade;
- situação de disponibilidade.

Informações administrativas, como quantidade exata em estoque, lote, validade,
competência, importação, usuário, subgrupo, classificações e UPS de origem, não deverão
ser exibidas publicamente. Princípio ativo permanece previsto para evolução futura.

## RN26 — Consulta administrativa

O módulo administrativo deverá permitir consulta mais detalhada dos medicamentos.

A consulta poderá incluir:

- estoque por UPS;
- estoque consolidado;
- histórico por competência;
- lotes;
- validades;
- classificações;
- subgrupos;
- filtros administrativos.

## RN27 — Seleção de múltiplos medicamentos

O usuário administrativo poderá selecionar múltiplos medicamentos para exibição conjunta.

A funcionalidade deverá ser adequada ao volume de centenas de medicamentos cadastrados, permitindo seleção e filtragem sem exigir consulta individual de cada item.

## RN28 — Filtros administrativos

A interface administrativa deverá permitir filtros que auxiliem a análise de grandes quantidades de medicamentos.

Os filtros poderão considerar, conforme os dados disponíveis:

- classificação;
- subgrupo;
- UPS;
- disponibilidade;
- princípio ativo;
- apresentação.

## RN29 — Indicador visual de estoque

A situação do estoque deverá possuir representação visual simplificada em três níveis:

- verde;
- amarelo;
- vermelho.

Os limites utilizados para cada nível deverão ser definidos como parâmetros do sistema e não permanecer fixos diretamente no código-fonte.

## RN30 — Parâmetros de cálculo

Os cálculos utilizados para apoio à gestão deverão ser configuráveis.

Os valores atualmente utilizados pela farmacêutica servirão como valores iniciais do sistema, mas poderão ser alterados posteriormente por usuários autorizados.

## RN31 — Margem de segurança

O cálculo de necessidade de compra deverá permitir a utilização de uma margem de segurança configurável.

A margem não deverá ser fixada permanentemente em um único percentual.

## RN32 — Cobertura de estoque

O sistema deverá permitir estimar por quanto tempo o estoque disponível poderá atender ao consumo esperado.

Essa estimativa será baseada nos valores de estoque e nas regras de média de consumo definidas para o StockFlow.

## RN33 — Média de consumo

A média de consumo deverá considerar os meses anteriores disponíveis do ano corrente.

Quando não houver histórico suficiente no ano atual, poderão ser utilizados dados do ano anterior conforme a regra definida para o cálculo.

Meses com consumo igual a zero deverão participar do cálculo da média.

## RN34 — Comparação entre períodos

O sistema deverá permitir comparação entre o comportamento de consumo do período atual e períodos anteriores.

Essa funcionalidade poderá ser utilizada pela farmacêutica para identificar alterações relevantes no consumo e efeitos de sazonalidade.

## RN35 — Fonte definitiva para consumo

A regra técnica definitiva para obtenção dos valores de consumo mensal ainda deverá ser validada durante o desenvolvimento.

O relatório de inventário será utilizado como fonte principal para estoque mensal, lotes, validade, UPS de origem e demais informações disponíveis.

Não deverá ser calculado consumo real apenas pela diferença entre dois estoques mensais quando existirem entradas ou outras movimentações que possam alterar o saldo.

## RN36 — Disponibilidade pública

A disponibilidade apresentada ao cidadão deverá ser calculada pelo StockFlow a partir da competência considerada atual e dos registros das UPS.

A competência válida para esse cálculo será a competência completa mais recente. Se a
competência cronologicamente mais recente estiver incompleta, deverá ser usada a
competência completa anterior mais recente. Se nenhuma competência completa existir, a
situação pública dos medicamentos sem a tag ativa `MANIPULADO` será
`Disponibilidade não informada`.

O cálculo deverá consolidar internamente os estoques das UPS. O cidadão não deverá
visualizar o valor numérico utilizado, a UPS de origem nem qual UPS possui o medicamento.

A disponibilidade integra a resposta da API pública de medicamentos como situação
textual, sem expor os dados administrativos usados no cálculo.

## RN37 — Rastreabilidade das importações

Cada importação deverá registrar informações que permitam sua rastreabilidade, incluindo:

- arquivo importado;
- hash SHA-256 do arquivo;
- data da importação;
- usuário responsável;
- competência;
- UPS;
- status do processamento.

Os status persistidos terão a seguinte semântica:

- `concluida`: todos os registros foram processados sem warnings ou rejeições;
- `concluida_com_alertas`: existem warnings não bloqueantes, mas nenhum registro foi rejeitado;
- `concluida_parcial`: uma ou mais linhas ou registros foram rejeitados.

Somente `concluida` e `concluida_com_alertas` poderão completar uma competência. Falhas
inesperadas deverão provocar rollback integral e não deixar dados parcialmente
persistidos.

## RN38 — Integridade dos dados

O sistema deverá evitar duplicidades e inconsistências entre medicamento, competência, UPS, lote e importação.

As regras específicas de restrições `UNIQUE` e validações do banco serão definidas durante a implementação física do banco de dados.

## RN39 — Evolução do sistema

O modelo deverá permitir expansão futura sem necessidade de alterações estruturais desnecessárias.

Novas UPS, classificações e outras informações configuráveis deverão, sempre que possível, ser cadastradas como dados e não permanecer fixadas no código-fonte.

## RN40 — Dados do G-MUS

Os dados importados do G-MUS deverão ser preservados em sua forma original sempre que isso for relevante para rastreabilidade e conferência.

Tratamentos, padronizações e informações adicionais do StockFlow deverão complementar os dados de origem, evitando apagar informações necessárias para auditoria ou verificação.

## RN41 — Disponibilidade pública de medicamentos manipulados

`MANIPULADO` é uma classificação/tag associada ao medicamento. Um medicamento não se
torna uma entidade diferente por possuir essa tag: sua apresentação e seu código G-MUS
continuam identificando normalmente o mesmo medicamento.

A situação pública especial de medicamento manipulado deverá ser determinada pela
existência da classificação/tag ativa `MANIPULADO` no medicamento. Uma classificação
com `ativo=False` não deverá acionar essa regra. A tag ativa não dependerá de
quantidade positiva, lote antigo ou histórico de estoque na UPS de manipulação. Assim,
todo medicamento com essa tag ativa deverá receber a mensagem especial, inclusive quando
possuir estoque convencional positivo ou quando o estoque registrado estiver zerado.

A ordem de decisão da disponibilidade pública é:

1. Se o medicamento possuir a tag ativa `MANIPULADO`, apresentar exatamente
   `Disponível sob manipulação, confirmar disponibilidade`, independentemente de haver
   estoque convencional positivo ou de o estoque registrado estar zerado.
2. Se o medicamento não possuir a tag ativa `MANIPULADO` e não existir competência
   completa, apresentar `Disponibilidade não informada`.
3. Se o medicamento não possuir a tag ativa `MANIPULADO`, existir competência completa
   e houver estoque convencional
   positivo considerado válido para a consulta pública, apresentar `Disponível`.
4. Se o medicamento não possuir a tag ativa `MANIPULADO`, existir competência completa
   e não houver estoque convencional positivo, apresentar `Indisponível`.

A existência de lote antigo, saldo positivo anterior ou simples histórico na UPS de
manipulação não garante que o medicamento esteja sendo manipulado atualmente e não
deverá ser usada para afirmar disponibilidade.

A tag poderá ser usada internamente no cálculo, mas o cidadão deverá receber somente a
situação pública resultante. O módulo público não deverá revelar UPS, quantidade por
UPS, quantidade consolidada, estoque da UPS de manipulação, lotes, validade,
competência, importação ou outros dados administrativos usados na decisão. A UPS
continuará sendo informação exclusivamente administrativa.

Licitações, contratos e processos de compra não fazem parte do escopo do StockFlow. O
StockFlow não deverá criar funcionalidades, models, tabelas, campos, requisitos,
integrações ou módulos para controlar essas informações como parte desta regra.
