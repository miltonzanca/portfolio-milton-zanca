# Análise de reembolsos sob risco

Pipeline reproduzível que sustenta o case apresentado no portfólio. A base, os rótulos de auditoria e os resultados são integralmente sintéticos.

## Pergunta de negócio

Como reduzir perdas com reembolsos potencialmente indevidos sem aumentar o atrito de clientes legítimos?

## Estrutura

```text
analise-reembolsos/
├── data/
│   ├── raw/                 # arquivos recebidos pelo ETL
│   └── processed/           # base reconciliada e anonimizada
├── evidencias/              # saídas, amostras, testes e logs
└── src/
    ├── gerar_base_sintetica.py
    ├── etl_reembolsos.py
    └── analisar_reembolsos.py
```

## Execução

```powershell
python analise-reembolsos/src/gerar_base_sintetica.py
python analise-reembolsos/src/etl_reembolsos.py
python analise-reembolsos/src/analisar_reembolsos.py
```

A geração usa a semente `20250827`. A mesma execução deve produzir:

- 60.000 pedidos únicos;
- 4.800 contestações únicas;
- R$ 328.600,00 reembolsados;
- R$ 74.600,00 de exposição sintética auditada;
- 1.950 solicitações sem resposta da loja.

## Etapas

1. **Geração:** cria pedidos, contestações, relatos e rótulo sintético de auditoria. Também introduz duplicidades e inconsistências de formato para testar o ETL.
2. **ETL:** remove duplicidades, padroniza datas, moedas e categorias, valida a relação pedido-contestação, anonimiza o cliente e cria variáveis analíticas.
3. **Diagnóstico:** reconcilia KPIs, testa associações 2x2, segmenta o risco e analisa temas dos relatos.
4. **Modelo:** ajusta regressão logística com NumPy, escolhe o limiar apenas no treino e avalia AUC, precisão, recall, F1 e matriz de confusão no teste.
5. **Política:** compara cenários de revisão considerando exposição capturada, custo operacional e clientes legítimos direcionados à revisão.

## Principais resultados

- AUC de teste: **0,785**; IC bootstrap de 95%: **0,754 a 0,817**.
- Limiar selecionado no treino: **0,20**.
- Recall: **62,5%**; precisão: **36,0%**.
- Cenário equilibrado: **32%** de revisão, **73,5%** da exposição capturada e **R$ 47,0 mil** de benefício líquido estimado.

O cenário restritivo apresenta captura maior, mas direciona aproximadamente metade dos casos legítimos para revisão. Por esse motivo ele não é recomendado sem piloto e guardrails de experiência.

## Limites

- O desempenho é uma demonstração metodológica sobre dados sintéticos, não uma validação de produção.
- Associação não comprova causalidade.
- Score de risco prioriza análise; não comprova fraude.
- Uma implantação real exigiria revisão jurídica, avaliação de vieses, monitoramento de drift e experimento controlado.

## Ferramentas demonstradas

- Python, pandas e NumPy
- tratamento e reconciliação de dados
- análise qualitativa e quantitativa
- teste de hipóteses
- regressão logística e avaliação de modelo
- simulação de políticas
- Excel auditável
