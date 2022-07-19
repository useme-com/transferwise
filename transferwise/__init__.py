import logging
import requests
import base64
from urllib.parse import urljoin
from OpenSSL import crypto

from .exceptions import TransferWiseNoPrivateKeyException, \
    TransferWiseConnectionError, QuoteAttributesError

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
        if not headers:
            headers = self._get_headers()
        try:
            response = self.session.request(
                method, url, json=payload, headers=headers)
            is_approval_rejected = \
                response.headers.get('x-2fa-approval-result', None) == \
                'REJECTED'

            if not response.ok and is_approval_rejected:
                return self._request(
                    method, url, payload, self._get_approval_headers(response))
            return response.json()
        except ConnectionError as e:
            logger.exception('TransferWise connection error')
            raise TransferWiseConnectionError.create_from_connection_error(e)


class Accounts(TransferWiseClient):
    url = 'v1/accounts'
    url_v2 = 'v2/accounts'

    borderless_url = 'v1/borderless-accounts'

    def create_email_recipient(
            self, profile_id, account_name, currency, email):
        data = {
            "profile": profile_id,
            "accountHolderName": account_name,
            "currency": currency.upper(),
            "type": "email",
            "details": {
                "email": email
            }
        }

        return self._request('POST', self.url, data)

    def create_recipient(
            self, profile_id, account_name, currency, account_type=None,
            **kwargs):
        data = {
            "profile": profile_id,
            "accountHolderName": account_name,
            "currency": currency.upper(),
            "type": "email",
        }

        if account_type:
            data['type'] = account_type

        if kwargs:
            data['details'] = kwargs

        return self._request('POST', self.url, data)

    def create_creditcard_recipient(
            self, account_name, currency, country, cc_token, cc_owner_address,
            cc_owner_country, cc_owner_post_code, cc_owner_state,
            cc_owner_city):

        data = {
            "accountHolderName": account_name,
            "currency": currency,
            "country": country,
            "type": "CARD",
            "details": {
                "cardToken": cc_token,
                "address": {
                    "firstLine": cc_owner_address,
                    "country": cc_owner_country,
                    "postCode": cc_owner_post_code,
                    "state": cc_owner_state,
                    "city": cc_owner_city
                }
            }
        }
        return self._request('POST', self.url_v2, data)

    def create_creditcard_recipient_by_kwargs(
            self, account_name, currency, country, **kwargs):

        data = {
            "accountHolderName": account_name,
            "currency": currency,
            "country": country,
            "type": "CARD",
        }

        if kwargs:
            data['details'] = kwargs

        return self._request('POST', self.url, data)

    def get_balance(self, profile_id):
        url = f'{self.borderless_url}/?profileId={profile_id}'
        return self._request('GET', url)

    def get_requirements(
            self, source_currency, target_currency, source_amount, refresh_requirements=None):
        if not refresh_requirements:
            url = f'v1/account-requirements?source={source_currency}&target='\
                f'{target_currency}&sourceAmount={source_amount}'

            return self._request('GET', url)

        data = {
            "type": "personal",
            "details": refresh_requirements,
        }

        url = f'v1/account-requirements?source={source_currency}&target='\
            f'{target_currency}&sourceAmount={source_amount}'
        return self._request('POST', url, data)


class Profiles(TransferWiseClient):
    url = 'v1/profiles'
    url_v3 = 'v3/profiles'

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

    def get_profiles(self):
        return self._request('GET', self.url)

    def fund(self, profile_id, transfer_id):
        url = f'{self.url_v3}/{profile_id}/transfers/{transfer_id}/payments'
        data = {
            "type": "BALANCE"
         }
        return self._request('POST', url, data)


class Quote(TransferWiseClient):
    url = 'v2/quotes'

    def create_quote(
            self, profile_id, source_currency, target_currency,
            source_amount=None, target_amount=None, target_account=None):

        if not source_amount and not target_amount:
            raise QuoteAttributesError(
                "source_amount OR target_amount are required, never both.")

        if source_amount and target_amount:
            raise QuoteAttributesError(
                "source_amount OR target_amount are required, never both.")

        data = {
          "profile": profile_id,
          "sourceCurrency": source_currency.upper(),
          "targetCurrency": target_currency.upper(),
          "targetAmount": target_amount,
          "sourceAmount": source_amount,
        }

        if target_account:
            data['targetAccount'] = target_account

        return self._request('POST', self.url, data)

    def get_account_requirements(self, quote_id):
        url = f"{self.url}/{quote_id}/account-requirements"
        return self._request('GET', url)


class Transfer(TransferWiseClient):
    url_v1 = 'v1/transfers'
    url = 'v2/transfers'

    def create_transfer(
            self, target_account, quote_id, transaction_id,
            details_reference=None, details_transfer_purpose=None,
            details_source_of_Funds=None, **kwargs):

        data = {
          "targetAccount": target_account,
          "quoteUuid": quote_id,
          "customerTransactionId": transaction_id,
          "details": {}
        }

        if details_reference:
            data['details']['reference'] = details_reference
        if details_transfer_purpose:
            data['details']['transferPurpose'] = details_transfer_purpose
        if details_transfer_purpose:
            data['details']['sourceOfFunds'] = details_source_of_Funds

        if kwargs:
            data['details'].update(**kwargs)

        return self._request('POST', self.url_v1, data)

    def list(self, profile_id, status, source_currency, created_date_start,
             created_date_end, offset=0, limit=100):
        url = f"{self.url_v1}/?offset={offset}&limit={limit}&" \
            f"status={status}&sourceCurrency={source_currency}&" \
            f"createdDateStart={created_date_start}&" \
            f"createdDateEnd={created_date_end}"

        return self._request('GET', url)

    def cancel(self, transfer_id):
        url = f"{self.url_v1}/{transfer_id}/cancel"
        return self._request('PUT', url)


class CardTokenization(TransferWiseClient):
    url = 'v3/card'

    def tokenize(self, card_number):
        data = {
            'cardNumber': card_number,
        }

        return self._request('POST', self.url, data)
