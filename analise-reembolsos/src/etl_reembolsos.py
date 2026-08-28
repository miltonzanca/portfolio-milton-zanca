from pathlib import Path
import hashlib
import re
import unicodedata

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
EVIDENCIAS = ROOT / "evidencias"


def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower())
    return texto.strip("_")


def ler_moeda(valor):
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto or texto.lower() == "nan":
        return np.nan
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


def ler_data(valor):
    texto = str(valor).strip()
    formato = "%d/%m/%Y" if "/" in texto else "%Y-%m-%d"
    return pd.to_datetime(texto, format=formato, errors="coerce")


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)

    pedidos_raw = pd.read_csv(RAW / "pedidos_raw.csv", dtype=str, encoding="utf-8-sig")
    claims_raw = pd.read_csv(RAW / "contestacoes_raw.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)

    print("ETL - REEMBOLSOS SOB RISCO")
    print(f"entrada pedidos: {len(pedidos_raw):,} linhas")
    print(f"entrada contestações: {len(claims_raw):,} linhas")
    print("\nAMOSTRA ANTES DO TRATAMENTO")
    print(claims_raw[["contestacao_id", "data_pedido", "motivo", "status_resposta_loja", "valor_reembolso"]].head(6).to_string(index=False))

    qualidade = []
    duplicados_pedidos = int(pedidos_raw.duplicated("pedido_id").sum())
    duplicados_claims = int(claims_raw.duplicated("contestacao_id").sum())
    qualidade.extend([
        {"regra": "pedido_id duplicado", "antes": duplicados_pedidos, "depois": 0, "tratamento": "manter primeiro registro"},
        {"regra": "contestacao_id duplicada", "antes": duplicados_claims, "depois": 0, "tratamento": "manter primeiro registro"},
        {"regra": "datas em formato DD/MM/AAAA", "antes": int(claims_raw["data_pedido"].str.contains("/", regex=False).sum()), "depois": 0, "tratamento": "padronizar para ISO"},
        {"regra": "valores monetários com vírgula ou R$", "antes": int(claims_raw["valor_reembolso"].str.contains(r"R\$|,", regex=True).sum()), "depois": 0, "tratamento": "converter para número decimal"},
        {"regra": "relato vazio", "antes": int(claims_raw["relato_cliente"].eq("").sum()), "depois": 0, "tratamento": "marcar ausência sem inventar conteúdo"},
    ])

    pedidos = pedidos_raw.drop_duplicates("pedido_id", keep="first").copy()
    pedidos["data_pedido"] = pedidos["data_pedido"].map(ler_data)
    pedidos["valor_pedido"] = pedidos["valor_pedido"].map(ler_moeda)
    pedidos["itens_pedido"] = pd.to_numeric(pedidos["itens_pedido"], errors="coerce").astype("Int64")
    pedidos["cidade"] = pedidos["cidade"].str.title().str.strip()
    pedidos["categoria_loja"] = pedidos["categoria_loja"].str.strip().str.title()

    claims = claims_raw.drop_duplicates("contestacao_id", keep="first").copy()
    claims["data_claim_raw"] = claims["data_pedido"].map(ler_data)
    claims["valor_claim_raw"] = claims["valor_pedido"].map(ler_moeda)
    claims["valor_reembolso"] = claims["valor_reembolso"].map(ler_moeda).fillna(0.0)
    claims["itens_contestados"] = pd.to_numeric(claims["itens_contestados"], errors="coerce").astype("Int64")
    claims["foto_anexada"] = pd.to_numeric(claims["foto_anexada"], errors="coerce").fillna(0).astype(int)
    claims["idade_conta_dias"] = pd.to_numeric(claims["idade_conta_dias"], errors="coerce").astype("Int64")
    claims["contestacoes_60d"] = pd.to_numeric(claims["contestacoes_60d"], errors="coerce").astype("Int64")
    claims["evidencia_incompativel"] = pd.to_numeric(claims["evidencia_incompativel"], errors="coerce").fillna(0).astype(int)
    claims["exposicao_confirmada"] = pd.to_numeric(claims["exposicao_confirmada"], errors="coerce").fillna(0).astype(int)
    claims["motivo"] = claims["motivo"].map(normalizar_texto)
    claims["status_resposta_loja"] = claims["status_resposta_loja"].map(normalizar_texto).map(
        lambda x: "sem_resposta" if "sem_resposta" in x else "respondida"
    )
    claims["relato_ausente"] = claims["relato_cliente"].eq("").astype(int)
    claims.loc[claims["relato_ausente"].eq(1), "relato_cliente"] = "sem relato informado"
    claims["cluster_conta"] = claims["cluster_conta"].fillna("").str.strip()

    colunas_pedido = [
        "pedido_id", "data_pedido", "cliente_id", "loja_id", "cidade", "categoria_loja",
        "itens_pedido", "valor_pedido", "status_pedido"
    ]
    colunas_claim = [
        "contestacao_id", "pedido_id", "motivo", "relato_cliente", "relato_ausente",
        "itens_contestados", "foto_anexada", "idade_conta_dias", "contestacoes_60d",
        "evidencia_incompativel", "cluster_conta", "status_resposta_loja", "rota_decisao",
        "decisao_final", "valor_reembolso", "exposicao_confirmada"
    ]
    base = claims[colunas_claim].merge(pedidos[colunas_pedido], on="pedido_id", how="left", validate="one_to_one", indicator=True)
    sem_correspondencia = int(base["_merge"].ne("both").sum())
    qualidade.append({"regra": "contestação sem pedido correspondente", "antes": sem_correspondencia, "depois": sem_correspondencia, "tratamento": "bloquear carga se maior que zero"})
    if sem_correspondencia:
        raise ValueError("Existem contestações sem pedido correspondente.")
    base = base.drop(columns="_merge")

    base["mes"] = base["data_pedido"].dt.strftime("%Y-%m")
    base["percentual_itens_contestados"] = (base["itens_contestados"] / base["itens_pedido"]).astype(float)
    base["selecao_completa"] = base["itens_contestados"].eq(base["itens_pedido"]).astype(int)
    base["recorrencia_alta"] = base["contestacoes_60d"].ge(3).astype(int)
    base["sem_resposta_loja"] = base["status_resposta_loja"].eq("sem_resposta").astype(int)
    base["conta_relacionada"] = base["cluster_conta"].ne("").astype(int)
    base["valor_alto"] = base["valor_reembolso"].gt(base["valor_reembolso"].quantile(0.75)).astype(int)
    base["score_regra"] = (
        25 * base["selecao_completa"]
        + 20 * base["recorrencia_alta"]
        + 16 * base["sem_resposta_loja"]
        + 22 * base["evidencia_incompativel"]
        + 14 * base["conta_relacionada"]
        + 8 * base["valor_alto"]
        - 8 * base["foto_anexada"]
    )
    ranking = base["score_regra"].rank(method="first")
    base["faixa_risco"] = pd.qcut(
        ranking,
        q=[0, 0.55, 0.84375, 1],
        labels=["baixo", "intermediario", "alto"],
    ).astype(str)
    base["exposicao_potencial"] = np.where(base["exposicao_confirmada"].eq(1), base["valor_reembolso"], 0.0)
    base["cliente_hash"] = base["cliente_id"].map(
        lambda x: "anon_" + hashlib.sha256(str(x).encode("utf-8")).hexdigest()[:10]
    )
    base = base.drop(columns="cliente_id")

    colunas_finais = [
        "contestacao_id", "pedido_id", "data_pedido", "mes", "cliente_hash", "loja_id", "cidade",
        "categoria_loja", "motivo", "relato_cliente", "relato_ausente", "itens_pedido",
        "itens_contestados", "percentual_itens_contestados", "selecao_completa", "foto_anexada",
        "idade_conta_dias", "contestacoes_60d", "recorrencia_alta", "evidencia_incompativel",
        "cluster_conta", "conta_relacionada", "status_resposta_loja", "sem_resposta_loja",
        "rota_decisao", "decisao_final", "valor_pedido", "valor_reembolso", "valor_alto",
        "score_regra", "faixa_risco", "exposicao_confirmada", "exposicao_potencial"
    ]
    base = base[colunas_finais].sort_values(["data_pedido", "contestacao_id"]).reset_index(drop=True)

    mensal_pedidos = pedidos.assign(mes=pedidos["data_pedido"].dt.strftime("%Y-%m")).groupby("mes", as_index=False).agg(
        pedidos=("pedido_id", "nunique"), valor_pedidos=("valor_pedido", "sum")
    )
    qualidade_df = pd.DataFrame(qualidade)

    base.to_csv(PROCESSED / "contestacoes_tratadas.csv", index=False, encoding="utf-8-sig")
    mensal_pedidos.to_csv(PROCESSED / "pedidos_mensais.csv", index=False, encoding="utf-8-sig")
    base.to_json(PROCESSED / "contestacoes_tratadas.json", orient="records", date_format="iso", force_ascii=False)
    mensal_pedidos.to_json(PROCESSED / "pedidos_mensais.json", orient="records", force_ascii=False)
    qualidade_df.to_csv(EVIDENCIAS / "qualidade_etl.csv", index=False, encoding="utf-8-sig")
    qualidade_df.to_json(EVIDENCIAS / "qualidade_etl.json", orient="records", force_ascii=False)
    base.head(20).to_csv(EVIDENCIAS / "amostra_tratada.csv", index=False, encoding="utf-8-sig")

    dicionario = pd.DataFrame([
        ("contestacao_id", "Identificador sintético da contestação"),
        ("pedido_id", "Identificador sintético do pedido"),
        ("cliente_hash", "Identificador anonimizado do cliente"),
        ("motivo", "Tema padronizado da reclamação"),
        ("percentual_itens_contestados", "Itens contestados dividido pelos itens do pedido"),
        ("contestacoes_60d", "Quantidade de contestações do cliente na janela de 60 dias"),
        ("sem_resposta_loja", "Indicador de ausência de resposta da loja no prazo"),
        ("score_regra", "Pontuação de triagem baseada em sinais observáveis"),
        ("faixa_risco", "Faixa relativa de priorização: baixo, intermediário ou alto"),
        ("exposicao_confirmada", "Rótulo sintético de auditoria usado apenas para validar o método"),
        ("exposicao_potencial", "Valor reembolsado quando o rótulo sintético de auditoria é positivo"),
    ], columns=["campo", "definicao"])
    dicionario.to_csv(EVIDENCIAS / "dicionario_dados.csv", index=False, encoding="utf-8-sig")

    assert len(pedidos) == 60000
    assert len(base) == 4800
    assert round(base["valor_reembolso"].sum(), 2) == 328600.00
    assert round(base["exposicao_potencial"].sum(), 2) == 74600.00
    assert int(base["sem_resposta_loja"].sum()) == 1950
    assert base["faixa_risco"].value_counts().to_dict() == {"baixo": 2640, "intermediario": 1410, "alto": 750}

    print("\nCONTROLES DO ETL")
    print(qualidade_df.to_string(index=False))
    print("\nAMOSTRA DEPOIS DO TRATAMENTO")
    print(base[["contestacao_id", "mes", "motivo", "percentual_itens_contestados", "sem_resposta_loja", "score_regra", "faixa_risco", "valor_reembolso"]].head(8).to_string(index=False))
    print("\nRECONCILIAÇÃO")
    print(f"pedidos únicos: {len(pedidos):,}")
    print(f"contestações únicas: {len(base):,}")
    print(f"valor reembolsado: R$ {base['valor_reembolso'].sum():,.2f}")
    print(f"exposição sintética auditada: R$ {base['exposicao_potencial'].sum():,.2f}")
    print(f"lojas sem resposta: {base['sem_resposta_loja'].sum():,}")
    print("faixas de risco:")
    print(base["faixa_risco"].value_counts().to_string())


if __name__ == "__main__":
    main()
