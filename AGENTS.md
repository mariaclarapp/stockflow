# AGENTS.md — StockFlow

## 1. Sobre o projeto

StockFlow é um sistema web desenvolvido como Trabalho de Graduação (TG) da FATEC Ourinhos.

O sistema tem como objetivo auxiliar a gestão, consolidação e consulta do estoque de medicamentos da Farmácia Municipal de Ribeirão Claro.

Antes de implementar ou alterar funcionalidades, consulte a documentação existente em `docs/`.

A documentação do projeto é a principal referência para requisitos, regras de negócio e modelagem.

---

## 2. Tecnologias definidas

### Back-end
- Python
- Django
- Django REST Framework
- MySQL

### Front-end
- React
- JavaScript

Não substituir essas tecnologias sem solicitação explícita.

Não utilizar TypeScript.

---

## 3. Arquitetura

O StockFlow possui um único sistema web com dois contextos de acesso:

### Módulo administrativo
Exige autenticação e é destinado aos usuários autorizados da farmácia.

### Módulo público
Não exige autenticação e permite a consulta pública de medicamentos.

O front-end React comunica-se com o back-end Django por meio da API da aplicação.

O MySQL é utilizado para persistência.

---

## 4. Sistema G-MUS

O G-MUS é o sistema utilizado atualmente pela Farmácia Municipal.

O StockFlow NÃO possui acesso direto ao banco de dados do G-MUS.

O StockFlow NÃO deve implementar integração direta com o G-MUS sem uma mudança explícita nos requisitos.

Os dados são obtidos por relatórios exportados do G-MUS e posteriormente importados pelo usuário no StockFlow.

O formato escolhido para importação é CSV.

Nunca assumir a existência de API, acesso ao banco ou integração automática com o G-MUS.

---

## 5. Dados reais

Não versionar relatórios reais da Farmácia Municipal.

Não versionar dados sensíveis, credenciais ou arquivos `.env`.

Relatórios reais do G-MUS devem permanecer fora do Git.

Quando forem necessários arquivos para testes, utilizar dados fictícios ou devidamente anonimizados.

Respeitar o `.gitignore`.

---

## 6. Estoque e UPS

O estoque é organizado por competência.

As informações importadas devem preservar a UPS de origem.

O sistema trabalha atualmente com três UPS utilizadas pela Farmácia Municipal.

Um mesmo medicamento/apresentação pode existir simultaneamente em mais de uma UPS.

Isso não representa duplicidade.

Medicamentos provenientes da Farmácia de Manipulação não constituem uma classe terapêutica diferente.

Por exemplo, uma mesma apresentação de dipirona pode existir tanto no estoque convencional quanto na Farmácia de Manipulação.

---

## 7. Relatório de inventário

O relatório de inventário é uma das fontes de dados já confirmadas para o projeto.

Ele contém informações relevantes como:

- medicamento;
- código;
- UPS;
- competência;
- lote;
- validade;
- quantidade;
- outras informações existentes no relatório.

A UPS/unidade do relatório representa a localização e a origem do estoque. Não criar
uma entidade de localização separada para o inventário.

---

## 8. Consolidação

O estoque consolidado deve ser calculado a partir dos registros individuais das UPS.

Não criar uma tabela ou entidade de estoque consolidado apenas para armazenar o resultado calculado, salvo se uma futura decisão de arquitetura determinar explicitamente isso.

Os dados individuais das UPS devem continuar preservados.

---

## 9. Histórico

O histórico de estoque é obtido a partir dos registros associados às diferentes competências.

Evitar criar estruturas redundantes quando a informação já puder ser derivada dos registros mensais armazenados.

---

## 10. Lotes, validade e UPS

Um medicamento pode possuir múltiplos lotes.

Os registros devem preservar, quando disponíveis:

- lote;
- validade;
- quantidade;
- UPS;
- competência.

A quantidade deve estar associada ao registro de estoque correspondente.

Não assumir que um lote existe em apenas uma UPS.

---

## 11. Classificações

O StockFlow permitirá classificações personalizáveis dos medicamentos.

Essas classificações são diferentes dos subgrupos provenientes do G-MUS.

Não tratar medicamento manipulado como uma classificação terapêutica.

---

## 12. Cálculos

Os cálculos utilizados pela farmacêutica já possuem valores e regras-base existentes.

O sistema deverá reproduzir inicialmente esses valores-base e permitir que determinados parâmetros sejam personalizados.

