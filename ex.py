import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from my_exception import MyException, NoVariableException

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
        'PRACTICUM_TOKEN':PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN':TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID':TELEGRAM_CHAT_ID}
    for token in tokens:
        if not tokens[token]:
            missing_tokens.append(token)
    
    if missing_tokens:
        logger.critical(f'Ошибка: отсутствуют следующие \
                         переменные: {", ".join(missing_tokens)}.')
        raise NoVariableException(f'Ошибка: отсутствуют \
                         следующие переменные: {", ".join(missing_tokens)}.')


def get_api_answer(timestamp):
    """Функция отправляет запрос на ЯП API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error('Ошибка при получении данных от API')
            raise MyException()
    except requests.RequestException:
        logger.error('Ошибка при получении данных от API')
        raise MyException("An error occurred during API request")


def check_response(response):
    """
    Функция проверяет,что ответ полученный от API.
    соответствует документации.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ принимает неверный тип данных.')
    if 'homeworks' and 'current_date' not in response:
        raise ValueError('Ответ API не содержит нужных ключей')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Homeworks должен быть списком')
    return homework


def parse_status(homework):
    """Функция проверяет статус работы."""
    if 'status' not in homework:
        logger.error('Нет статуса работы.')
        raise KeyError('Нет статуса работы.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logger.error('Некорректный статус работы')
        raise ValueError('Некорректный статус работы')
    verdict = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        logger.error('Нет названия работы')
        raise KeyError('Нет названия работы')
    homework_name = homework.get('homework_name')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция отправляет сообщение в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно отправлено.')
    except telegram.TelegramError as error:
        logger.error(f'Произошла ошибка при отправке сообщения :{error}')



    """Основная логика работы бота."""

timestamp = int(time.time())

response = get_api_answer(0)
homework = check_response(response)
print(homework)
           
