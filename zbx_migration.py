import pathlib
import sys

from backup_zabbix import BackupZabbix, C
from restore_zabbix import RestoreZabbix

from configparser import ConfigParser
from requests import ConnectionError as ZabbixConnectionError

# Получение текущего каталога файла.
BASE_DIR = pathlib.Path(__file__).parent


def backup_restore_line(action_type: str):
    """
    Функция позволяет выбрать, какую резервную копию делать или восстанавливать.

    :param action_type: str - тип действия, которое необходимо выполнить (Backup или Restore)
    """

    url, login, password = get_auth(for_=action_type)  # Backup/Restore

    ACTION_CHOOSE = {
        1: "images",
        2: "global_macros",
        3: "host_groups",
        4: "templates",
        5: "hosts",
        6: "maps",
        7: "user_groups",
        8: "scripts",
        9: "media_types",
        10: "users",
    }

    while True:
        print(
            "\n",
            f" Выберите, какую резервную копию необходимо",
            f"{'сделать' if action_type == 'Backup' else 'восстановить'}. \n",
            " (несколько пунктов передавать через пробел) -> 1 2 5 \n\n",
            "  0.  " + C.HEADER + "Все" + C.ENDC + "\n",
            "  1.  Изображения \n",
            "  2.  Глобальные макросы \n",
            "  3.  Группы узлов сети \n",
            "  4.  Шаблоны \n",
            "  5.  Узлы сети \n",
            "  6.  Карты сетей \n",
            "  7.  Группы пользователей\n",
            "  8.  Глобальные скрипты (зависит от `3, 7`)\n",
            "  9.  Способы оповещения \n",
            "  10. Пользователи (зависит от 7, 9)\n",
        )
        operation = input(" > ")
        numbers = list(
            map(
                int,
                filter(
                    lambda n: n.isdigit() and 0 <= int(n) <= 10,
                    set(operation.split()),
                ),
            )
        )
        if numbers:
            break
        print(C.FAIL, "Неверный вариант", C.ENDC)

    # Проверка, соответствует ли тип действия строке «Backup».
    if action_type == "Backup":
        action_instance = BackupZabbix(url, login, password)
    elif action_type == "Restore":
        action_instance = RestoreZabbix(url, login, password)
    else:
        print(f"Неверное действие! {action_type}")
        sys.exit()

    with action_instance as zbx_session:
        for n, method_name in ACTION_CHOOSE.items():
            # Проходимся по действия
            # Проверяем, ввел ли пользователь «0» или «n» в списке чисел.
            if n in numbers or 0 in numbers:
                try:
                    # Выполняем требуемый метод Backup или Restore
                    getattr(zbx_session, method_name)()

                # Отлов ошибки, возникающей при сбое подключения к Zabbix API.
                except ZabbixConnectionError:
                    print(C.FAIL, "Ошибка подключения", C.ENDC)


def get_auth(for_: str) -> tuple:
    """
    Возвращаем URL, логин, пароль

    :param for_: Имя сервиса, для которого вы хотите получить авторизацию
    """

    # Переменная, которая используется для хранения имени раздела в файле конфигурации.
    cfg_section_name: str = f"Zabbix_{for_}"
    # Создание пути к файлу `auth` в том же каталоге, что и скрипт.
    auth_file: pathlib.Path = BASE_DIR / "auth"
    # Сокращение для одновременного присвоения одного и того же значения нескольким переменным.
    url = login = password = ""

    cfg = ConfigParser()
    cfg.read(auth_file)

    # Существует ли раздел в файле конфигурации.
    if cfg.has_section(cfg_section_name):
        # Смотрим, если ли прошлые данные
        url = (
            cfg.get(cfg_section_name, "url")
            if cfg.has_option(cfg_section_name, "url")
            else ""
        )
        login = (
            cfg.get(cfg_section_name, "login")
            if cfg.has_option(cfg_section_name, "login")
            else ""
        )
        password = (
            cfg.get(cfg_section_name, "password")
            if cfg.has_option(cfg_section_name, "password")
            else ""
        )

    while True:

        # Проверяем, не пуста ли какая-либо из переменных.
        if not url or not login or not password:
            # Вводим данные для подключения
            print(f" Укажите данные для подключений к {C.FAIL}Zabbix API{C.ENDC}:")
            url = input("    URL > ")
            login = input("    Логин > ")
            password = input("    Пароль > ")

            save = input(
                " Сохранить данные в файле для дальнейшего использования? [Y/n] > "
            )

            # Проверка того, ввел ли пользователь `y` или `Y`
            if save.lower() == "y":
                # Проверяем, существует ли раздел в файле конфигурации.
                if not cfg.has_section(cfg_section_name):
                    # Создаем секцию, если её нет
                    cfg.add_section(cfg_section_name)

                # Установка значения переменной `url` в ключ `url` в разделе `cfg_section_name`
                cfg.set(cfg_section_name, "url", url)
                # Установка значения переменной `login` в ключ `login` в секции `cfg_section_name`
                cfg.set(cfg_section_name, "login", login)
                # Установка значения переменной `password` в ключ `password` в секции `cfg_section_name`
                cfg.set(cfg_section_name, "password", password)
                with auth_file.open("w") as file:
                    # Записываем конфигурацию в файл.
                    cfg.write(file)
                break

        else:
            # Может использовать прошлые данные? Они есть
            print(
                f" Имеются сохраненные данные для подключения:\n{C.HEADER}",
                f"   Адрес: {url}\n",
                f"   Логин: {login}\n",
                f"   Пароль: **********",
                C.ENDC,
                sep="",
            )
            from_file = input(
                " Использовать последние сохраненные данные подключения? [Y/n] > "
            )
            # Использовать прошлые данные
            if from_file.lower() == "y":
                break

            # Переопределить данные
            elif from_file.lower() == "n":
                url = login = password = ""

            else:
                print(C.FAIL, "Ошибка ввода", C.ENDC)

    return url, login, password


if __name__ == "__main__":
    print(
        C.BOLD,
        f"Добро пожаловать в программу резервного копирования {C.FAIL}Zabbix{C.ENDC}\n",
        C.ENDC,
    )

    # Цикл, который будет выполняться до тех пор, пока пользователь не выберет пункт
    while True:
        print(
            " Выберите, какое действие необходимо выполнить: \n",
            "  1. Сделать резервную копию \n",
            "  2. Восстановить резервную копию \n",
            "> ",
            end="",
        )
        operation = input()
        # Проверка, является ли ввод числом и находится ли он между 1 и 2.
        if operation.isdigit() and 1 <= int(operation) <= 2:
            break

        print(C.FAIL, "Неверный вариант", C.ENDC)

    if operation == "1":
        backup_restore_line("Backup")
    elif operation == "2":
        backup_restore_line("Restore")
