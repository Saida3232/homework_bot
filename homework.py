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

formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s, %(name)s',)
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
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        missing_tokens.append('TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('TELEGRAM_CHAT_ID')

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


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        check_tokens()
    except NoVariableException as error:
        message = f'Отсутствуют нужные переменные окружения: {error}'
        send_message(bot, message)
        logger.debug('Сообщение успешно отправлено.')
        return
    #timestamp = int(time.time())
    timestamp = 1702151053

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error:
                send_message(bot, message)
                logger.error(f'Произошла ошибка при \
                              отправке сообщения :{error}')

            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
