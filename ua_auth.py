"""Microsoft/Xbox/Minecraft sign-in for Unsupervised Adults MC.

No third-party launcher, password boxes or offline accounts. Microsoft login happens in
Windows' normal browser via an OAuth PKCE loopback callback. Only the refresh token and
profile metadata are cached, encrypted with Windows DPAPI for this OS user.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ACCOUNT_FILE = "account.dpapi"
CALLBACK_TIMEOUT = 180


class AuthenticationError(RuntimeError):
    pass


def is_valid_client_id(value: str) -> bool:
    import uuid
    try:
        uuid.UUID(value)
        return len(value) == 36
    except (ValueError, TypeError, AttributeError):
        return False


def require_client_id(catalog: dict) -> str:
    client_id = str(catalog.get("microsoft_client_id", "")).strip()
    if not is_valid_client_id(client_id):
        raise AuthenticationError(
            "Launcher owner setup is required: microsoft_client_id is empty in the "
            "published pack catalog. Register a Microsoft public-client app, place "
            "its Application (client) ID in pack/catalog.json, and publish it. "
            "Minecraft Services may require separate application approval."
        )
    return client_id


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _windows_dpapi(data: bytes, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise OSError("Account storage requires Windows DPAPI; run the Windows launcher on Windows.")
    if not data:
        raise ValueError("Empty protected data")
    raw = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    src = _Blob(len(data), ctypes.cast(raw, ctypes.POINTER(ctypes.c_ubyte)))
    dst = _Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    api = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    api.restype = wintypes.BOOL
    if decrypt:
        api.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = api(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dst))
    else:
        api.argtypes = [ctypes.POINTER(_Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = api(ctypes.byref(src), "Unsupervised Adults MC", None, None, None, 1, ctypes.byref(dst))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(dst.pbData, ctypes.c_void_p))


def _account_path(root: Path) -> Path:
    return root / ACCOUNT_FILE


def save_account(root: Path, session: dict) -> None:
    subset = {k: session[k] for k in ("refresh_token", "name", "id")}
    if not all(isinstance(v, str) and v for v in subset.values()):
        raise AuthenticationError("Microsoft returned an incomplete account profile")
    root.mkdir(parents=True, exist_ok=True)
    data = _windows_dpapi(json.dumps(subset).encode("utf-8"))
    tmp = root / (ACCOUNT_FILE + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(_account_path(root))


def load_account(root: Path) -> dict | None:
    path = _account_path(root)
    if not path.is_file():
        return None
    try:
        saved = json.loads(_windows_dpapi(path.read_bytes(), decrypt=True).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise AuthenticationError("Saved Microsoft login could not be opened on this Windows account. Sign in again.") from exc
    if not isinstance(saved, dict) or not all(saved.get(x) for x in ("refresh_token", "name", "id")):
        raise AuthenticationError("Saved Microsoft login is incomplete. Sign in again.")
    return saved


def sign_out(root: Path) -> None:
    _account_path(root).unlink(missing_ok=True)


def microsoft_login(client_id: str, status=print, timeout: float = CALLBACK_TIMEOUT,
                    browser_open=webbrowser.open) -> dict:
    """Browser OAuth PKCE + state checked locally; no passwords or access tokens in URLs we store."""
    import minecraft_launcher_lib

    if not is_valid_client_id(client_id):
        raise AuthenticationError("Invalid Microsoft public client ID")

    result: dict[str, str] = {}
    ready = threading.Event()
    login_state: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path not in ("/", ""):
                self.send_error(404)
                return
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("state", [""])[0] != login_state.get("state"):
                self.send_error(400, "Invalid state")
                return
            if "error" in query:
                result["error"] = query["error"][0]
            elif "code" in query:
                result["code"] = query["code"][0]
            else:
                self.send_error(400, "Missing authorization code")
                return
            payload = ("<html><body style='font-family:sans-serif;text-align:center;" 
                       "background:#17121f;color:white;padding:5rem'>"
                       "<h2>You're signed in!</h2><p>You can return to Unsupervised Adults MC.</p>"
                       "</body></html>").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            ready.set()

        def log_message(self, *_):
            # URLs can contain short-lived authorization codes; never log them.
            pass

    with HTTPServer(("127.0.0.1", 0), CallbackHandler) as server:
        server.timeout = 1.0
        redirect = f"http://localhost:{server.server_port}/"
        url, state, verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(client_id, redirect)
        login_state["state"] = state
        status("Opening Microsoft sign-in in your browser...")
        if not browser_open(url):
            raise AuthenticationError("Couldn't open the browser for Microsoft sign-in")
        deadline = time.monotonic() + timeout
        while not ready.is_set() and time.monotonic() < deadline:
            server.handle_request()
    if not ready.is_set():
        raise AuthenticationError("Microsoft login timed out. Click SIGN IN to try again.")
    if "error" in result:
        raise AuthenticationError("Microsoft login was cancelled or denied: " + result["error"])
    status("Checking your Minecraft Java Edition account...")
    try:
        return minecraft_launcher_lib.microsoft_account.complete_login(client_id, None, redirect, result["code"], verifier)
    except minecraft_launcher_lib.exceptions.AzureAppNotPermitted as exc:
        raise AuthenticationError("Microsoft has not approved this application's Minecraft API access yet. The owner must request approval.") from exc
    except minecraft_launcher_lib.exceptions.AccountNotOwnMinecraft as exc:
        raise AuthenticationError("This Microsoft account does not own Minecraft Java Edition.") from exc


def refresh_account(root: Path, client_id: str) -> dict:
    import minecraft_launcher_lib
    saved = load_account(root)
    if not saved:
        raise AuthenticationError("Please sign into Microsoft first")
    try:
        session = minecraft_launcher_lib.microsoft_account.complete_refresh(client_id, None, None, saved["refresh_token"])
    except minecraft_launcher_lib.exceptions.InvalidRefreshToken as exc:
        sign_out(root)
        raise AuthenticationError("Microsoft session expired. Please sign in again.") from exc
    save_account(root, session)
    return session


class DeviceCodeUnavailable(AuthenticationError):
    """Device login is disabled for this Microsoft application; PKCE may work."""


def _microsoft_form(url: str, params: dict) -> dict:
    """POST only to the fixed Microsoft OAuth endpoint (never to a supplied URL)."""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = Request(url, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            return json.loads(exc.read(8192).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as parse_exc:
            raise AuthenticationError(f"Microsoft sign-in service returned HTTP {exc.code}") from parse_exc
    except (URLError, TimeoutError) as exc:
        raise AuthenticationError("Could not contact Microsoft sign-in; check your internet connection") from exc


def _minecraft_session(ms_token: dict) -> dict:
    """Use Microsoft's access token to authenticate through Xbox and Minecraft."""
    import minecraft_launcher_lib as lib
    token = ms_token.get("access_token", "")
    refresh = ms_token.get("refresh_token", "")
    if not token or not refresh:
        raise AuthenticationError("Microsoft did not return a complete sign-in session")
    try:
        xbl = lib.microsoft_account.authenticate_with_xbl(token)
        xsts = lib.microsoft_account.authenticate_with_xsts(xbl["Token"])
        userhash = xbl["DisplayClaims"]["xui"][0]["uhs"]
        mc = lib.microsoft_account.authenticate_with_minecraft(userhash, xsts["Token"])
        mc_token = mc.get("access_token")
        if not mc_token:
            raise AuthenticationError(
                "Minecraft Services rejected this launcher. Microsoft's separate Minecraft "
                "application approval may be required for the launcher client ID.")
        profile = lib.microsoft_account.get_profile(mc_token)
        if profile.get("error") or not profile.get("id") or not profile.get("name"):
            raise AuthenticationError("This Microsoft account does not have a usable Minecraft Java Edition profile")
        return {**profile, "access_token": mc_token, "refresh_token": refresh}
    except AuthenticationError:
        raise
    except (KeyError, IndexError, TypeError) as exc:
        raise AuthenticationError("Microsoft/Xbox authentication returned incomplete account data") from exc


