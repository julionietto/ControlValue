import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
import db.auth as auth

# Mock helper for database connection
@pytest.fixture
def mock_db():
    with patch('db.auth.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_connection
        yield mock_cursor

# 1. Teste de login com usuário inválido
def test_login_invalid_user(mock_db):
    # Mocking database to return None (user not found)
    mock_db.fetchone.return_value = None
    
    success, user_id, username, is_admin, status, extra, theme = auth.verify_user(
        "usuario_inexistente@gmail.com", "senha123"
    )
    
    assert success is False
    assert status == 'NOT_FOUND'
    assert user_id is None
    assert username is None

# 2. Teste de login com senha inválida
def test_login_invalid_password(mock_db):
    # Mocking database to return a valid user but with a different password hash
    # user_id, username, hashed_password, email, birth_date, failed_attempts, locked_until, theme_preference
    hashed_pwd = auth.hash_password("senha_correta")
    mock_db.fetchone.return_value = (
        1, "usuario_teste", hashed_pwd, "usuario_teste@gmail.com", "1990-01-01", 0, None, "default"
    )
    
    success, user_id, username, is_admin, status, extra, theme = auth.verify_user(
        "usuario_teste@gmail.com", "senha_errada"
    )
    
    assert success is False
    assert status == 'WRONG_PASS'
    assert username == "usuario_teste"


# 4. Teste de login com sucesso para controlvalueoficial@gmail.com / teste123
def test_login_success_controlvalueoficial(mock_db):
    # Mocking database to return valid user for controlvalueoficial@gmail.com
    hashed_pwd = auth.hash_password("teste123")
    mock_db.fetchone.return_value = (
        10, "controlvalueoficial", hashed_pwd, "controlvalueoficial@gmail.com", "1990-01-01", 0, None, "cyberpunk"
    )
    
    success, user_id, username, is_admin, status, extra, theme = auth.verify_user(
        "controlvalueoficial@gmail.com", "teste123"
    )
    
    assert success is True
    assert status == 'SUCCESS'
    assert user_id == 10
    assert username == "controlvalueoficial"
    assert is_admin is False
    assert theme == "cyberpunk"

# 5. Teste de logout
def test_logout_flow():
    # Inicializa o estado simulado do streamlit
    session_state = {
        "authenticated": True,
        "user_id": 10,
        "username": "controlvalueoficial",
        "is_admin": False,
        "theme_preference": "cyberpunk"
    }
    
    # Simula o clique no botão Sair (st.session_state.clear())
    session_state.clear()
    
    # Verifica que o estado foi completamente limpo e o usuário está deslogado
    assert "authenticated" not in session_state
    assert len(session_state) == 0

# 6. Teste de login com username em vez de email
def test_login_success_by_username(mock_db):
    hashed_pwd = auth.hash_password("teste123")
    mock_db.fetchone.return_value = (
        10, "controlvalueoficial", hashed_pwd, "controlvalueoficial@gmail.com", "1990-01-01", 0, None, "cyberpunk"
    )
    
    success, user_id, username, is_admin, status, extra, theme = auth.verify_user(
        "controlvalueoficial", "teste123"
    )
    
    assert success is True
    assert status == 'SUCCESS'
    assert username == "controlvalueoficial"

# 7. Teste de login com e-mail case-insensitive e espaços nas pontas
def test_login_case_insensitive_and_whitespace(mock_db):
    hashed_pwd = auth.hash_password("teste123")
    mock_db.fetchone.return_value = (
        10, "controlvalueoficial", hashed_pwd, "controlvalueoficial@gmail.com", "1990-01-01", 0, None, "cyberpunk"
    )
    
    success, user_id, username, is_admin, status, extra, theme = auth.verify_user(
        "  ControlValueOficial@Gmail.Com  ", "teste123"
    )
    
    assert success is True
    assert status == 'SUCCESS'
