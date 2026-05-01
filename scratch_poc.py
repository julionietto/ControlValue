import sys
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
import pandas as pd
import re
from datetime import datetime
import json

def scrape_investidor10(ticker, tipo):
    print(f"Scraping {ticker} ({tipo})...")
    
    # Monta a url baseada no tipo (acao, fii, stock, reit, bdr)
    if tipo == 'acao':
        url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"
    elif tipo == 'fii':
        url = f"https://investidor10.com.br/fiis/{ticker.lower()}/"
    elif tipo == 'stock':
        url = f"https://investidor10.com.br/stocks/{ticker.lower()}/"
    elif tipo == 'reit':
        url = f"https://investidor10.com.br/reits/{ticker.lower()}/"
    else:
        url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"
        
    session = cffi_requests.Session(impersonate='chrome120')
    custom_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://investidor10.com.br/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    session.headers.update(custom_headers)
    
    # Pega cookies iniciais
    try:
        session.get("https://investidor10.com.br/", timeout=15)
    except:
        pass
        
    try:
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            print(f"Erro HTTP {response.status_code} para {url}")
            return None
            
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # O investidor10 normalmente guarda a tabela de dividendos no id "table-dividends-history" ou class "table-dividends"
        table = soup.find('table', id='table-dividends-history')
        if not table:
            # tenta encontrar a tab de dividendos
            print("Tabela table-dividends-history nao encontrada via BeautifulSoup. Verificando padroes.")
            
            # Vamos procurar no raw HTML qualquer json injetado ou tabela oculta
            if "table-dividends-history" in html:
                print("O id table-dividends-history existe no HTML puro. Pode estar comentado ou num script.")
            else:
                print("Nenhuma mencao a table-dividends-history encontrada.")
            return None
            
        rows = table.find('tbody').find_all('tr')
        results = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                tipo_prov = cols[0].text.strip()
                data_com = cols[1].text.strip()
                data_pag = cols[2].text.strip()
                valor_str = cols[3].text.strip().replace('R$', '').replace('$', '').strip()
                
                try:
                    valor = float(valor_str.replace('.', '').replace(',', '.'))
                except:
                    valor = 0.0
                    
                results.append({
                    'ticker': ticker,
                    'tipo': tipo_prov,
                    'data_com': data_com,
                    'data_pag': data_pag,
                    'valor': valor
                })
        return results
    except Exception as e:
        print(f"Erro ao parsear {ticker}: {e}")
        return None

if __name__ == "__main__":
    ativos = [
        ('EGIE3', 'acao'),
        ('KLBN11', 'acao'),
        ('PETR4', 'acao'),
        ('NHI', 'reit')
    ]
    
    todos = []
    for t, tipo in ativos:
        res = scrape_investidor10(t, tipo)
        if res:
            todos.extend(res)
            
    if todos:
        df = pd.DataFrame(todos)
        
        # Filtrar os do futuro ou de maio de 2026
        # Como as datas vem como dd/mm/yyyy
        df['dt_pag_obj'] = pd.to_datetime(df['data_pag'], format='%d/%m/%Y', errors='coerce')
        hoje = datetime.now()
        
        futuros = df[df['dt_pag_obj'] >= hoje].sort_values(by=['ticker', 'dt_pag_obj'])
        print("\n--- PROVENTOS PROVISIONADOS (FUTUROS) NO INVESTIDOR10 ---")
        if futuros.empty:
            print("Nenhum provento futuro (a partir de hoje) encontrado para esses ativos.")
        else:
            for idx, row in futuros.iterrows():
                print(f"Ativo: {row['ticker']} | Tipo: {row['tipo']} | Data Com: {row['data_com']} | Pagamento: {row['data_pag']} | Valor: R$ {row['valor']}")
    else:
        print("Nenhum dado capturado.")
