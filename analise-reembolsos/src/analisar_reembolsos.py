from pathlib import Path
from collections import Counter
import json
import math
import re
import unicodedata

import numpy as np
import pandas as pd


SEED = 20250827
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
EVIDENCIAS = ROOT / "evidencias"


FEATURES = {
    "selecao_completa": "Pedido completo selecionado",
    "recorrencia_alta": "Recorrência >= 3 em 60 dias",
    "sem_resposta_loja": "Loja sem resposta",
    "evidencia_incompativel": "Evidência incompatível",
    "conta_relacionada": "Conta ligada a agrupamento",
    "foto_ausente": "Foto não anexada",
    "percentual_itens_contestados": "% de itens contestados",
    "valor_reembolso": "Valor solicitado",
    "idade_conta_dias": "Idade da conta",
    "contestacoes_60d": "Contestações em 60 dias",
}


def sigmoid(z):
    z = np.clip(z, -30, 30)
    return 1.0 / (1.0 + np.exp(-z))


def ajustar_logistica(x, y, iteracoes=2200, taxa=0.055, l2=0.018):
    x_bias = np.c_[np.ones(len(x)), x]
    pesos = np.zeros(x_bias.shape[1])
    for _ in range(iteracoes):
        prob = sigmoid(x_bias @ pesos)
        gradiente = (x_bias.T @ (prob - y)) / len(y)
        gradiente[1:] += l2 * pesos[1:]
        pesos -= taxa * gradiente
    return pesos


def prever_logistica(x, pesos):
    return sigmoid(np.c_[np.ones(len(x)), x] @ pesos)


def auc_rank(y, prob):
    y = np.asarray(y, dtype=int)
    prob = pd.Series(prob)
    ranks = prob.rank(method="average").to_numpy()
    positivos = y.sum()
    negativos = len(y) - positivos
    return (ranks[y == 1].sum() - positivos * (positivos + 1) / 2) / (positivos * negativos)


