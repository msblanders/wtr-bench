"""Encrypt raw run archives for public artifact transport; decrypt only with the private key."""
import argparse
import hashlib
import hmac
import json
import secrets
import subprocess
import tempfile
from pathlib import Path


def openssl(args, data=None):
    result = subprocess.run(["openssl", *args], input=data, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("OpenSSL operation failed; no key material logged")
    return result.stdout


def seal(archive, public_key, out):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite sealed archive")
    out.mkdir(parents=True, exist_ok=True)
    password, mac_key = secrets.token_hex(32), secrets.token_bytes(32)
    with tempfile.TemporaryDirectory() as directory:
        keyfile = Path(directory) / "password"
        keyfile.write_text(password)
        keyfile.chmod(0o600)
        openssl(["enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt",
                 "-in", str(archive), "-out", str(out / "raw.enc"), "-pass", "file:" + str(keyfile)])
    keydata = json.dumps({"password": password, "mac_key": mac_key.hex()}).encode()
    wrapped = openssl(["pkeyutl", "-encrypt", "-pubin", "-inkey", str(public_key),
                       "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256"], keydata)
    (out / "key.enc").write_bytes(wrapped)
    ciphertext = (out / "raw.enc").read_bytes()
    tag = hmac.new(mac_key, ciphertext, hashlib.sha256).hexdigest()
    (out / "integrity.json").write_text(json.dumps({"format": 1, "algorithm": "AES-256-CBC-PBKDF2-200000+HMAC-SHA256; RSA-OAEP-SHA256",
                                                  "hmac_sha256": tag}, indent=2))
    print("Raw archive encrypted; private key was not supplied to this runner.")


def unseal(source, private_key, archive):
    wrapped = (source / "key.enc").read_bytes()
    keys = json.loads(openssl(["pkeyutl", "-decrypt", "-inkey", str(private_key),
                              "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256"], wrapped))
    ciphertext = (source / "raw.enc").read_bytes()
    metadata = json.loads((source / "integrity.json").read_text())
    tag = hmac.new(bytes.fromhex(keys["mac_key"]), ciphertext, hashlib.sha256).hexdigest()
    if metadata["format"] != 1 or not hmac.compare_digest(tag, metadata["hmac_sha256"]):
        raise ValueError("Archive authentication failed")
    if archive.exists():
        raise ValueError("Refusing to overwrite decrypted archive")
    with tempfile.TemporaryDirectory() as directory:
        keyfile = Path(directory) / "password"
        keyfile.write_text(keys["password"])
        keyfile.chmod(0o600)
        openssl(["enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                 "-in", str(source / "raw.enc"), "-out", str(archive), "-pass", "file:" + str(keyfile)])
    archive.chmod(0o600)
    print("Archive authenticated and decrypted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seal", "unseal"))
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "seal":
        seal(args.archive, args.key, args.directory)
    else:
        unseal(args.directory, args.key, args.archive)
