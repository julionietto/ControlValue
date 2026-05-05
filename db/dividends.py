import psycopg2.extras
from db.connection import get_db_connection, _query_to_df
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_proventos(user_id):
    """Retorna o histórico de proventos recebidos."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM proventos WHERE user_id = %s ORDER BY ano DESC, mes DESC, ticker ASC", (user_id,))
        return pd.DataFrame(cursor.fetchall())

def save_provento(ano, mes, ticker, valor, user_id):
    """Salva ou atualiza um registro de provento recebido."""
    ano = int(ano)
    ticker = str(ticker).strip().upper()
    valor = float(valor)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM proventos WHERE ano = %s AND mes = %s AND ticker = %s AND user_id = %s", (ano, mes, ticker, user_id))
        res = cursor.fetchone()
        
        if res:
            cursor.execute("UPDATE proventos SET valor = %s WHERE id = %s AND user_id = %s", (valor, res[0], user_id))
        else:
            cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)", (ano, mes, ticker, valor, user_id))
        conn.commit()

def delete_proventos_ativo_ano(ano, ticker, user_id):
    """Remove todos os proventos de um ativo em um ano específico."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proventos WHERE ano = %s AND ticker = %s AND user_id = %s", (ano, ticker, user_id))
        conn.commit()

def get_proventos_provisionados_calculados(user_id):
    """
    Retorna os proventos provisionados cruzados com a quantidade de ativos do usuário na data com,
    respeitando a posição histórica até aquela data.
    """
    query = """
        SELECT 
            p.*, 
            COALESCE(SUM(h.quantity), 0) as quantidade_elegivel
        FROM proventos_provisionados p
        JOIN assets a ON p.ticker = a.ticker AND p.user_id = a.user_id
        LEFT JOIN asset_history h ON h.asset_id = a.id AND h.date <= p.data_com
        WHERE p.user_id = %s
        GROUP BY p.id, p.ticker, p.data_pagamento, p.valor
        ORDER BY p.data_pagamento ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(user_id,))

def clear_proventos_provisionados(user_id):
    """Limpa a tabela de proventos futuros do usuário."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proventos_provisionados WHERE user_id = %s", (user_id,))
        conn.commit()