Não inventar novas fórmulas ou regras de cálculo.

Quando a documentação não for suficiente para determinar uma fórmula, interromper aquela implementação e indicar a informação faltante.

A fonte definitiva dos dados de consumo ainda deve ser validada.

Não inferir consumo real simplesmente pela diferença entre dois estoques mensais quando entradas ou outras movimentações puderem alterar o saldo.

---

## 13. Consulta pública

O módulo público não exige autenticação.

O cidadão poderá consultar medicamentos e sua disponibilidade.

Informações administrativas não devem ser expostas publicamente.

Não exibir publicamente, salvo alteração explícita dos requisitos:

- quantidade exata em estoque;
- lote;
- validade;
- UPS de origem;
- informações administrativas internas.

---

## 14. Segurança

Senhas nunca devem ser armazenadas em texto simples.

Utilizar os mecanismos seguros de autenticação e hashing disponibilizados pelo Django.

Segredos, credenciais e configurações locais devem ser obtidos por variáveis de ambiente.

Nunca inserir senhas, chaves ou credenciais reais no código-fonte.

---

## 15. Modelagem

A modelagem existente está localizada em `docs/diagramas/`.

Atualmente existem artefatos para:

- DER;
- diagrama de classes;
- casos de uso;
- diagramas de sequência;
- arquitetura geral.

Antes de criar models ou alterar estruturas persistentes, consultar o DER, o diagrama de classes e `docs/requisitos/regras-de-negocio.md`.

Não modificar silenciosamente a modelagem para adequá-la ao código.

Caso seja necessária uma mudança estrutural, explicar primeiro a incompatibilidade encontrada.

---

## 16. Requisitos

Consultar obrigatoriamente:

- `docs/requisitos/requisitos-funcionais.md`
- `docs/requisitos/requisitos-nao-funcionais.md`
- `docs/requisitos/regras-de-negocio.md`

Não criar funcionalidades apenas porque parecem úteis.

O projeto é um TG e o escopo deve permanecer controlado.

Funcionalidades novas devem ser implementadas somente quando estiverem previstas nos requisitos ou forem explicitamente solicitadas.

---

## 17. Código

Priorizar:

- código legível;
- responsabilidades bem separadas;
- nomes descritivos;
- validação de entrada;
- tratamento explícito de erros;
- baixa duplicação;
- testes para regras de negócio importantes.

Evitar abstrações desnecessárias para o tamanho atual do projeto.

Não implementar funcionalidades futuras antecipadamente.

---

## 18. Testes

Funcionalidades relevantes devem possuir testes sempre que aplicável.

Priorizar testes para:

- importação de CSV;
- prevenção de duplicidades;
- reimportação;
- consolidação;
- autenticação;
- permissões;
- disponibilidade;
- cálculos de estoque.

Não alterar uma regra de negócio apenas para fazer um teste passar.

---

## 19. Git

A branch `main` representa a versão estável e é protegida.

O desenvolvimento ocorre a partir de `develop`.

Utilizar branches de trabalho quando apropriado, por exemplo:

- `feature/...`
- `fix/...`
- `docs/...`

Não fazer merge ou push diretamente para `main`.

Não criar commits ou realizar push sem solicitação explícita do usuário.

Antes de realizar alterações significativas, verificar a branch atual.

---

## 20. Commits

Quando solicitado a criar commits, utilizar mensagens claras, por exemplo:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `test: ...`
- `refactor: ...`
- `chore: ...`

---

## 21. Antes de implementar

Antes de iniciar uma tarefa:

1. Ler este `AGENTS.md`.
2. Consultar os documentos relevantes em `docs/`.
3. Examinar a implementação existente.
4. Verificar se a tarefa é compatível com os requisitos e a modelagem.
5. Não preencher lacunas de regra de negócio com suposições.

Quando houver conflito entre código e documentação, informar o conflito antes de alterar uma regra de negócio.

---

## 22. Ao finalizar uma tarefa

Sempre que possível:

1. executar os testes relevantes;
2. executar verificações do framework;
3. verificar arquivos modificados;
4. informar resumidamente o que foi alterado;
5. informar testes/comandos executados;
6. informar qualquer pendência ou decisão de negócio necessária.

Não declarar que algo funciona sem ter executado a verificação correspondente.

---

## 23. Documentação sincronizada

Alterações futuras na API ou no banco de dados devem manter a documentação correspondente em `docs/api/` e `docs/banco-de-dados/` sincronizada com a implementação.
