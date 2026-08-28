from pathlib import Path
import json

import numpy as np
import pandas as pd


SEED = 20250827
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
EVIDENCIAS = ROOT / "evidencias"

MESES = [
    ("2025-01", 9200, 690, 250, 38400.0, 8100.0),
    ("2025-02", 9800, 750, 275, 44800.0, 9500.0),
    ("2025-03", 10100, 780, 300, 51200.0, 10800.0),
    ("2025-04", 10400, 860, 365, 57900.0, 13200.0),
    ("2025-05", 10300, 835, 350, 64300.0, 14900.0),
    ("2025-06", 10200, 885, 410, 72000.0, 18100.0),
]

TEMAS = {
    "item_faltante": [
        "Faltou um item do pedido e a loja não respondeu.",
        "O pedido chegou incompleto, faltou parte da compra.",
        "Não recebi todos os itens que estavam na nota.",
    ],
    "pedido_incorreto": [
        "Recebi produtos diferentes do que selecionei.",
        "O pedido veio errado e preciso corrigir a cobrança.",
        "Entregaram outro item no lugar do que comprei.",
    ],
    "produto_avariado": [
        "A embalagem chegou aberta e o produto estava avariado.",
        "O item vazou durante a entrega e não dava para consumir.",
        "O produto chegou danificado dentro da sacola.",
    ],
    "qualidade": [
        "A comida chegou fria e com qualidade abaixo do esperado.",
        "O produto estava com aparência ruim quando chegou.",
        "A qualidade não correspondeu ao que foi anunciado.",
    ],
    "nao_entregue": [
        "O aplicativo marcou como entregue, mas não recebi o pedido.",
        "O pedido não chegou no endereço informado.",
        "Consta entrega concluída, porém nada foi recebido.",
    ],
}


def ratear(indices, total, rng, peso=None):
    indices = np.asarray(indices)
    if not len(indices):
        raise ValueError("Não há registros para ratear o valor.")
    if peso is None:
        peso = rng.lognormal(mean=3.6, sigma=0.45, size=len(indices))
    peso = np.asarray(peso, dtype=float)
    valores = np.round(total * peso / peso.sum(), 2)
    valores[-1] = np.round(valores[-1] + total - valores.sum(), 2)
    return pd.Series(valores, index=indices)


def moeda_suja(valor, posicao):
    if posicao % 11 == 0:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if posicao % 7 == 0:
        return f"{valor:.2f}".replace(".", ",")
    return f"{valor:.2f}"


def data_suja(data, posicao):
    return data.strftime("%d/%m/%Y") if posicao % 6 == 0 else data.strftime("%Y-%m-%d")


