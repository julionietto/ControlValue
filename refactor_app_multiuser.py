import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Login replacement
login_old = """                    if db.verify_user(user, password):
                        st.session_state.authenticated = True
                        st.rerun()"""
login_new = """                    success, uid = db.verify_user(user, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = uid
                        st.rerun()"""
content = content.replace(login_old, login_new)

# 2. Registration replacement
reg_old = """                        if new_pass == confirm_pass:
                            db.create_user(new_user, new_pass)
                            st.success("Usuário cadastrado!")
                            st.rerun()"""
reg_new = """                        if new_pass == confirm_pass:
                            db.create_user(new_user, new_pass)
                            success, uid = db.verify_user(new_user, new_pass)
                            st.session_state.authenticated = True
                            st.session_state.user_id = uid
                            st.success("Usuário cadastrado!")
                            st.rerun()"""
content = content.replace(reg_old, reg_new)

# 3. Simple function replacements (those without arguments or with predictable ones)
replacements = [
    ("db.get_proventos()", "db.get_proventos(st.session_state.user_id)"),
    ("db.get_all_assets()", "db.get_all_assets(st.session_state.user_id)"),
    ("db.get_opcoes()", "db.get_opcoes(st.session_state.user_id)"),
    ("db.get_all_total_proventos()", "db.get_all_total_proventos(st.session_state.user_id)"),
    ("db.get_all_proventos()", "db.get_all_proventos(st.session_state.user_id)"),
    ("db.check_and_create_next_year_dashboard()", "db.check_and_create_next_year_dashboard(st.session_state.user_id)"),
    ("db.import_proventos_csv(csv_path)", "db.import_proventos_csv(csv_path, st.session_state.user_id)"),
    ("db.import_opcoes_tsv(tsv_path)", "db.import_opcoes_tsv(tsv_path, st.session_state.user_id)"),
    ("db.add_or_update_fixed_income_asset(nome, saldo)", "db.add_or_update_fixed_income_asset(nome, saldo, st.session_state.user_id)"),
    ("db.add_empty_asset(clean_name, tipo_inicial)", "db.add_empty_asset(clean_name, tipo_inicial, st.session_state.user_id)"),
    ("db.save_provento(ano, selected_mes, ticker, novo_valor)", "db.save_provento(ano, selected_mes, ticker, novo_valor, st.session_state.user_id)"),
    ("db.delete_proventos_ativo_ano(ano, ticker)", "db.delete_proventos_ativo_ano(ano, ticker, st.session_state.user_id)"),
    ("db.save_provento(ano, 'Janeiro', ticker_novo, 0.0)", "db.save_provento(ano, 'Janeiro', ticker_novo, 0.0, st.session_state.user_id)"),
    ("db.delete_proventos_ativo_ano(ano, ticker)", "db.delete_proventos_ativo_ano(ano, ticker, st.session_state.user_id)"),
    ("db.get_total_proventos_by_ticker(ticker)", "db.get_total_proventos_by_ticker(ticker, st.session_state.user_id)"),
    ("db.get_total_proventos_by_ticker(t)", "db.get_total_proventos_by_ticker(t, st.session_state.user_id)"),
    ("db.insert_opcao(ativo_val, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status)", "db.insert_opcao(ativo_val, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status, st.session_state.user_id)")
]

for old_str, new_str in replacements:
    content = content.replace(old_str, new_str)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("App refactored successfully.")
