# Fachada para o pacote db - Facilita a transição e mantém compatibilidade
from db.connection import (
    get_db_connection,
    init_connection_pool,
    init_db,
    get_database_url
)

from db.auth import (
    verify_user,
    create_user,
    get_user_count,
    hash_password,
    verify_password,
    get_user_by_email,
    get_all_users,
    admin_create_user,
    admin_update_user,
    admin_unlock_user,
    get_user_details,
    update_user_profile,
    update_user_password,
    trigger_unblock_thread,
    create_password_reset_token,
    verify_password_reset_token,
    reset_password_with_token
)

from db.assets import (
    get_all_assets,
    add_empty_asset,
    get_asset_by_id,
    add_asset_operation,
    update_asset_operation,
    delete_asset_operation,
    delete_asset,
    get_asset_history,
    add_or_update_fixed_income_asset,
    update_asset_valuation,
    get_user_allocations,
    save_user_allocations,
    recalculate_asset_balance,
    infer_asset_type,
    update_asset,
    import_assets_csv
)

from db.dividends import (
    get_proventos,
    save_provento,
    delete_proventos_ativo_ano,
    get_proventos_provisionados_calculados,
    clear_proventos_provisionados,
    add_provento_provisionado,
    import_proventos_csv,
    get_total_proventos_by_ticker,
    check_and_create_next_year_dashboard,
    get_all_total_proventos
)

from db.options import (
    get_opcoes,
    insert_opcao,
    update_opcao,
    delete_opcao,
    get_opcoes_import
)

from db.utils import (
    save_sync_log,
    get_last_sync_log,
    check_sync_today
)
