# Fraude & Desperdício

## Objetivo

Organizar eventos de utilização de saúde para triagem de auditoria e priorização de análise. O painel não classifica nenhum evento como fraude confirmada.

## Escopo sintético

- Período: janeiro a junho de 2024.
- Granularidade: um evento de utilização por registro.
- Volume: 300 eventos, com 50 registros por mês.
- Entidades: beneficiário, prestador, procedimento, data, valor, regra de alerta, risco e status.

## Regras do cenário

| Regra | Sinal identificado | Uso no painel |
|---|---|---|
| Uso por terceiro | Possível divergência entre utilizador e titular do benefício | Prioridade de auditoria e valor sob revisão |
| Incompatibilidade de perfil | Procedimento incompatível com o perfil cadastral do beneficiário | Verificação cadastral e assistencial |
| Possível desperdício | Repetição de exame em intervalo inferior ao parâmetro do cenário | Revisão de pertinência e histórico de utilização |

## Métricas

- **Eventos analisados:** quantidade de registros depois dos filtros.
- **Alertas para auditoria:** eventos com uma regra de alerta associada.
- **Valor sob revisão:** soma do valor dos alertas; não representa perda confirmada.
- **Alto risco:** quantidade de alertas classificados como prioritários no cenário.

## Visuais e decisões

| Visual | Pergunta respondida |
|---|---|
| KPIs | Qual é o tamanho do recorte e da fila de auditoria? |
| Volume mensal | Em qual mês os alertas se concentraram? |
| Valor por tipo de alerta | Qual regra concentra maior valor sob revisão? |
| Ranking de prestadores | Onde há maior concentração de eventos sinalizados? |
| Fila de eventos | Quais casos devem ser avaliados primeiro? |

## Limitações e validação

Em ambiente real, as regras exigem conferência com cadastro, guias, prontuário, autorização, histórico de utilização e política assistencial. A classificação de risco deve ser revisada por auditoria especializada.

