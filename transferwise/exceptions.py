from requests.exceptions import ConnectionError


class TransferWiseExcetption(Exception):
    pass


class TransferWiseNoPrivateKeyException(TransferWiseExcetption):
    pass


class TransferWiseConnectionError(TransferWiseExcetption, ConnectionError):
    @classmethod
    def create_from_connection_error(cls, connection_error):
        return cls(
            response=connection_error.response,
            request=connection_error.request)
