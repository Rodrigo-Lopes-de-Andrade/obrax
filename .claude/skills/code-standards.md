---
name: code-standards
description: Extrai e documenta os padrões de código de um projeto – convenções de naming, estrutura de pastas, estilo de imports, padrão de error handling e uso de tipos. Use sempre que o usuário pedir coisas como "quais são os padrões do código?", "documente as convenções", "code standards", "como a gente nomeia coisas aqui?", "me dá um guia de estilo desse repo", ou quiser checar se uma mudança está seguindo as convenções do projeto. Também use quando o usuário estiver onboardando alguém novo no repo e precisar de um resumo dos padrões.
allowed-tools: Read, Glob, Grep
---

# Code Standards
Skill para varrer o código existente e produzir um guia de estilo vivo baseado no que o projeto já faz – não no que deveria fazer. A ideia é descobrir a convenção real, não inventar uma.

## Quando usar
Dispare essa skill quando o usuário:

Pedir um documento de padrões ("code standards", "guia de estilo", "convenções do projeto").

Perguntar como algo é nomeado/organizado/tratado neste repo.

Quiser validar se um arquivo ou mudança segue o padrão do resto.

Estiver preparando onboarding de alguém novo.

## O que analisar
Cobrir estes cinco eixos, nessa ordem:

### 1. Naming & Patterns

Convenção de nomes de arquivos (kebab-case, snake_case, PascalCase, camelCase).

Nomes de classes, funções, variáveis, constantes.

Sufixos/prefixos usados (Service, Repository, use*, is*, *_dto, etc.).

Padrões de nomes de testes (test_*.py, *.spec.ts, *.test.tsx).

### 2. Estrutura de arquivos

Árvore de pastas principal e o papel de cada uma.

Onde modelos, schemas/DTOs, rotas/controllers, services, testes, utils e configs moram.

Divisão por domínio vs por tipo (ex.: features/user/ vs controllers/ + services/).

### 3. Imports

Ordem de imports (stdlib → terceiros → locais; ou conforme o linter configurado).

Uso de aliases (@/components, ~/lib) vs paths relativos.

Wildcards e re-exports (export * from ...) – usados ou evitados?

Presença de isort, ruff, eslint-plugin-import e como estão configurados.

### 4. Error handling

Exceções customizadas vs nativas.

Camada onde erros são capturados (handler global, middleware, try/catch in-loco).

Formato do payload de erro devolvido pelo backend.

Uso de Result/Either, exceptions, ou retorno por tupla.

Padrão de logging em erro (nível, contexto, traceback).

### 5. Tipos

Rigor: strict: true no TS? mypy ativo? Quais módulos têm anotação completa?

Uso de DTOs/Schemas para contrato externo vs modelos internos.

Tipos genéricos, Protocol/interfaces, TypedDict, dataclass/BaseModel.

Evitação (ou tolerância) de any, # type: ignore, as unknown as X.

## Como conduzir (passo a passo)
Mapeie a raiz do repo com Glob: /*.{py,ts,tsx,js,jsx,go,rs,java,kt} (ajuste pelas linguagens reais). /package.json, /pyproject.toml, /eslintrc*, /ruff.toml, /mypy.ini para pegar config de linter/formatter.

Leia os arquivos de config de lint/type primeiro – eles já declaram metade do padrão.

Pegue 3-5 arquivos representativos por camada (ex.: 1 controller, 1 service, 1 model, 1 schema, 1 teste) e leia-os por inteiro ou por amostra.

Use Grep para confirmar padrões suspeitos, por exemplo:

^from \.\. para imports relativos profundos.

raise HTTPException|throw new Error|return Err para estilo de erro.

class [A-Z]\w+(Service|Repository|Controller) para sufixos de classe.

\s*any|b# type: ignore para escapes de tipo.

Quando houver conflito entre amostras, prefira o padrão majoritário e registre a exceção (ex.: "90% dos routers usam async def; 2 rotas legadas em legacy/ ainda usam funções síncronas").

Nunca invente regra que não está no código. Se um eixo estiver vazio ou inconsistente, diga isso explicitamente: "sem padrão consolidado para X".

## Formato da saída
Produza um CODE_STANDARDS.md na raiz do projeto (ou imprima no chat se o usuário preferir), com cinco seções nessa ordem e sempre em prosa curta + exemplos reais do repositório:

# Code Standards

> Documento gerado a partir do código existente em <data>. Reflete o que o repo faz hoje, não o que deveria fazer.

## 1. Naming & Patterns

Exemplo: src/services/user_service.py - sufixo _service em todos os arquivos de services/.

## 2. Estrutura de arquivos ... (seguindo até a seção 5)

## Exceções e pontos cinzas

<lugares onde o padrão não é uniforme, com caminho dos arquivos divergentes>

Regras pro documento:

Cada regra referencia pelo menos um arquivo real como evidência (path + linha opcional).

Frases curtas, sem enrolar.

Se não houver evidência suficiente pra afirmar algo, escreva "não há padrão claro".

No fim, sempre a seção Exceções e pontos cinzas pra catalogar o que destoa – é tão útil quanto a regra.

Modo "review"
Se o usuário não pedir o documento e sim uma revisão ("essa mudança segue o padrão?"), pule o passo de produzir arquivo. Em vez disso:

Identifique que arquivos mudaram (perguntar ao usuário, ou usar git diff se aplicável).

Compare cada arquivo mudado contra o padrão majoritário dos seus pares no mesmo diretório.

Devolva uma lista curta: √ o que está conforme, X o que destoa, com path + sugestão.

O que NÃO fazer

Não proponha mudanças no código; essa skill só observa e documenta.

Não invente convenções modernas ("o ideal seria..."). Fale só do que está no repo.

Não escreva um guia genérico de boas práticas. O valor é ser específico deste repo.

Não ultrapasse o escopo das ferramentas permitidas (Read, Glob, Grep). Se precisar rodar algo, avise o usuário pra rodar manualmente.
