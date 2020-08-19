import logging
import requests
import base64
from urllib.parse import urljoin
from OpenSSL import crypto

from .exceptions import TransferWiseNoPrivateKeyException, TransferWiseConnectionError

logger = logging.getLogger(__name__)


class TransferWiseClient:
    def __init__(
            self, api_base_url, api_token, private_key_path,
            private_key_passphrase=None):
        self.api_base_url = api_base_url
        self.api_token = api_token
        self.session = requests.Session()

        try:
            private_key_file = open(private_key_path, "r")
            private_key = private_key_file.read()
            private_key_file.close()
        except (IOError, ValueError):
            logger.exception(
                "EnterCash API: Problem with open/read private key")
            raise TransferWiseNoPrivateKeyException()

        self.private_key = crypto.load_privatekey(
            crypto.FILETYPE_PEM, private_key, private_key_passphrase)

    def _sign_token(self, approval_token: str):
        """Generate signature from json."""
        sign = crypto.sign(self.private_key, approval_token, "sha256")
        return base64.b64encode(sign)

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        }

    def _get_approval_headers(self, response):
        approval_token = response.headers.get('x-2fa-approval')
        headers = self._get_headers()
        headers.update({
            'x-2fa-approval': approval_token,
            'X-Signature': self._sign_token(approval_token)
        })
        return headers

    def _request(self, method, url, payload: dict = None, headers=None):
        url = urljoin(self.api_base_url, url)
        print(url)
        if not headers:
            headers = self._get_headers()
        try:
            response = self.session.request(
                method, url, json=payload, headers=headers)
            print(payload)
            print(headers)
            print(response,  response.headers)
            is_approval_rejected = \
                response.headers.get('x-2fa-approval-result', None) == 'REJECTED'

            if not response.ok and is_approval_rejected:
                return self._request(
                    method, url, payload, self._get_approval_headers(response))
            return response.json()
        except ConnectionError as e:
            logger.exception('TransferWise connection error')
            raise TransferWiseConnectionError.create_from_connection_error(e)


class Accounts(TransferWiseClient):
    url = 'v1/accounts'

    def create_email_recipient(self, user_id, account_name, currency, email):
        data = {
            "profile": user_id,
            "accountHolderName": account_name,
            "currency": currency.upper(),
            "type": "email",
            "details": {
                "email": email
            }
        }

        return self._request('POST', self.url, data)


class Profiles(TransferWiseClient):
    url = 'v1/profiles'

    def create_personal_profile(
            self, first_name, last_name, date_of_birth, phone_number):
        data = {
            "type": "personal",
            "details": {
                "firstName": first_name,
                "lastName": last_name,
                "dateOfBirth": date_of_birth,
                "phoneNumber": phone_number
            }
        }

        return self._request('POST', self.url, data)

    def create_business_profile(
            self, name, registration_number, company_type, company_role,
            description_of_business, webpage, acn=None, abn=None, arbn=None):
        data = {
            "type": "business",
            "details": {
                "name": name,
                "registrationNumber": registration_number,
                "companyType": company_type,
                "companyRole": company_role,
                "descriptionOfBusiness": description_of_business,
                "webpage": webpage,
                "acn": acn,
                "abn": abn,
                "arbn": arbn,
            }
        }

        return self._request('POST', self.url, data)
