import logging
import os
import sys
import time
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv

from my_exception import EmptyApiException, MyException, NoVariableException

load_dotenv()
logger = logging.getLogger('bot_logger')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s',)
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверяет что переменные есть в глобальной области видимости."""
    missing_tokens = []
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}
    for token in tokens:
        if not tokens[token]:
            missing_tokens.append(token)

    if missing_tokens:
        logger.critical(f'Ошибка: отсутствуют следующие '
                        f'переменные: {", ".join(missing_tokens)}.')
        raise NoVariableException(
            f'Ошибка: отсутствуют '
            f'следующие переменные: {", ".join(missing_tokens)}.')


def get_api_answer(timestamp):
    """Функция отправляет запрос на ЯП API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        raise MyException('Ошибка при получении данных от API')
    except requests.RequestException:
        raise MyException('Ошибка при получении данных от API')


def check_response(response):
    """
    Функция проверяет,что ответ полученный от API.
    соответствует документации.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ принимает неверный тип данных.')
    if 'homeworks' and 'current_date' not in response:
        raise EmptyApiException('Ответ API не содержит нужных ключей')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks должен быть списком')
    return homeworks


def parse_status(homework):
    """Функция проверяет статус работы."""
    if 'status' not in homework:
        raise KeyError('Нет статуса работы.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError('Некорректный статус работы')
    verdict = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        raise KeyError('Нет названия работы')
    homework_name = homework.get('homework_name')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция отправляет сообщение в телеграмм."""
    try:
        logger.debug('Собираемся отправить сообщение.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно отправлено.')
    except telegram.TelegramError as error:
        logger.error(f'Произошла ошибка при отправке сообщения :{error}')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    check_tokens()
    timestamp = 0
    old_status = ''
    new_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', 0)
            homeworks = check_response(response)
            if len(homeworks) != 0:
                logger.error('Список домашних работ пуст.')
                message = parse_status(homeworks[0])
            else:
                message = 'К сожалению у домашек пока нет новых статусов.'
            new_status = message
            if old_status != new_status:
                send_message(bot, message)
            old_status = new_status
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error:
                send_message(bot, message)
                logger.error(f'Произошла ошибка при \
                              отправке сообщения :{error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
