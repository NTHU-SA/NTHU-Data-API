from OpenSSL import crypto, SSL


def generate_certificate(
    organization="huixing.tw",
    common_name="api.huixing.tw",
    country="TW",
    duration=(10 * 365 * 24 * 60 * 60),
    path="src/utils/openssl/",
    keyfilename="key.pem",
    certfilename="cert.pem",
):
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)

    cert = crypto.X509()
    cert.get_subject().C = country
    cert.get_subject().O = organization
    cert.get_subject().CN = common_name
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(duration)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, "sha512")

    with open(path + keyfilename, "wt") as keyfile:
        keyfile.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))
    with open(path + certfilename, "wt") as certfile:
        certfile.write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8")
        )


if __name__ == "__main__":
    generate_certificate()