def microsoft_device_login(client_id: str, status=print, show_code=None,
                           *, post=_microsoft_form, sleep=time.sleep,
                           clock=time.monotonic) -> dict:
    """Display a Microsoft device code; user signs in using their normal browser.

    This uses no hosted API or client secret. The registered public app client ID
    remains mandatory, and Minecraft Services may independently require approval.
    """
    if not is_valid_client_id(client_id):
        raise AuthenticationError("Launcher owner must configure a valid Microsoft application ID")
    base = "https://login.microsoftonline.com/consumers/oauth2/v2.0/"
    init = post(base + "devicecode", {
        "client_id": client_id, "scope": "XboxLive.signin offline_access"})
    if init.get("error"):
        code = init["error"]
        if code in ("unauthorized_client", "unsupported_grant_type", "invalid_request"):
            raise DeviceCodeUnavailable("Microsoft device-code sign-in is unavailable for this application")
        raise AuthenticationError("Microsoft device sign-in failed: " + str(code)[:120])
    try:
        uri = init["verification_uri"]
        code = init["user_code"]
        device = init["device_code"]
        interval = max(5, min(int(init.get("interval", 5)), 60))
        expires = max(1, min(int(init["expires_in"]), 1800))
    except (KeyError, ValueError, TypeError) as exc:
        raise AuthenticationError("Microsoft did not return a usable sign-in code") from exc
    host = urllib.parse.urlsplit(uri).hostname
    if not (uri.startswith("https://") and host in ("microsoft.com", "www.microsoft.com", "login.microsoftonline.com")):
        raise AuthenticationError("Microsoft supplied an unexpected verification link")
    status(f"Open {uri} and enter code: {code}")
    if show_code:
        show_code(uri, code)
    deadline = clock() + expires
    while clock() < deadline:
        sleep(min(interval, max(0, deadline - clock())))
        reply = post(base + "token", {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "device_code": device,
        })
        error = reply.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval = min(interval + 5, 60)
            continue
        if error in ("authorization_declined", "access_denied"):
            raise AuthenticationError("Microsoft sign-in was declined")
        if error in ("expired_token", "bad_verification_code"):
            raise AuthenticationError("The Microsoft sign-in code expired; start sign-in again")
        if error:
            raise AuthenticationError("Microsoft sign-in failed: " + str(error)[:120])
        status("Microsoft authorized. Checking Minecraft Java account...")
        return _minecraft_session(reply)
    raise AuthenticationError("The Microsoft verification code expired; click Sign In for a new code")