def metricas_classificacao(y, prob, limiar=0.5):
    previsto = (prob >= limiar).astype(int)
    tp = int(((previsto == 1) & (y == 1)).sum())
    fp = int(((previsto == 1) & (y == 0)).sum())
    tn = int(((previsto == 0) & (y == 0)).sum())
    fn = int(((previsto == 0) & (y == 1)).sum())
    precisao = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precisao * recall / (precisao + recall) if precisao + recall else 0
    return {"auc": auc_rank(y, prob), "precisao": precisao, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def dividir_estratificado(y, rng, proporcao_teste=0.25):
    teste = []
    for classe in [0, 1]:
        idx = np.where(y == classe)[0]
        rng.shuffle(idx)
        teste.extend(idx[: int(round(len(idx) * proporcao_teste))])
    teste = np.array(sorted(teste))
    treino = np.setdiff1d(np.arange(len(y)), teste)
    return treino, teste


def teste_2x2(base, sinal):
    tabela = pd.crosstab(base[sinal], base["exposicao_confirmada"]).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
    observado = tabela.to_numpy(dtype=float)
    esperado = observado.sum(axis=1, keepdims=True) @ observado.sum(axis=0, keepdims=True) / observado.sum()
    qui2 = (((observado - esperado) ** 2) / esperado).sum()
    p_valor = math.erfc(math.sqrt(qui2 / 2))
    taxa_sem = observado[0, 1] / observado[0].sum()
    taxa_com = observado[1, 1] / observado[1].sum()
    rr = taxa_com / taxa_sem if taxa_sem else np.nan
    return {
        "sinal": FEATURES.get(sinal, sinal),
        "volume_com_sinal": int(observado[1].sum()),
        "taxa_exposicao_com_sinal": taxa_com,
        "taxa_exposicao_sem_sinal": taxa_sem,
        "risco_relativo": rr,
        "qui_quadrado": qui2,
        "p_valor": p_valor,
    }


def tokens(textos):
    stop = {
        "para", "como", "mais", "pela", "pelo", "pedido", "produto", "estava", "foram",
        "isso", "recebi", "chegou", "quando", "dentro", "parte", "compra", "informado",
        "consta", "entrega", "entregue", "porém", "porem", "todos", "itens", "item",
    }
    contador = Counter()
    for texto in textos:
        limpo = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
        palavras = [p for p in re.findall(r"[a-z]+", limpo) if len(p) > 3 and p not in stop]
        contador.update(palavras)
        contador.update([f"{a} {b}" for a, b in zip(palavras, palavras[1:])])
    return contador


def main():
    rng = np.random.default_rng(SEED)
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(PROCESSED / "contestacoes_tratadas.csv", parse_dates=["data_pedido"], encoding="utf-8-sig")
    pedidos = pd.read_csv(PROCESSED / "pedidos_mensais.csv", encoding="utf-8-sig")

    print("ANÁLISE QUANTITATIVA")
    resumo = pd.DataFrame([
        ("Pedidos concluídos", int(pedidos["pedidos"].sum())),
        ("Contestações", len(base)),
        ("Taxa de contestação", len(base) / pedidos["pedidos"].sum()),
        ("Valor reembolsado", base["valor_reembolso"].sum()),
        ("Exposição sintética auditada", base["exposicao_potencial"].sum()),
        ("Participação da exposição", base["exposicao_potencial"].sum() / base["valor_reembolso"].sum()),
        ("Loja sem resposta", int(base["sem_resposta_loja"].sum())),
        ("Taxa sem resposta", base["sem_resposta_loja"].mean()),
    ], columns=["metrica", "valor"])
    print(resumo.to_string(index=False))

    mensal = base.groupby("mes", as_index=False).agg(
        contestacoes=("contestacao_id", "count"),
        sem_resposta=("sem_resposta_loja", "sum"),
        valor_reembolsado=("valor_reembolso", "sum"),
        exposicao=("exposicao_potencial", "sum"),
    ).merge(pedidos[["mes", "pedidos"]], on="mes", how="left")
    mensal["taxa_contestacao"] = mensal["contestacoes"] / mensal["pedidos"]
    mensal["taxa_sem_resposta"] = mensal["sem_resposta"] / mensal["contestacoes"]
    mensal["participacao_exposicao"] = mensal["exposicao"] / mensal["valor_reembolsado"]
    mensal = mensal[["mes", "pedidos", "contestacoes", "taxa_contestacao", "sem_resposta", "taxa_sem_resposta", "valor_reembolsado", "exposicao", "participacao_exposicao"]]
    print("\nEVOLUÇÃO MENSAL")
    print(mensal.round(4).to_string(index=False))

    sinais_binarios = ["selecao_completa", "recorrencia_alta", "sem_resposta_loja", "evidencia_incompativel", "conta_relacionada"]
    testes = pd.DataFrame([teste_2x2(base, sinal) for sinal in sinais_binarios]).sort_values("risco_relativo", ascending=False)
    print("\nTESTE DAS HIPÓTESES - ASSOCIAÇÃO 2x2")
    print(testes.round(4).to_string(index=False))

    segmentos = base.groupby("faixa_risco", as_index=False, observed=True).agg(
        contestacoes=("contestacao_id", "count"),
        valor_reembolsado=("valor_reembolso", "sum"),
        exposicao=("exposicao_potencial", "sum"),
        taxa_exposicao=("exposicao_confirmada", "mean"),
        taxa_sem_resposta=("sem_resposta_loja", "mean"),
    )
    ordem = pd.Categorical(segmentos["faixa_risco"], ["baixo", "intermediario", "alto"], ordered=True)
    segmentos = segmentos.assign(_ordem=ordem).sort_values("_ordem").drop(columns="_ordem")
    print("\nSEGMENTAÇÃO DE RISCO")
    print(segmentos.round(4).to_string(index=False))

    print("\nANÁLISE QUALITATIVA")
    temas = base.groupby("motivo", as_index=False).agg(
        mencoes=("contestacao_id", "count"),
        valor_reembolsado=("valor_reembolso", "sum"),
        exposicao=("exposicao_potencial", "sum"),
        taxa_exposicao=("exposicao_confirmada", "mean"),
        taxa_sem_resposta=("sem_resposta_loja", "mean"),
    ).sort_values("mencoes", ascending=False)
    temas["participacao_mencoes"] = temas["mencoes"] / len(base)
    print(temas.round(4).to_string(index=False))

    termos_expostos = tokens(base.loc[base["exposicao_confirmada"].eq(1), "relato_cliente"])
    termos_legitimos = tokens(base.loc[base["exposicao_confirmada"].eq(0), "relato_cliente"])
    top_termos = pd.DataFrame([
        {"grupo": "exposição", "termo": termo, "frequencia": freq}
        for termo, freq in termos_expostos.most_common(12)
    ] + [
        {"grupo": "legítimo", "termo": termo, "frequencia": freq}
        for termo, freq in termos_legitimos.most_common(12)
    ])
    print("\nTERMOS MAIS FREQUENTES NOS RELATOS")
    print(top_termos.to_string(index=False))

    amostras = pd.concat([
        base.sort_values("score_regra", ascending=False).head(1),
        base.loc[base["faixa_risco"].eq("intermediario")].sort_values("score_regra", ascending=False).head(1),
        base.sort_values("score_regra").head(1),
    ])[ ["contestacao_id", "motivo", "relato_cliente", "faixa_risco", "score_regra", "exposicao_confirmada"] ]
    print("\nAMOSTRA QUALITATIVA PRIORIZADA")
    print(amostras.to_string(index=False))

    print("\nMODELO DE PRIORIZAÇÃO - REGRESSÃO LOGÍSTICA COM NUMPY")
    modelo = base.copy()
    modelo["foto_ausente"] = modelo["foto_anexada"].eq(0).astype(int)
    feature_names = list(FEATURES)
    x_raw = modelo[feature_names].astype(float).to_numpy()
    y = modelo["exposicao_confirmada"].astype(int).to_numpy()
    treino, teste = dividir_estratificado(y, rng)
    media = x_raw[treino].mean(axis=0)
    desvio = x_raw[treino].std(axis=0)
    desvio[desvio == 0] = 1
    x = (x_raw - media) / desvio
    pesos = ajustar_logistica(x[treino], y[treino])
    prob_treino = prever_logistica(x[treino], pesos)
    candidatos = np.linspace(0.12, 0.55, 44)
    limiar = max(candidatos, key=lambda t: metricas_classificacao(y[treino], prob_treino, t)["f1"])
    prob_teste = prever_logistica(x[teste], pesos)
    metricas = metricas_classificacao(y[teste], prob_teste, limiar=limiar)
    metricas["limiar_definido_no_treino"] = float(limiar)

    auc_boot = []
    for _ in range(200):
        amostra = rng.integers(0, len(teste), len(teste))
        if len(np.unique(y[teste][amostra])) == 2:
            auc_boot.append(auc_rank(y[teste][amostra], prob_teste[amostra]))
    metricas["auc_ic95_inferior"] = float(np.quantile(auc_boot, 0.025))
    metricas["auc_ic95_superior"] = float(np.quantile(auc_boot, 0.975))
    coeficientes = pd.DataFrame({
        "variavel": [FEATURES[x] for x in feature_names],
        "coeficiente_padronizado": pesos[1:],
        "odds_ratio_aproximado": np.exp(pesos[1:]),
    }).sort_values("coeficiente_padronizado", ascending=False)
    print(pd.DataFrame([metricas]).round(4).to_string(index=False))
    print("\nCOEFICIENTES")
    print(coeficientes.round(4).to_string(index=False))

    pesos_full = ajustar_logistica(x, y)
    base["probabilidade_modelo"] = prever_logistica(x, pesos_full)
    cenarios = []
    for nome, proporcao in [("conservador", 0.15), ("equilibrado", 0.32), ("restritivo", 0.56)]:
        limiar = base["probabilidade_modelo"].quantile(1 - proporcao)
        revisar = base["probabilidade_modelo"].ge(limiar)
        legitimos = base["exposicao_confirmada"].eq(0)
        perda_evitada = base.loc[revisar, "exposicao_potencial"].sum()
        custo_revisao = max(0, int(revisar.sum()) - 826) * 7.50
        casos_legitimos_revisados = int((revisar & legitimos).sum())
        custo_atrito = casos_legitimos_revisados * 2.50
        cenarios.append({
            "cenario": nome,
            "proporcao_revisao": revisar.mean(),
            "casos_revisados": int(revisar.sum()),
            "captura_exposicao": perda_evitada / base["exposicao_potencial"].sum(),
            "perda_evitada": perda_evitada,
            "legitimos_revisados": casos_legitimos_revisados,
            "taxa_atrito_legitimos": casos_legitimos_revisados / legitimos.sum(),
            "custo_revisao_incremental": custo_revisao,
            "custo_atrito_estimado": custo_atrito,
            "beneficio_liquido": perda_evitada - custo_revisao - custo_atrito,
        })
    cenarios = pd.DataFrame(cenarios)
    print("\nSIMULAÇÃO DE POLÍTICAS")
    print(cenarios.round(4).to_string(index=False))

    resumo.to_csv(EVIDENCIAS / "resumo_kpis.csv", index=False, encoding="utf-8-sig")
    mensal.to_csv(EVIDENCIAS / "analise_mensal.csv", index=False, encoding="utf-8-sig")
    testes.to_csv(EVIDENCIAS / "testes_hipoteses.csv", index=False, encoding="utf-8-sig")
    segmentos.to_csv(EVIDENCIAS / "segmentacao_risco.csv", index=False, encoding="utf-8-sig")
    temas.to_csv(EVIDENCIAS / "analise_qualitativa_temas.csv", index=False, encoding="utf-8-sig")
    top_termos.to_csv(EVIDENCIAS / "termos_relato.csv", index=False, encoding="utf-8-sig")
    amostras.to_csv(EVIDENCIAS / "amostras_qualitativas.csv", index=False, encoding="utf-8-sig")
    coeficientes.to_csv(EVIDENCIAS / "coeficientes_modelo.csv", index=False, encoding="utf-8-sig")
    cenarios.to_csv(EVIDENCIAS / "cenarios_politica.csv", index=False, encoding="utf-8-sig")
    base[["contestacao_id", "probabilidade_modelo"]].to_csv(EVIDENCIAS / "scores_modelo.csv", index=False, encoding="utf-8-sig")
    (EVIDENCIAS / "metricas_modelo.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    for nome, tabela in {
        "analise_mensal": mensal,
        "testes_hipoteses": testes,
        "analise_qualitativa_temas": temas,
        "segmentacao_risco": segmentos,
        "cenarios_politica": cenarios,
        "coeficientes_modelo": coeficientes,
    }.items():
        tabela.to_json(EVIDENCIAS / f"{nome}.json", orient="records", force_ascii=False)


if __name__ == "__main__":
    main()
