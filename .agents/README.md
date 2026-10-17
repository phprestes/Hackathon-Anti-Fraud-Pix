# .agents

Material para agentes de código, complementar ao [`AGENTS.md`](../AGENTS.md). A API e os testes não leem esta pasta.

```
.agents/
└── skills/                   receitas passo a passo, uma pasta por tarefa
    ├── nova-regra/           regra antifraude nova ou calibragem, com TDD
    ├── novo-erro/            recusa nova da API com código QIT
    ├── nova-decisao/         ADR novo ou mudança de status
    ├── registrar-mudanca/    linha no CHANGELOG.md ao fim de toda tarefa
    └── revisar-mudanca/      checklist antes de declarar pronto
```

Cada skill é um `SKILL.md` com front-matter `name` e `description` (formato [Agent Skills](https://agentskills.io)): a `description` diz quando usar, o corpo diz como. Skill nova: copie uma pasta, troque o front-matter, liste aqui e registre no [CHANGELOG](../CHANGELOG.md). Ferramentas que procuram skills em outra pasta usam um link simbólico local ([docs/trabalhando-com-ia.md](../docs/trabalhando-com-ia.md)).
