import base64
import json

from keycloak.exceptions import KeycloakPostError, raise_error_from_response
from keycloak.keycloak_openid import URL_TOKEN, KeycloakOpenID


class KeycloakIm:

    def __init__(self, server_url, realm_name, client_id, client_secret_key):
        self.realm_name = realm_name
        self.client_id = client_id
        self.client_secret_key = client_secret_key
        self.kc_openid = KeycloakOpenID(
            server_url=server_url,
            realm_name=realm_name,
            client_id=client_id,
            client_secret_key=client_secret_key,
        )

    # async def get_secret(self):
    #    secret = await self.kc_openid.a_public_key()
    #    return secret
    def get_secret(self):
        return self.kc_openid.public_key()

    # async def decode(self, token):
    #    access_token = await self.kc_openid.a_decode_token(token)
    #    return access_token
    def decode(self, token):
        # check_token = self.kc_openid.introspect(token)
        # if not check_token or not check_token["active"]:
        #    raise InvalidTokenError
        access_token = self.kc_openid.decode_token(token)
        return access_token

    # async def client_token(self, grant_type: str = 'urn:ietf:params:oauth:grant-type:uma-ticket', audience: str = "account", claims: dict = []):
    #    params_path = {"realm-name": self.realm_name}
    #    payload = {
    #        "client_id": self.client_id,
    #        "grant_type": grant_type,
    #        "audience": audience,
    #        "claim_token": base64.urlsafe_b64encode(json.dumps(claims).encode()),
    #        "claim_token_format": "urn:ietf:params:oauth:token-type:jwt",
    #    }
    #    payload = self.kc_openid._add_secret_key(payload)
    #    content_type = self.kc_openid.connection.headers.get("Content-Type")
    #    self.kc_openid.connection.add_param_headers("Content-Type", "application/x-www-form-urlencoded")
    #    data_raw = await self.kc_openid.connection.a_raw_post(URL_TOKEN.format(**params_path), data=payload)
    #    (
    #        self.kc_openid.connection.add_param_headers("Content-Type", content_type)
    #        if content_type
    #        else self.kc_openid.connection.del_param_headers("Content-Type")
    #    )
    #    return raise_error_from_response(data_raw, KeycloakPostError)

    def client_token(
        self,
        grant_type: str = "urn:ietf:params:oauth:grant-type:uma-ticket",
        audience: str = "account",
        claims: dict = [],
    ):
        params_path = {"realm-name": self.realm_name}
        payload = {
            "client_id": self.client_id,
            "grant_type": grant_type,
            "audience": audience,
            "claim_token": base64.urlsafe_b64encode(json.dumps(claims).encode()),
            "claim_token_format": "urn:ietf:params:oauth:token-type:jwt",
        }
        payload = self.kc_openid._add_secret_key(payload)
        content_type = self.kc_openid.connection.headers.get("Content-Type")
        self.kc_openid.connection.add_param_headers(
            "Content-Type", "application/x-www-form-urlencoded"
        )
        data_raw = self.kc_openid.connection.raw_post(URL_TOKEN.format(**params_path), data=payload)
        (
            self.kc_openid.connection.add_param_headers("Content-Type", content_type)
            if content_type
            else self.kc_openid.connection.del_param_headers("Content-Type")
        )
        return raise_error_from_response(data_raw, KeycloakPostError)