def add_provento_provisionado(user_id, ticker, tipo, data_com, data_pagamento, valor):
    """Adiciona um novo provento futuro mapeado."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO proventos_provisionados (ticker, tipo, data_com, data_pagamento, valor, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticker, tipo, data_com, data_pagamento, valor, user_id))
        conn.commit()

def import_proventos_csv(file_content, user_id):
    """Importa proventos de um arquivo CSV (layout padrão do sistema)."""
    import csv
    import io
    
    meses_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
        'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
        'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
    }
    
    try:
        if isinstance(file_content, str):
            import os
            if not os.path.exists(file_content):
                return False, "Arquivo não encontrado."
            f = open(file_content, mode='r', encoding='utf-8')
        else:
            if hasattr(file_content, 'getvalue'):
                content = file_content.getvalue()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                f = io.StringIO(content)
            else:
                f = file_content

        content_for_validation = f.read()
        f.seek(0)
        
        validation_f = io.StringIO(content_for_validation)
        reader = csv.reader(validation_f, delimiter=',')
        header = next(reader)
        if not header or len(header) < 14:
            return False, "Layout do arquivo de Proventos inválido."
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM proventos WHERE user_id = %s", (user_id,))
            
            reader = csv.reader(io.StringIO(content_for_validation), delimiter=',')
            next(reader) # pular cabeçalho
            
            meses_colunas = [col.strip() for col in header[2:]]
            
            for row in reader:
                if not row or len(row) < 3:
                    continue
                    
                ano = int(row[0].strip())
                ticker = row[1].strip().upper()
                if "." not in ticker and len(ticker) >= 4:
                    ticker += ".SA"
                    
                for idx, val_str in enumerate(row[2:]):
                    val_str = val_str.strip()
                    if not val_str:
                        continue
                        
                    if idx < len(meses_colunas):
                        mes_original = meses_colunas[idx]
                        mes_pt = meses_map.get(mes_original, idx + 1)
                        val_clean = val_str.replace('R$', '').replace('$', '').replace(',', '.').strip()
                        valor = float(val_clean)
                        
                        if valor > 0:
                            cursor.execute(
                                "INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)",
                                (ano, mes_pt, ticker, valor, user_id)
                            )
            conn.commit()
            return True, "Importação de Proventos concluída com sucesso."
    except Exception as e:
        return False, f"Erro ao importar: {str(e)}"

def get_total_proventos_by_ticker(ticker, user_id):
    ticker = ticker.strip().upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE ticker = %s AND user_id = %s", (ticker, user_id))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def check_and_create_next_year_dashboard(user_id):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    if now.month == 12:
        current_year = now.year
        next_year = current_year + 1
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM proventos WHERE ano = %s AND user_id = %s LIMIT 1", (next_year, user_id))
            if cursor.fetchone() is None:
                cursor.execute("SELECT DISTINCT ticker FROM proventos WHERE ano = %s AND user_id = %s", (current_year, user_id))
                tickers = cursor.fetchall()
                if not tickers:
                    cursor.execute("SELECT DISTINCT ticker FROM assets WHERE user_id = %s", (user_id,))
                    tickers = cursor.fetchall()
                for row in tickers:
                    cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, 1, %s, 0.0, %s)", (next_year, row[0], user_id))
                conn.commit()
                return True
    return False

def get_all_total_proventos(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE user_id = %s", (user_id,))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def upsert_provento_provisionado(ticker, tipo, data_com, data_pagamento, valor, user_id):
    """Insere ou atualiza um provento provisionado (upsert)."""
    ticker = str(ticker).strip().upper()
    valor = float(valor)
    
    # Normalização de datas conforme esperado pelo banco (DATE)
    # O scraper pode retornar objetos date ou strings DD/MM/YYYY
    try:
        if isinstance(data_com, str):
            dt_com_db = datetime.strptime(data_com, '%d/%m/%Y').strftime('%Y-%m-%d')
        else:
            dt_com_db = data_com
            
        if isinstance(data_pagamento, str):
            dt_pag_db = datetime.strptime(data_pagamento, '%d/%m/%Y').strftime('%Y-%m-%d')
        else:
            dt_pag_db = data_pagamento
    except Exception as e:
        import logging
        logging.warning(f"Erro ao formatar data no upsert_provento: {e}")
        return
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Verifica se já existe um provento idêntico para atualizar o valor
        # Incluímos tipo e data_com na busca para evitar que proventos diferentes na mesma data se sobreponham
        cursor.execute(
            "SELECT id FROM proventos_provisionados WHERE ticker = %s AND tipo = %s AND data_com = %s AND data_pagamento = %s AND user_id = %s",
            (ticker, tipo, dt_com_db, dt_pag_db, user_id)
        )
        res = cursor.fetchone()
        
        if res:
            cursor.execute(
                "UPDATE proventos_provisionados SET valor = %s, tipo = %s, data_com = %s WHERE id = %s AND user_id = %s",
                (valor, tipo, dt_com_db, res[0], user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO proventos_provisionados (ticker, tipo, data_com, data_pagamento, valor, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (ticker, tipo, dt_com_db, dt_pag_db, valor, user_id)
            )
        conn.commit()

def sync_proventos_from_provisionados(user_id):
    """
    Sincroniza a tabela proventos com os valores proventos_provisionados calculados,
    respeitando a regra do mês de Dezembro para pagamentos do ano seguinte.
    """
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    current_year = now.year
    current_month = now.month
    
    with get_db_connection() as conn:
        # Busca todos os proventos provisionados calculando a quantidade elegível
        # A quantidade elegível é a quantidade que o usuário tinha na 'data_com'
        query = '''
            SELECT
                p.ticker,
                p.data_pagamento,
                p.valor,
                COALESCE(SUM(h.quantity), 0) as quantidade_elegivel
            FROM proventos_provisionados p
            JOIN assets a ON a.ticker = p.ticker AND a.user_id = p.user_id
            LEFT JOIN asset_history h ON h.asset_id = a.id AND CAST(h.date AS DATE) <= p.data_com
            WHERE p.user_id = %s
            GROUP BY p.id, p.ticker, p.data_pagamento, p.valor
        '''
        df = _query_to_df(query, conn, params=(user_id,))
        
    if df.empty:
        return

    # Converte data_pagamento para datetime para extrair ano e mês
    df['data_pagamento'] = pd.to_datetime(df['data_pagamento'])
    df['ano_pag'] = df['data_pagamento'].dt.year
    df['mes_pag_num'] = df['data_pagamento'].dt.month
    
    # Calcula total a receber por evento (quantidade acumulada * valor por cota)
    df['total_receber'] = df['valor'] * df['quantidade_elegivel']
    
    # Agrupa por ticker, ano, mes
    grouped = df.groupby(['ticker', 'ano_pag', 'mes_pag_num'])['total_receber'].sum().reset_index()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for index, row in grouped.iterrows():
            ticker = row['ticker']
            ano = int(row['ano_pag'])
            mes_num = int(row['mes_pag_num'])
            total_valor = float(row['total_receber'])
                
            # Regra de negócio: Para proventos provisionados para o ano seguinte, 
            # os valores somente serão atualizados depois do dia 01 de Dezembro do ano corrente.
            if ano > current_year and current_month < 12:
                continue
                
            # Verifica se já existe na tabela proventos
            cursor.execute("SELECT id FROM proventos WHERE ano = %s AND mes = %s AND ticker = %s AND user_id = %s", (ano, mes_num, ticker, user_id))
            res = cursor.fetchone()
            
            if res:
                # Atualiza com o valor exato (sobrepondo valor anterior/manual)
                cursor.execute("UPDATE proventos SET valor = %s WHERE id = %s AND user_id = %s", (total_valor, res[0], user_id))
            else:
                # Insere
                cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)", (ano, mes_num, ticker, total_valor, user_id))
                
        # Rotina de Limpeza: Remove registros da tabela de provisionados onde a data de pagamento já passou
        hoje_sp = now.date()
        cursor.execute("DELETE FROM proventos_provisionados WHERE user_id = %s AND data_pagamento < %s", (user_id, hoje_sp))
        
        conn.commit()
