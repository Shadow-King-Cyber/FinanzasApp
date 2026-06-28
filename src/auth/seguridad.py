import json
import os
import sys
import base64
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_ITERACIONES = 600000
_LONGITUD_CLAVE = 32


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KEY_PATH = os.path.join(BASE_DIR, "finanzas.key")


def _derivar_clave(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_LONGITUD_CLAVE,
        salt=salt,
        iterations=_ITERACIONES,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _hash_clave(clave_bytes: bytes) -> bytes:
    d = hashes.Hash(hashes.SHA256())
    d.update(clave_bytes)
    return d.finalize()


def existe_cuenta() -> bool:
    return os.path.exists(KEY_PATH)


def registrar(usuario: str, password: str, pista: str = "") -> tuple[Fernet, str]:
    salt = os.urandom(16)
    clave = _derivar_clave(password, salt)
    verificador = _hash_clave(clave)

    recovery = secrets.token_hex(8)

    datos = {
        "usuario": usuario,
        "salt": salt.hex(),
        "verificador": verificador.hex(),
        "iteraciones": _ITERACIONES,
        "pista": pista,
        "recovery": _hash_clave(recovery.encode("utf-8")).hex(),
    }
    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2)

    return Fernet(clave), recovery


def autenticar(password: str) -> tuple[Fernet, str] | None:
    if not existe_cuenta():
        return None

    with open(KEY_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)

    salt = bytes.fromhex(datos["salt"])
    verificador_guardado = bytes.fromhex(datos["verificador"])
    clave = _derivar_clave(password, salt)
    verificador_calculado = _hash_clave(clave)

    if verificador_calculado != verificador_guardado:
        return None

    return Fernet(clave), datos["usuario"]


def obtener_pista() -> str:
    if not existe_cuenta():
        return ""
    with open(KEY_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return datos.get("pista", "")


def recuperar_con_recovery(recovery: str) -> Fernet | None:
    if not existe_cuenta():
        return None

    with open(KEY_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)

    recovery_guardado = bytes.fromhex(datos["recovery"])
    recovery_calculado = _hash_clave(recovery.encode("utf-8"))

    if recovery_calculado != recovery_guardado:
        return None

    new_password = secrets.token_hex(8)
    salt = os.urandom(16)
    clave = _derivar_clave(new_password, salt)
    verificador = _hash_clave(clave)

    nueva_recovery = secrets.token_hex(8)

    datos["salt"] = salt.hex()
    datos["verificador"] = verificador.hex()
    datos["recovery"] = _hash_clave(nueva_recovery.encode("utf-8")).hex()

    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2)

    return Fernet(clave), new_password, nueva_recovery


def cambiar_password(password_actual: str, password_nueva: str) -> Fernet | None:
    resultado = autenticar(password_actual)
    if resultado is None:
        return None
    _, usuario = resultado

    with open(KEY_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)
    pista = datos.get("pista", "")

    salt = os.urandom(16)
    clave = _derivar_clave(password_nueva, salt)
    verificador = _hash_clave(clave)

    datos["salt"] = salt.hex()
    datos["verificador"] = verificador.hex()

    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2)

    return Fernet(clave)
