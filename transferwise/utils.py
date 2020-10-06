from . import Accounts, Profiles, Quote, Transfer
from .exceptions import UndefinedAPI


class BaseCreateByObject:
    api = None
    attributes_map = {}

    def __init__(
            self, api_base_url, api_token, private_key_path,
            private_key_passphrase=None):
        if self.api is None:
            raise UndefinedAPI()

        self._api = self.api(
            api_base_url, api_token, private_key_path, private_key_passphrase)
        self._methods = [
            method_name for method_name in dir(self._api)
            if callable(getattr(self._api, method_name)) and
            not method_name.startswith('_')]

    def __call_method(self, method_name):
        def method(**kwargs):
            for key, value in self.attributes_map.get(method_name, {}).items():
                if key in kwargs:
                    continue

                val = getattr(self, value)
                if callable(val):
                    kwargs[key] = val()
                else:
                    kwargs[key] = val

            method = getattr(self._api, method_name)
            print(kwargs)
            return method(**kwargs)
        return method

    def __getattr__(self, method_name):
        if method_name in self._methods:
            return self.__call_method(method_name)
            return

        return super().__getattr__(method_name)


class Accounts(BaseCreateByObject):
    api = Accounts


class Profiles(BaseCreateByObject):
    api = Profiles


class Quote(BaseCreateByObject):
    api = Quote


class Transfer(BaseCreateByObject):
    api = Transfer
