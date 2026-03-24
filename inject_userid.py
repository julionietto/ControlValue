import re

def update_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        ("db.delete_asset(asset_id_del)", "db.delete_asset(asset_id_del, st.session_state.user_id)"),
        ("db.delete_asset_operation(op_data_del['id'], asset_id)", "db.delete_asset_operation(op_data_del['id'], asset_id, st.session_state.user_id)"),
        ("db.add_asset_operation(asset_id, op_date", "db.add_asset_operation(asset_id, st.session_state.user_id, op_date"),
        ("db.update_asset_operation(op_data['id'], target_asset_id, op_date", "db.update_asset_operation(op_data['id'], target_asset_id, st.session_state.user_id, op_date"),
        ("db.get_asset_history(asset_id)", "db.get_asset_history(asset_id, st.session_state.user_id)"),
        ("db.get_asset_history(row['id'])", "db.get_asset_history(row['id'], st.session_state.user_id)"),
        ("db.update_asset(asset_data['id'],", "db.update_asset(asset_data['id'], st.session_state.user_id,"),
        ("db.update_opcao(op_data['id'],", "db.update_opcao(op_data['id'], st.session_state.user_id,"),
        ("db.delete_opcao(opcao_id)", "db.delete_opcao(opcao_id, st.session_state.user_id)"),
        ("db.get_asset_by_id(target_asset_id)", "db.get_asset_by_id(target_asset_id, st.session_state.user_id)")
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Substitutions applied successfully.")

if __name__ == '__main__':
    update_app()
