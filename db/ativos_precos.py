import csv
import io
import pandas as pd
import unicodedata
from db.connection import get_db_connection, _query_to_df, clear_db_cache


def _normalize_col_name(col: str) -> str:
    """Normaliza nome de coluna removendo acentos, espaços e caracteres especiais."""
    if not col:
        return ""
    col_str = str(col).strip().lower()
    nfkd = unicodedata.normalize('NFKD', col_str)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).replace("_", " ").replace("-", " ")


def _parse_price_value(val) -> float:
    """Converte valor textual em float suportando formato brasileiro e americano."""
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str in ['-', 'N/A', 'null', 'None']:
        return 0.0
    
    # Remove símbolos de moeda e espaços
    val_str = val_str.replace('R$', '').replace('$', '').replace(' ', '')
    
    # Se contiver vírgula e ponto (ex: 1.234,56), remove o ponto e troca a vírgula por ponto
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
        
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def import_ativos_precos_csv(file_content, replace_existing=True):
    """
    Importa arquivo CSV de Ativos e Preços contendo 4 colunas:
    Código, Preço Teto, Preço Justo e Mercado.
    
    Retorna (sucesso: bool, mensagem: str, total_importados: int).
    """
    try:
        # 1. Leitura de bytes / string com fallback de encoding
        if hasattr(file_content, 'getvalue'):
            raw_bytes = file_content.getvalue()
        elif hasattr(file_content, 'read'):
            raw_bytes = file_content.read()
            if isinstance(raw_bytes, str):
                raw_bytes = raw_bytes.encode('utf-8')
        elif isinstance(file_content, bytes):
            raw_bytes = file_content
        elif isinstance(file_content, str):
            raw_bytes = file_content.encode('utf-8')
        else:
            return False, "Tipo de arquivo inválido para leitura.", 0

        # Tenta decodificar UTF-8 (com ou sem BOM) ou latin-1 / cp1252
        text_content = None
        for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                text_content = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            return False, "Não foi possível decodificar o arquivo. Certifique-se de que é um CSV válido.", 0

        # 2. Detecção de delimitador (, ou ;)
        sample = text_content[:2048]
        delimiter = ';' if sample.count(';') > sample.count(',') else ','

        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        try:
            raw_header = next(reader)
        except StopIteration:
            return False, "O arquivo CSV enviado está vazio.", 0

        if not raw_header:
            return False, "Cabeçalho do arquivo CSV não encontrado.", 0

        # Mapeia colunas pelo nome ou pela posição
        col_indices = {}
        for idx, col in enumerate(raw_header):
            norm = _normalize_col_name(col)
            if any(k in norm for k in ['codigo', 'ticker', 'ativo', 'cod']):
                col_indices['codigo'] = idx
            elif any(k in norm for k in ['preco teto', 'teto']):
                col_indices['preco_teto'] = idx
            elif any(k in norm for k in ['preco justo', 'justo']):
                col_indices['preco_justo'] = idx
            elif any(k in norm for k in ['mercado', 'market', 'tipo']):
                col_indices['mercado'] = idx

        # Fallback posicional se faltar alguma coluna e houver ao menos 4 colunas
        if len(raw_header) >= 4:
            if 'codigo' not in col_indices: col_indices['codigo'] = 0
            if 'preco_teto' not in col_indices: col_indices['preco_teto'] = 1
            if 'preco_justo' not in col_indices: col_indices['preco_justo'] = 2
            if 'mercado' not in col_indices: col_indices['mercado'] = 3

        missing = [c for c in ['codigo', 'preco_teto', 'preco_justo', 'mercado'] if c not in col_indices]
        if missing:
            return False, f"O arquivo deve conter as colunas: Código, Preço Teto, Preço Justo e Mercado. Colunas não identificadas: {', '.join(missing)}.", 0

        # 3. Processamento das linhas
        records_to_insert = []
        seen_codigos = set()

        for line_num, row in enumerate(reader, start=2):
            if not row or all(str(cell).strip() == "" for cell in row):
                continue
            
            try:
                codigo_raw = row[col_indices['codigo']].strip().upper() if col_indices['codigo'] < len(row) else ""
                if not codigo_raw:
                    continue

                teto_val = _parse_price_value(row[col_indices['preco_teto']]) if col_indices['preco_teto'] < len(row) else 0.0
                justo_val = _parse_price_value(row[col_indices['preco_justo']]) if col_indices['preco_justo'] < len(row) else 0.0
                mercado_raw = row[col_indices['mercado']].strip() if col_indices['mercado'] < len(row) else "Geral"

                # Se houver duplicidade no mesmo arquivo, o último sobrescreve
                records_to_insert.append({
                    'codigo': codigo_raw,
                    'preco_teto': teto_val,
                    'preco_justo': justo_val,
                    'mercado': mercado_raw if mercado_raw else "Geral"
                })
                seen_codigos.add(codigo_raw)
            except Exception as e:
                return False, f"Erro ao processar linha {line_num}: {e}", 0

        if not records_to_insert:
            return False, "Nenhum registro válido encontrado no arquivo CSV.", 0

        # 4. Gravação no banco de dados
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if replace_existing:
                cursor.execute("DELETE FROM ativos_precos;")

            # Insere com Upsert caso haja repetição
            insert_query = """
                INSERT INTO ativos_precos (codigo, preco_teto, preco_justo, mercado, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (codigo) DO UPDATE 
                SET preco_teto = EXCLUDED.preco_teto,
                    preco_justo = EXCLUDED.preco_justo,
                    mercado = EXCLUDED.mercado,
                    updated_at = CURRENT_TIMESTAMP;
            """
            for rec in records_to_insert:
                cursor.execute(insert_query, (rec['codigo'], rec['preco_teto'], rec['preco_justo'], rec['mercado']))

            conn.commit()
            clear_db_cache()

        total = len(seen_codigos)
        return True, f"Importação concluída com sucesso! {total} ativo(s) cadastrado(s) na tabela.", total

    except Exception as e:
        return False, f"Erro inesperado durante a importação: {str(e)}", 0


