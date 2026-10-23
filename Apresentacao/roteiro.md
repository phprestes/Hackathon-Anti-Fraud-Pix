# Roteiro da apresentação (7 min + 3 min de perguntas)

Slides: `slides.pdf` (18 páginas). Para regerar depois de editar o `slides.html`:

```bash
google-chrome --headless=new --no-pdf-header-footer --print-to-pdf=slides.pdf "file://$PWD/slides.html"
```

## Bloco 1 · Problema e abordagem (0:45)

1. **Capa (0:05).** "Somos o Hackathon-Anti-Fraud-Pix: um motor que decide, em milissegundos, se um Pix segue, pede confirmação ou é barrado."
2. **Não reinventamos a roda (0:20).** "Somos iniciantes em antifraude. Em vez de inventar limites, fomos à literatura, às normas do Banco Central e a um simulador aberto. Daí saiu uma arquitetura em que cada regra entra e sai sem mexer no resto, e cada banco recalibra para os seus clientes."
3. **O desafio (0:20).** "Quase toda a literatura é de cartão, com estorno e décadas de dados. Pix é instantâneo e não tem base real aberta. A pergunta do projeto foi: as técnicas clássicas funcionam no Pix? Medimos."

## Bloco 2 · Regras (1:30)

4. **Fluxo da decisão (0:20).** "Todo Pix passa por todas as 15 regras; vence a mais severa. Duas dúvidas não viram bloqueio: barrar exige um golpe reconhecível. Toda resposta diz o porquê em português."
5. **Critério (0:25).** "Uma regra só entra se pega fraude no simulador, se segue o BCB ou se cobre um golpe que o simulador não gera. Desligamos uma de cada vez e tiramos três que incomodavam mais do que protegiam."
6. **Três regras (0:25).** "A que mais protege é a do primeiro Pix alto para alguém novo: golpe manda dinheiro para quem a vítima nunca pagou. Aparelho novo é o primeiro passo de conta tomada. E 'rápido demais' é relativo a cada cliente."
7. **Bolton & Hand (0:20).** "Organizamos a literatura em quatro níveis. O individual é o coração do motor; o de pares medimos e descartamos; a ruptura está só aproximada; os rótulos externos simulamos com o MED."

## Bloco 3 · Validação (1:15)

8. **Método (0:25).** "No nosso simulador as regras pegavam 98,5%: corrigir a própria prova. Por isso medimos no PixSim, de outros autores. Um cenário escolhe os parâmetros, outro confirma."
9. **Resultados (0:25).** "Cerca de 3% dos legítimos pedem confirmação, quase nenhum é barrado. Conta tomada é pega em 99% dos golpes. O prejuízo esperado cai 21% em relação a não ter motor."
10. **Limite honesto (0:25).** "O ponto fraco é engenharia social: a vítima faz o Pix e pode confirmar o 2FA. Se mais de 40% confirmarem, o motor passa a custar mais que nada. É o próximo problema a atacar."

## Bloco 4 · Arquitetura (1:30)

11. **Rápido × de fundo (0:30).** "As regras decidem dentro da requisição. Em paralelo, um worker olha a rede de quem paga quem e grava a reputação de cada conta; a API só lê o score pronto."
12. **Um motor, dois lugares (0:30).** "O mesmo código roda na API e num backtest em memória, porque o motor pergunta o histórico sempre pela mesma 'tomada'. Rodamos 255 mil Pix em 100 segundos, e a paridade com a API dá zero divergências."
13. **Base Service (0:30).** "Mantivemos as camadas das aulas e só acrescentamos o motor. Idempotência por id, banco só com INSERT, logger com id da requisição e 113 testes pela própria API."

## Bloco 5 · ML e retroalimentação (1:00)

14. **Modo sombra (0:30).** "Cinco modelos rodam em todo Pix, mas só opinam. Com a qualidade típica de dado real, um modelo custaria 7% a mais que as regras. Ligar é uma linha de código; falta rótulo real."
15. **MED (0:30).** "O rótulo vem da vítima reclamando no MED, dias depois. Simulamos esse ciclo no backtest e achamos o viés: o que o motor barra nunca vira reclamação, então o modelo aprende a esquecer o que já é barrado."

## Bloco 6 · Software e próximos passos (0:45)

16. **Documentação (0:20).** "Cada decisão é uma ADR, com as alternativas descartadas. Diagramas C4, CHANGELOG e um AGENTS.md que deixa o projeto pronto para agentes de IA."
17. **Próximos passos (0:25).** "Rota de desfechos do MED e do DICT, inferência de rejeitados, janelas em streaming, scores externos e dados de sessão."
18. **Referências.** Só exibir.

**Total previsto: 6:45.**

## Perguntas para ensaiar

O capítulo "Perguntas prováveis da banca" do relatório (`Hackathon/docs/relatorio/relatorio.pdf`) tem as respostas com números. As mais prováveis:

- Por que regras decidem e não um modelo?
- Por que manter o limite noturno de R$ 1.000 se o simulador preferia outro valor?
- Para que servem regras que nunca disparam no simulador?
- Houve vazamento de dados? O AUC de 0,99 não é bom demais?
- Como o motor lida com engenharia social?
- Qual a latência e quanto aguenta? (resposta honesta: motor 0,6 ms por Pix; não houve teste de carga)
- Tem concept drift? (PSI e retreino só offline; detecção em produção é próximo passo)
- O que é o HistoryPort? O que é inferência de rejeitados?
