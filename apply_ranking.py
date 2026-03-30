import re

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '# ---- Dashboard principal ----' in line:
        start_idx = i
        break

if start_idx != -1:
    for i in range(start_idx, len(lines)):
        if 'if current_view == "Opções":' in lines[i]:
            for j in range(i-1, -1, -1):
                if 'st.stop()' in lines[j]:
                    end_idx = j
                    break
            break

if start_idx != -1 and end_idx != -1:
    print(f"Found block from {start_idx} to {end_idx}")
    
    # Locate the 'else:' block for empty check
    else_idx = -1
    for i in range(start_idx, end_idx):
        if '    else:' in lines[i] and 'Nenhum dado de provento' in lines[i-1]:
            else_idx = i
            break
            
    if else_idx != -1:
        print(f"Found else block at {else_idx}")
        
        # We need to insert the tabs right after 'else:'
        # and indent everything from else_idx+1 to end_idx-1
        
        new_lines = lines[:else_idx+1]
        
        # Inject tabs
        new_lines.append('        tab_mensal, tab_ranking = st.tabs(["Histórico Mensal", "🏆 Ranking de Pagadores"])\n')
        new_lines.append('        with tab_mensal:\n')
        
        for i in range(else_idx+1, end_idx):
            line = lines[i]
            if line == '\n':
                new_lines.append(line)
            else:
                new_lines.append('    ' + line)
                
        # Now add the ranking code
        ranking_code = """
        with tab_ranking:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;'>Top Pagadores de Dividendos</h3>", unsafe_allow_html=True)
            
            # Select year
            ano_selecionado = st.selectbox("Selecione o Ano", anos_disponiveis, key="ano_ranking_prov")
            
            df_ano_ranking = proventos_df[proventos_df['ano'] == ano_selecionado].copy()
            
            if not df_ano_ranking.empty:
                ranking_df = df_ano_ranking.groupby('ticker')['valor'].sum().reset_index()
                ranking_df.rename(columns={'valor': 'Valor Anual', 'ticker': 'Ativo'}, inplace=True)
                ranking_df['Ativo'] = ranking_df['Ativo'].apply(format_ticker_for_display)
                ranking_df = ranking_df.sort_values(by='Valor Anual', ascending=False).reset_index(drop=True)
                ranking_df.index = ranking_df.index + 1
                ranking_df = ranking_df.reset_index().rename(columns={'index': 'Posição'})
                
                # Plotly Bar Chart Premium
                max_val = ranking_df['Valor Anual'].max()
                fig = px.bar(
                    ranking_df,
                    x='Ativo', 
                    y='Valor Anual',
                    text_auto='.2f',
                    color='Valor Anual',
                    color_continuous_scale='tempo',
                    template='plotly_dark'
                )
                
                fig.update_traces(
                    textfont_size=12,
                    textangle=0,
                    textposition="outside",
                    cliponaxis=False,
                    marker_line_color="#1f1f1f",
                    marker_line_width=1,
                    opacity=0.9
                )
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=30, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    coloraxis_showscale=False,
                    xaxis=dict(title=""),
                    yaxis=dict(title="Valor Anual (R$)", range=[0, max_val * 1.15], showgrid=True, gridcolor="#333333"),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Table format
                ranking_display = ranking_df.copy()
                ranking_display['Posição'] = ranking_display['Posição'].apply(lambda x: f"#{x}")
                ranking_display['Valor Anual'] = ranking_display['Valor Anual'].apply(lambda val: f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                styled_rank = ranking_display.style.set_properties(**{'text-align': 'center'}, subset=['Posição', 'Ativo']) \
                                                 .set_properties(**{'text-align': 'right'}, subset=['Valor Anual'])
                
                st.dataframe(styled_rank, hide_index=True, use_container_width=True)
            else:
                st.info(f"Nenhum provento registrado para o ano {ano_selecionado}.")
"""
        new_lines.extend(ranking_code.splitlines(True))
        
        # Add the remaining lines (st.stop() and beyond)
        new_lines.append('\n')
        new_lines.extend(lines[end_idx:])
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        print("Successfully modified app.py")
