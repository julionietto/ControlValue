import pytest
import pandas as pd
from db.ativos_precos import (
    _normalize_col_name,
    _parse_price_value,
    import_ativos_precos_csv,
    get_all_ativos_precos,
    delete_all_ativos_precos
)
import db


def test_normalize_col_name():
    assert _normalize_col_name("Código") == "codigo"
    assert _normalize_col_name("Preço Teto") == "preco teto"
    assert _normalize_col_name("PREÇO_JUSTO") == "preco justo"
    assert _normalize_col_name(" Mercado ") == "mercado"
    assert _normalize_col_name("") == ""
    assert _normalize_col_name(None) == ""


def test_parse_price_value():
    assert _parse_price_value("35.50") == 35.50
    assert _parse_price_value("35,50") == 35.50
    assert _parse_price_value("R$ 1.234,56") == 1234.56
    assert _parse_price_value("$ 150.25") == 150.25
    assert _parse_price_value("0") == 0.0
    assert _parse_price_value("-") == 0.0
    assert _parse_price_value("N/A") == 0.0
    assert _parse_price_value(None) == 0.0
    assert _parse_price_value("invalid_text") == 0.0


def test_import_ativos_precos_csv_comma_and_semicolon(monkeypatch):
    # Test CSV with comma
    csv_comma = """Código,Preço Teto,Preço Justo,Mercado
BBAS3,35.00,42.50,Brasil
PETR4,38.20,44.00,Brasil
AAPL,180.00,210.00,EUA
"""
    # Test CSV with semicolon and Brazilian numbers
    csv_semicolon = """Codigo;Preco Teto;Preco Justo;Mercado
HGLG11;165,50;175,00;Brasil
MSFT;400,00;450,00;EUA
"""
    # Initialize db schema if needed
    db.init_db()

    # Import comma CSV
    success, msg, count = import_ativos_precos_csv(csv_comma, replace_existing=True)
    assert success is True
    assert count == 3
    assert "3 ativo(s)" in msg

    df = get_all_ativos_precos()
    assert len(df) == 3
    assert set(df['codigo'].tolist()) == {"BBAS3", "PETR4", "AAPL"}
    bbas3_row = df[df['codigo'] == 'BBAS3'].iloc[0]
    assert float(bbas3_row['preco_teto']) == 35.00
    assert float(bbas3_row['preco_justo']) == 42.50
    assert bbas3_row['mercado'] == 'Brasil'

    # Import semicolon CSV with replacement
    success_semi, msg_semi, count_semi = import_ativos_precos_csv(csv_semicolon, replace_existing=True)
    assert success_semi is True
    assert count_semi == 2

    df_semi = get_all_ativos_precos()
    assert len(df_semi) == 2
    assert set(df_semi['codigo'].tolist()) == {"HGLG11", "MSFT"}
    hglg_row = df_semi[df_semi['codigo'] == 'HGLG11'].iloc[0]
    assert float(hglg_row['preco_teto']) == 165.50
    assert float(hglg_row['preco_justo']) == 175.00

    # Import without replace (upsert / append)
    csv_add = "Código,Preço Teto,Preço Justo,Mercado\nVALE3,65.00,75.00,Brasil\n"
    success_add, _, count_add = import_ativos_precos_csv(csv_add, replace_existing=False)
    assert success_add is True
    assert count_add == 1

    df_merged = get_all_ativos_precos()
    assert len(df_merged) == 3
    assert "VALE3" in df_merged['codigo'].tolist()
    assert "HGLG11" in df_merged['codigo'].tolist()


def test_import_ativos_precos_csv_validations():
    # Empty CSV
    success_empty, msg_empty, _ = import_ativos_precos_csv("", replace_existing=False)
    assert success_empty is False
    assert "vazio" in msg_empty.lower()

    # Missing mandatory columns
    csv_invalid = "Ativo,Valor\nPETR4,30.00\n"
    success_inv, msg_inv, _ = import_ativos_precos_csv(csv_invalid, replace_existing=False)
    assert success_inv is False
    assert "colunas" in msg_inv.lower()
