import html
import pandas as pd

def format_ticker_for_display(ticker_str):
    if isinstance(ticker_str, str) and ticker_str.endswith(".SA"):
        return ticker_str[:-3]
    return ticker_str

def escape_html(text):
    """Sanitiza strings de entrada convertendo caracteres perigosos (XSS) em HTML entities."""
    if text is None: return ""
    return html.escape(str(text))

def format_brl(value):
    """Formata um float para o padrão de moeda brasileiro (R$ X.XXX,XX)"""
    try:
        # Formata com 2 casas decimais, usando vírgula no final e ponto como separador de milhar
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value

def infer_asset_type(ticker):
    ticker = ticker.upper()
    if ticker.endswith('.SA'):
        if '11.SA' in ticker:
            return 'Fiis'
        return 'Ações'
    elif '-' in ticker or ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
        return 'Cripto'
    else:
        return 'Reits'

def get_annual_proventos_summary(proventos_df, anos_disponiveis):
    meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    meses_abrev = {
        'Janeiro': 'Jan', 'Fevereiro': 'Fev', 'Março': 'Mar', 'Abril': 'Abr',
        'Maio': 'Mai', 'Junho': 'Jun', 'Julho': 'Jul', 'Agosto': 'Ago',
        'Setembro': 'Set', 'Outubro': 'Out', 'Novembro': 'Nov', 'Dezembro': 'Dez'
    }

    resumo_rows = []
    for ano in anos_disponiveis:
        df_ano = proventos_df[proventos_df['ano'] == ano]
        pivot_ano = df_ano.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)

        for mes in meses_ordem:
            if mes not in pivot_ano.columns:
                pivot_ano[mes] = 0.0

        totais_mes = pivot_ano[meses_ordem].sum(axis=0)
        retorno_total = totais_mes.sum()
        media_mensal = retorno_total / 12

        row = {'Ano': str(ano), 'Ano_Int': int(ano)}
        for mes_completo, abrev in meses_abrev.items():
            row[abrev] = totais_mes[mes_completo]
        row['Valor Mensal'] = media_mensal
        row['Valor Anual'] = retorno_total
        resumo_rows.append(row)

    resumo_df = pd.DataFrame(resumo_rows)
    if not resumo_df.empty:
        resumo_df = resumo_df.sort_values('Ano_Int', ascending=True).drop(columns=['Ano_Int'])
    return resumo_df
