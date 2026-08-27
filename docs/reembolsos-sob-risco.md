# Reembolsos sob risco

## Escopo

Case independente de portfólio sobre a jornada de contestação e reembolso em um marketplace fictício de delivery. A experiência é familiar a usuários de aplicativos do setor, mas não representa auditoria, diagnóstico ou produto oficial de nenhuma empresa.

Todos os pedidos, clientes, lojas, dispositivos, regras, valores e resultados são sintéticos.

## Pergunta de negócio

Como reduzir perdas com reembolsos potencialmente indevidos sem aumentar o atrito de clientes legítimos?

## Decisão suportada

Definir uma política de triagem que combine aprovação rápida, solicitação de evidência e revisão humana conforme risco e impacto financeiro.

## Hipóteses

1. Selecionar todos os itens do pedido concentra maior exposição financeira.
2. Reincidência em janela curta aumenta o risco estimado.
3. A ausência de resposta da loja reduz a informação disponível para decisão.
4. Evidência incompatível com os itens contestados aumenta a necessidade de revisão.
5. Contas relacionadas por dispositivo ou pagamento podem indicar comportamento coordenado.
6. Restrições indiscriminadas podem reduzir perdas e simultaneamente prejudicar clientes legítimos.

As hipóteses devem ser validadas. Associação não representa causalidade e risco não equivale a fraude comprovada.

## Base sintética resumida

- Período: janeiro a junho de 2025.
- Pedidos concluídos: 60.000.
- Contestações: 4.800.
- Valor reembolsado: R$ 328.600.
- Exposição financeira estimada: R$ 74.600.
- Solicitações sem resposta da loja: 1.950.
- Solicitações encaminhadas para revisão manual: 826.

## Métricas

### Taxa de contestação

`Contestações / Pedidos concluídos`

### Taxa de ausência de resposta

`Contestações sem resposta da loja / Contestações abertas`

### Participação da exposição

`Exposição financeira estimada / Valor reembolsado`

### Economia líquida potencial

`Perda evitada - custo incremental de revisão - impacto estimado sobre clientes legítimos`

## Cenários

### Conservador

Revisa somente solicitações simultaneamente classificadas como alto risco e alto impacto.

### Equilibrado

Mantém aprovação rápida para baixo risco, solicita evidência contextual no risco intermediário e direciona alto risco para revisão humana.

### Restritivo

Aumenta significativamente a revisão manual. Pode reduzir a exposição bruta, mas amplia custos e falsos positivos.

## Recomendação

Executar um piloto controlado do cenário equilibrado. Monitorar economia líquida, falsos positivos, tempo de resolução, reincidência, satisfação do cliente e volume operacional antes de ampliar a política.

## Governança

- Não utilizar atributos protegidos ou dados pessoais desnecessários.
- Manter identificadores anonimizados.
- Tratar o score como priorização, não como acusação.
- Exigir revisão humana nos casos de alto impacto.
- Disponibilizar recurso para clientes legítimos.
- Realizar auditoria periódica de vieses e qualidade das regras.

## Método de elaboração

1. Registrar a experiência observada sem tratá-la como evidência conclusiva.
2. Mapear a jornada pública de contestação e seus participantes.
3. Converter a observação em hipóteses testáveis.
4. Definir granularidade, campos, qualidade e anonimização dos dados.
5. Separar fraude, erro operacional, desperdício e caso inconclusivo.
6. Simular políticas considerando perdas evitadas, revisão e impacto em clientes legítimos.
7. Validar a política em modo de observação e piloto controlado.
8. Monitorar economia líquida, falsos positivos, tempo, recursos e reclamações externas.

## Referências oficiais

- [Lei 8.078/1990 — Código de Defesa do Consumidor](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm)
- [Decreto 7.962/2013 — Comércio eletrônico](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/decreto/d7962.htm)
- [Lei 13.709/2018 — Lei Geral de Proteção de Dados](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm)
- [ANPD — Direitos dos titulares de dados](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares)
- [Fundação Procon-SP — Escola Paulista de Defesa do Consumidor](https://www.procon.sp.gov.br/epdc/)
- [Lei estadual paulista 17.832/2023](https://www.al.sp.gov.br/repositorio/legislacao/lei/2023/compilacao-lei-17832-01.11.2023.html)
- [Consumidor.gov.br — Como funciona](https://www.consumidor.gov.br/pages/principal/como-funciona)
- [iFood — Problemas com o pedido](https://institucional.ifood.com.br/ajuda/problemas-com-o-pedido-ifood/)

Fontes consultadas em 27 de agosto de 2026. As referências são utilizadas para contextualização analítica e não substituem validação jurídica.

