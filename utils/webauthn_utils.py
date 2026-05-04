import os
import json
import base64
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    RegistrationCredential,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

# RP_NAME (Nome que aparece no prompt do Face ID)
RP_NAME = "ControlValue"

def get_registration_options(user_id, username, rp_id):
    """Gera as opções para o navegador iniciar o registro biométrico."""
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=RP_NAME,
        user_id=str(user_id).encode(),
        user_name=username,
        user_display_name=username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return options_to_json(options)

def verify_registration(user_id, response_json, expected_challenge, rp_id):
    """Verifica a resposta do navegador e retorna os dados da credencial para salvar."""
    try:
        registration_verification = verify_registration_response(
            credential=RegistrationCredential.parse_raw(response_json),
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_origin=f"https://{rp_id}",
            expected_rp_id=rp_id,
        )
        
        return {
            "credential_id": bytes_to_base64url(registration_verification.credential_id),
            "public_key": registration_verification.credential_public_key,
            "sign_count": registration_verification.sign_count,
        }
    except Exception as e:
        print(f"Erro na verificação de registro: {e}")
        return None

def get_authentication_options(rp_id, allowed_credentials=None):
    """Gera as opções para o navegador iniciar o login biométrico."""
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allowed_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return options_to_json(options)

def verify_authentication(response_json, expected_challenge, credential_public_key, credential_current_sign_count, rp_id):
    """Verifica a resposta de login e retorna o novo sign_count."""
    try:
        auth_verification = verify_authentication_response(
            credential=AuthenticationCredential.parse_raw(response_json),
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_origin=f"https://{rp_id}",
            expected_rp_id=rp_id,
            credential_public_key=credential_public_key,
            credential_current_sign_count=credential_current_sign_count,
        )
        return auth_verification.new_sign_count
    except Exception as e:
        print(f"Erro na verificação de autenticação: {e}")
        return None
