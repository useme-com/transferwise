from requests.exceptions import ConnectionError


class TransferWireExcetption(Exception):
    pass


class TransferWireNoPrivateKeyException(TransferWireExcetption):
    pass


class TransferWizeConnectionError(TransferWireExcetption, ConnectionError):
    @classmethod
    def create_from_connection_error(cls, connection_error):
        return cls(
            response=connection_error.response,
            request=connection_error.request)
