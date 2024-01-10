import requests


class NoVariableException(Exception):
    """Ошибка при отсутствии переменных в области видимости."""

    pass


class MyException(Exception):
    """Искючение для RequestException ."""

    pass
