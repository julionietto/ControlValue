import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Radar replacement
old_radar = '''    col_radar1, col_radar2 = st.columns(2)
    with col_radar1:
        show_radar_table("Radar BR (Ações e Fiis)", ['Ações', 'Fiis'], assets_df)
    
    with col_radar2:
        show_radar_table("Radar USA (Stocks e Reits)", ['Stocks', 'Reits'], assets_df)'''

new_radar = '''    has_us_assets = not assets_df[assets_df['asset_type'].isin(['Stocks', 'Reits'])].empty

    if has_us_assets:
        col_radar1, col_radar2 = st.columns(2)
        with col_radar1:
            show_radar_table("Radar BR (Ações e Fiis)", ['Ações', 'Fiis'], assets_df)
        with col_radar2:
            show_radar_table("Radar USA (Stocks e Reits)", ['Stocks', 'Reits'], assets_df)
    else:
        show_radar_table("Radar BR (Ações e Fiis)", ['Ações', 'Fiis'], assets_df)'''
code = code.replace(old_radar, new_radar)

old_tabs = '''    tab_dist, tab_setores, tab_us, tab_fii, tab_passiva, tab_sinteticos = st.tabs([
        "Distribuição do Portfólio", 
        "Distribuição por Setores", 
        "Ativos EUA", 
        "Fundos Imobiliários (FII)",
        "Renda Passiva",
        "Dividendos Sintéticos"
    ])'''

new_tabs = '''    tabs_labels = ["Distribuição do Portfólio", "Distribuição por Setores"]
    if has_us_assets:
        tabs_labels.append("Ativos EUA")
    tabs_labels.extend(["Fundos Imobiliários (FII)", "Renda Passiva", "Dividendos Sintéticos"])
    
    tabs = st.tabs(tabs_labels)
    tab_dist = tabs[0]
    tab_setores = tabs[1]
    
    idx = 2
    if has_us_assets:
        tab_us = tabs[idx]
        idx += 1
    else:
        tab_us = None
        
    tab_fii = tabs[idx]; idx += 1
    tab_passiva = tabs[idx]; idx += 1
    tab_sinteticos = tabs[idx]'''
code = code.replace(old_tabs, new_tabs)

match = re.search(r'(    with tab_us:\n.*?)(    with tab_fii:)', code, re.DOTALL)
if match:
    block = match.group(1)
    block_lines = block.split('\\n')
    new_block_lines = [block_lines[0].replace('    with tab_us:', '    if tab_us:\\n        with tab_us:')]
    for line in block_lines[1:]:
        if line.strip():
            new_block_lines.append('    ' + line)
        else:
            new_block_lines.append(line)
    
    new_block = '\\n'.join(new_block_lines)
    code = code.replace(block, new_block)
    print("Injected UI conditions perfectly!")
else:
    print("Could not find USA Tab Block.")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