def main():
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)

    pedidos = []
    claim_positions = []
    contador = 1
    for mes, qtd_pedidos, qtd_claims, *_ in MESES:
        ano, numero_mes = map(int, mes.split("-"))
        dias_mes = pd.Period(mes).days_in_month
        datas = pd.to_datetime(
            [f"{ano}-{numero_mes:02d}-{dia:02d}" for dia in rng.integers(1, dias_mes + 1, qtd_pedidos)]
        )
        inicio = len(pedidos)
        locais_claim = rng.choice(qtd_pedidos, size=qtd_claims, replace=False)
        claim_positions.extend((inicio + locais_claim).tolist())
        for data in datas:
            pedidos.append(
                {
                    "pedido_id": f"PED{contador:06d}",
                    "data_pedido": data,
                    "cliente_id": f"CLI{rng.integers(1, 18001):05d}",
                    "loja_id": f"LOJ{rng.integers(1, 451):04d}",
                    "cidade": rng.choice(["Campinas", "São Paulo", "Santos", "Sorocaba"], p=[0.34, 0.36, 0.15, 0.15]),
                    "categoria_loja": rng.choice(["Restaurante", "Mercado", "Farmácia", "Pet shop"], p=[0.68, 0.20, 0.08, 0.04]),
                    "itens_pedido": int(rng.integers(1, 8)),
                    "valor_pedido": float(np.round(rng.lognormal(4.25, 0.42), 2)),
                    "status_pedido": "concluido",
                }
            )
            contador += 1

    pedidos = pd.DataFrame(pedidos)
    claim_positions = np.array(claim_positions)
    pedidos.loc[claim_positions, "itens_pedido"] = np.maximum(pedidos.loc[claim_positions, "itens_pedido"], 2)

    claims = pedidos.loc[claim_positions, [
        "pedido_id", "data_pedido", "cliente_id", "loja_id", "itens_pedido", "valor_pedido"
    ]].copy().reset_index(drop=True)
    claims.insert(0, "contestacao_id", [f"CON{i:05d}" for i in range(1, len(claims) + 1)])
    claims["mes"] = claims["data_pedido"].dt.strftime("%Y-%m")

    n = len(claims)
    claims["motivo"] = rng.choice(list(TEMAS), size=n, p=[0.34, 0.24, 0.14, 0.16, 0.12])
    claims["relato_cliente"] = [rng.choice(TEMAS[tema]) for tema in claims["motivo"]]
    claims["foto_anexada"] = rng.choice([1, 0], size=n, p=[0.71, 0.29])
    claims["idade_conta_dias"] = rng.integers(12, 2400, size=n)
    claims["contestacoes_60d"] = rng.choice([0, 1, 2], size=n, p=[0.49, 0.35, 0.16])

    recorrentes = rng.choice(n, size=310, replace=False)
    claims.loc[recorrentes, "contestacoes_60d"] = rng.integers(3, 7, size=len(recorrentes))

    full = rng.choice(n, size=855, replace=False)
    claims["itens_contestados"] = [int(rng.integers(1, itens)) for itens in claims["itens_pedido"]]
    claims.loc[full, "itens_contestados"] = claims.loc[full, "itens_pedido"]

    mismatch = rng.choice(n, size=442, replace=False)
    claims["evidencia_incompativel"] = 0
    claims.loc[mismatch, "evidencia_incompativel"] = 1

    claims["cluster_conta"] = ""
    ligados = rng.choice(n, size=384, replace=False)
    clusters = np.repeat([f"GRP{i:03d}" for i in range(1, 129)], 3)
    rng.shuffle(clusters)
    claims.loc[ligados, "cluster_conta"] = clusters

    claims["status_resposta_loja"] = "respondida"
    for mes, _, _, sem_resposta, *_ in MESES:
        idx_mes = claims.index[claims["mes"].eq(mes)]
        idx_sem = rng.choice(idx_mes, size=sem_resposta, replace=False)
        claims.loc[idx_sem, "status_resposta_loja"] = "sem_resposta"

    rotas = np.array(["autoaprovada"] * 3300 + ["revisao_manual"] * 826 + ["negada_ou_retirada"] * 674)
    rng.shuffle(rotas)
    claims["rota_decisao"] = rotas
    claims["decisao_final"] = np.where(claims["rota_decisao"].eq("autoaprovada"), "aprovada", "negada")
    manuais = claims.index[claims["rota_decisao"].eq("revisao_manual")]
    manuais_aprovadas = rng.choice(manuais, size=510, replace=False)
    claims.loc[manuais_aprovadas, "decisao_final"] = "aprovada"
    retiradas = claims.index[claims["rota_decisao"].eq("negada_ou_retirada")]
    claims.loc[rng.choice(retiradas, size=230, replace=False), "decisao_final"] = "retirada"

    claims["selecao_completa"] = claims["itens_contestados"].eq(claims["itens_pedido"]).astype(int)
    claims["recorrencia_alta"] = claims["contestacoes_60d"].ge(3).astype(int)
    claims["sem_resposta_loja"] = claims["status_resposta_loja"].eq("sem_resposta").astype(int)
    claims["conta_relacionada"] = claims["cluster_conta"].ne("").astype(int)
    claims["valor_reembolso"] = 0.0
    claims["exposicao_confirmada"] = 0

    sinal_latente = (
        1.5 * claims["selecao_completa"]
        + 1.25 * claims["recorrencia_alta"]
        + 1.75 * claims["evidencia_incompativel"]
        + 1.1 * claims["conta_relacionada"]
        + 0.55 * claims["sem_resposta_loja"]
        + 0.35 * claims["foto_anexada"].eq(0)
        + rng.normal(0, 1.70, size=n)
    )

    for mes, _, _, _, total_reembolso, total_exposicao in MESES:
        idx_mes = claims.index[claims["mes"].eq(mes)]
        aprovadas = idx_mes[claims.loc[idx_mes, "decisao_final"].eq("aprovada")]
        qtd_expostas = max(1, int(round(len(aprovadas) * (0.17 + 0.015 * (int(mes[-2:]) - 1)))))
        expostas = sinal_latente.loc[aprovadas].nlargest(qtd_expostas).index
        legitimas = aprovadas.difference(expostas)
        claims.loc[expostas, "exposicao_confirmada"] = 1
        claims.loc[ratear(expostas, total_exposicao, rng).index, "valor_reembolso"] = ratear(expostas, total_exposicao, rng).values
        claims.loc[ratear(legitimas, total_reembolso - total_exposicao, rng).index, "valor_reembolso"] = ratear(legitimas, total_reembolso - total_exposicao, rng).values

    # Garante que o valor do pedido comporte o reembolso calculado.
    valor_minimo = claims["valor_reembolso"] + rng.uniform(4.0, 38.0, size=n)
    claims["valor_pedido"] = np.maximum(claims["valor_pedido"], valor_minimo).round(2)
    pedidos_valor = claims.set_index("pedido_id")["valor_pedido"]
    pedidos.loc[pedidos["pedido_id"].isin(pedidos_valor.index), "valor_pedido"] = pedidos.loc[
        pedidos["pedido_id"].isin(pedidos_valor.index), "pedido_id"
    ].map(pedidos_valor)

    pedidos_raw = pedidos.copy()
    pedidos_raw["data_pedido"] = [data_suja(x, i) for i, x in enumerate(pedidos_raw["data_pedido"])]
    pedidos_raw["valor_pedido"] = [moeda_suja(x, i) for i, x in enumerate(pedidos_raw["valor_pedido"])]
    pedidos_raw.loc[pedidos_raw.index[::19], "cidade"] = pedidos_raw.loc[pedidos_raw.index[::19], "cidade"].str.upper()
    pedidos_raw = pd.concat([pedidos_raw, pedidos_raw.sample(120, random_state=SEED)], ignore_index=True)

    claims_raw = claims.drop(columns=["mes", "selecao_completa", "recorrencia_alta", "sem_resposta_loja", "conta_relacionada"]).copy()
    claims_raw["data_pedido"] = [data_suja(x, i) for i, x in enumerate(claims_raw["data_pedido"])]
    claims_raw["valor_pedido"] = [moeda_suja(x, i) for i, x in enumerate(claims_raw["valor_pedido"])]
    claims_raw["valor_reembolso"] = [moeda_suja(x, i + 3) for i, x in enumerate(claims_raw["valor_reembolso"])]
    idx_sem_resposta = claims_raw.index[claims_raw["status_resposta_loja"].eq("sem_resposta")]
    claims_raw.loc[idx_sem_resposta[::2], "status_resposta_loja"] = "SEM RESPOSTA"
    claims_raw.loc[idx_sem_resposta[1::3], "status_resposta_loja"] = "sem resposta"
    claims_raw.loc[claims_raw.index[::23], "motivo"] = claims_raw.loc[claims_raw.index[::23], "motivo"].str.upper().str.replace("_", " ")
    claims_raw.loc[claims_raw.index[::401], "relato_cliente"] = ""
    claims_raw = pd.concat([claims_raw, claims_raw.sample(20, random_state=SEED + 1)], ignore_index=True)

    pedidos_raw.to_csv(RAW / "pedidos_raw.csv", index=False, encoding="utf-8-sig")
    claims_raw.to_csv(RAW / "contestacoes_raw.csv", index=False, encoding="utf-8-sig")

    metadados = {
        "semente": SEED,
        "periodo": "2025-01 a 2025-06",
        "pedidos_limpos_esperados": 60000,
        "contestacoes_limpas_esperadas": 4800,
        "dados": "100% sintéticos",
    }
    (RAW / "metadados_geracao.json").write_text(json.dumps(metadados, indent=2, ensure_ascii=False), encoding="utf-8")

    print("GERAÇÃO DA BASE SINTÉTICA")
    print(f"semente: {SEED}")
    print(f"pedidos gerados: {len(pedidos):,}")
    print(f"pedidos no arquivo raw: {len(pedidos_raw):,} (inclui 120 duplicados intencionais)")
    print(f"contestações geradas: {len(claims):,}")
    print(f"contestações no arquivo raw: {len(claims_raw):,} (inclui 20 duplicados intencionais)")
    print("\nAMOSTRA DE CONTESTAÇÕES RAW")
    print(claims_raw.head(5).to_string(index=False))
    print("\nCONTROLES DE GERAÇÃO")
    print(claims.groupby("mes").agg(contestacoes=("contestacao_id", "count"), sem_resposta=("sem_resposta_loja", "sum"), reembolso=("valor_reembolso", "sum"), exposicao=("valor_reembolso", lambda s: s[claims.loc[s.index, "exposicao_confirmada"].eq(1)].sum())).round(2).to_string())


if __name__ == "__main__":
    main()