def get_all_ativos_precos() -> pd.DataFrame:
    """Retorna todos os registros da tabela ativos_precos ordenados por mercado e código."""
    with get_db_connection() as conn:
        query = """
            SELECT 
                id, 
                codigo, 
                preco_teto, 
                preco_justo, 
                mercado, 
                created_at, 
                updated_at 
            FROM ativos_precos 
            ORDER BY mercado ASC, codigo ASC;
        """
        return _query_to_df(query, conn)


def delete_all_ativos_precos():
    """Remove todos os registros da tabela ativos_precos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ativos_precos;")
        conn.commit()
        clear_db_cache()


def update_ativo_preco(item_id: int, preco_teto: float, preco_justo: float) -> bool:
    """Atualiza o Preço Teto e Preço Justo de um registro específico na tabela ativos_precos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ativos_precos
            SET preco_teto = %s,
                preco_justo = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """, (float(preco_teto), float(preco_justo), int(item_id)))
        conn.commit()
        clear_db_cache()
        return True


def update_user_assets_from_ativos_precos():
    """
    Atualiza Preço Teto, Preço Justo e Moeda de todos os ativos de todos os usuários
    cadastrados no sistema com base na tabela ativos_precos.
    Retorna (sucesso: bool, mensagem: str, total_atualizados: int, total_usuarios: int).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verifica se existem registros na tabela de referência
        cursor.execute("SELECT COUNT(*) FROM ativos_precos;")
        total_ref = cursor.fetchone()[0] or 0
        if total_ref == 0:
            return False, "A tabela de Ativos e Preços está vazia. Importe um arquivo CSV antes de atualizar.", 0, 0

        # 2. Executa a atualização de todos os ativos de todos os usuários
        query = """
            UPDATE assets a
            SET 
                price_ceiling = ap.preco_teto,
                fair_value = ap.preco_justo,
                currency = CASE 
                    WHEN UPPER(TRIM(ap.mercado)) IN ('EUA', 'USA', 'US', 'ESTADOS UNIDOS') THEN 'USD'
                    WHEN UPPER(TRIM(ap.mercado)) IN ('BRASIL', 'BR', 'BRAZIL') THEN 'BRL'
                    WHEN a.asset_type IN ('Stocks', 'Reits') THEN 'USD'
                    ELSE 'BRL'
                END
            FROM ativos_precos ap
            WHERE UPPER(TRIM(REPLACE(a.ticker, '.SA', ''))) = UPPER(TRIM(REPLACE(ap.codigo, '.SA', '')))
            RETURNING a.id, a.user_id;
        """
        cursor.execute(query)
        updated_rows = cursor.fetchall()
        conn.commit()
        clear_db_cache()

        total_updated = len(updated_rows)
        affected_users = len(set(r[1] for r in updated_rows)) if updated_rows else 0
        
        return True, f"Atualização realizada com sucesso! {total_updated} ativo(s) atualizado(s) em {affected_users} usuário(s).", total_updated, affected_users

