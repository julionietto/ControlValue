import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Provide the format function
helper = """def format_ticker_for_display(ticker_str):
    if isinstance(ticker_str, str) and ticker_str.endswith(".SA"):
        return ticker_str[:-3]
    return ticker_str
"""
content = content.replace("def format_brl(", helper + "\ndef format_brl(")

# 2. show_asset_details_screen ticker
content = content.replace(
    "ticker = asset_data['ticker']\n    current_type = asset_data['asset_type']",
    "ticker = asset_data['ticker']\n    display_ticker = format_ticker_for_display(ticker)\n    current_type = asset_data['asset_type']"
)
content = content.replace(
    "st.markdown(f\"**Ativo:** `{ticker}`\")",
    "st.markdown(f\"**Ativo:** `{display_ticker}`\")"
)
content = content.replace(
    "st.markdown(f\"**Editando Operação - Ativo:** `{ticker}`\")",
    "st.markdown(f\"**Editando Operação - Ativo:** `{display_ticker}`\")"
)
content = content.replace(
    "<h2 style=\"color: #ffffff; margin-top: 0;\">Detalhe do Ativo: {ticker}</h2>",
    "<h2 style=\"color: #ffffff; margin-top: 0;\">Detalhe do Ativo: {display_ticker}</h2>"
)

# 3. Popup dialogs
content = content.replace(
    "st.warning(f\"Tem certeza que deseja excluir o ativo **{ticker}**?\")",
    "st.warning(f\"Tem certeza que deseja excluir o ativo **{format_ticker_for_display(ticker)}**?\")"
)
content = content.replace(
    "st.markdown(f\"**Ativo:** `{ticker}`  |  **Ano:** `{ano}`\")",
    "st.markdown(f\"**Ativo:** `{format_ticker_for_display(ticker)}`  |  **Ano:** `{ano}`\")"
)
content = content.replace(
    "st.markdown(f\"### 📝 Editando Opção: `{op_data['ativo']}`\")",
    "st.markdown(f\"### 📝 Editando Opção: `{format_ticker_for_display(op_data['ativo'])}`\")"
)
content = content.replace(
    "ativo = st.text_input(\"Ativo\", value=op_data['ativo']",
    "ativo = st.text_input(\"Ativo\", value=format_ticker_for_display(op_data['ativo'])"
)

# 4. Proventos DataFrame display
content = content.replace(
    "display_df.rename(columns={'ticker': 'Ativo'}, inplace=True)",
    "display_df['ticker'] = display_df['ticker'].apply(format_ticker_for_display)\n            display_df.rename(columns={'ticker': 'Ativo'}, inplace=True)"
)

# 5. Opções DataFrame display
content = content.replace(
    "display_df.rename(columns={\n            'ativo': 'Ativo',",
    "display_df['ativo'] = display_df['ativo'].apply(format_ticker_for_display)\n        display_df.rename(columns={\n            'ativo': 'Ativo',"
)

# 6. Overview DataFrame display (Meus Ativos unified_df)
content = content.replace(
    "display_unified = unified_df.copy()\n    \n    # Função",
    "display_unified = unified_df.copy()\n    display_unified['ticker'] = display_unified['ticker'].apply(format_ticker_for_display)\n    \n    # Função"
)

# 7. Radar table
content = content.replace(
    "display_radar['Ticker'] = radar_df['ticker']",
    "display_radar['Ticker'] = radar_df['ticker'].apply(format_ticker_for_display)"
)

# 8. Plotly charts
content = content.replace(
    "fig_asset = px.pie(assets_df, values='current_value', names='ticker', title='Por Ativo Específico', hole=0.4)",
    "plot_df = assets_df.copy()\n                plot_df['ticker_display'] = plot_df['ticker'].apply(format_ticker_for_display)\n                fig_asset = px.pie(plot_df, values='current_value', names='ticker_display', title='Por Ativo Específico', hole=0.4)"
)

content = content.replace(
    "fig_us = px.bar(\n                us_df, \n                x='ticker',",
    "us_df['ticker_display'] = us_df['ticker'].apply(format_ticker_for_display)\n            fig_us = px.bar(\n                us_df, \n                x='ticker_display',"
)

content = content.replace(
    "fig_fii = px.pie(\n                    fii_assets, \n                    values='current_value', \n                    names='ticker', \n                    title='Distribuição por Ticker', \n                    hole=0.4\n                )",
    "fii_assets['ticker_display'] = fii_assets['ticker'].apply(format_ticker_for_display)\n                fig_fii = px.pie(\n                    fii_assets, \n                    values='current_value', \n                    names='ticker_display', \n                    title='Distribuição por Ticker', \n                    hole=0.4\n                )"
)

content = content.replace(
    "fig_fii_p = px.bar(\n                    fii_prov_df, \n                    x='Ativo',",
    "fii_prov_df['Ativo_display'] = fii_prov_df['Ativo'].apply(format_ticker_for_display)\n                fig_fii_p = px.bar(\n                    fii_prov_df, \n                    x='Ativo_display',"
)

content = content.replace(
    "fig_fii_ret = px.bar(\n                    fii_return_df,\n                    x='Ativo',",
    "fii_return_df['Ativo_display'] = fii_return_df['Ativo'].apply(format_ticker_for_display)\n                fig_fii_ret = px.bar(\n                    fii_return_df,\n                    x='Ativo_display',"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Modification complete.")
