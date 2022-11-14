import pathlib
import json
import hashlib
from configparser import ConfigParser

from restore_zabbix import *

from requests import ConnectionError as ZabbixConnectionError

from slugify import slugify
from pyzabbix import ZabbixAPI

BASE_DIR = pathlib.Path(__file__).parent


(BASE_DIR / "backup").mkdir(exist_ok=True)

STATUS_OK = C.OKGREEN + "завершено" + C.ENDC


def backup_images(url, login, password):
    """
    Копируем все имеющиеся изображения в Zabbix

    Сохраняем в виде файлов .json с полями:
        {
            "imagetype": "1",
            "name": "Image_name",
            "image": "BASE64_IMAGE_STRING"
        }

    Имя каждого файла представляет из себя слаг имени изображения и хэш суммы файла,
    разделенного символами "_md5".

    Например для встроенного изображения Zabbix "Crypto-router_(24)" имя файла будет:

    crypto-router-24_md5df68f84de7d40c7559ee530b64460c5d.json

    Если изображение в Zabbix поменяется, то данный файл будет обновлен, в другом случае
    изменений не будет

    Все файлы располагаются в папке backup/images/

    """

    print()
    print(C.OKBLUE, "---> Начинаем копировать изображения", C.ENDC, "\n")

    (BASE_DIR / "backup" / "images").mkdir(exist_ok=True)

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        # Все изображения
        img_list = zbx.image.get(output="extend", select_image=True)

    # Существующие изображения
    existed_files = [p.name for p in BASE_DIR.glob("backup/images/*.json")]
    existed_images_name = [file.split("_md5")[0] for file in existed_files]
    new_images_count = 0
    updated_images_count = 0

    for img in img_list:
        del img["imageid"]  # Удаляем id изображения

        json_str_image = json.dumps(img)

        image_slug = slugify(img["name"])
        image_file_name = (
            f"{image_slug}_md5{hashlib.md5(json_str_image.encode()).hexdigest()}.json"
        )

        if image_file_name in existed_files:
            # Пропускаем существующее бэкапы изображений
            continue

        image_status = f"{C.OKGREEN} Добавлено"  # Если изображение новое
        if image_slug in existed_images_name:
            # Удаляем старые версии
            old_file = (BASE_DIR / "backup/images").glob(f"{image_slug}_md5*")
            for f in old_file:
                f.unlink()
            image_status = f"{C.OKBLUE} Изменено "

        with (BASE_DIR / "backup/images" / image_file_name).open("w") as file:
            # print(image_status, C.OKCYAN, image_file_name, C.ENDC)
            file.write(json_str_image)

        if "Добавлено" in image_status:
            new_images_count += 1
        else:
            updated_images_count += 1

    print(
        f" Резервное копирование изображений {STATUS_OK}\n",
        f"    {C.OKGREEN}Добавлено{C.ENDC}: {new_images_count}\n",
        f"    {C.OKBLUE}Обновлено{C.ENDC}: {updated_images_count}\n",
        f"    {C.HEADER}Всего изображений{C.ENDC}: {len(existed_files) + new_images_count}",
    )


def backup_regexp(url, login, password):
    """
    В таблице regexp хранится имя и id
    В таблице expressions хранятся значения regexp

    zabbix=# SELECT * FROM public.expressions;
     expressionid | regexpid |                                        expression
    --------------+----------+------------------------------------------------------------------------------------------
                1 |        1 | ^(btrfs|ext2|ext3|ext4|reiser|xfs|ffs|ufs|jfs|jfs2|vxfs|hfs|apfs|refs|ntfs|fat32|zfs)$
                3 |        3 | ^(Physical memory|Virtual memory|Memory buffers|Cached memory|Swap space)$
                5 |        4 | ^(MMCSS|gupdate|SysmonLog|clr_optimization_v2.0.50727_32|clr_optimization_v4.0.30319_32)$
                6 |        5 | ^(automatic|automatic delayed)$
                7 |        2 | ^Software Loopback Interface
                8 |        2 | ^(In)?[Ll]oop[Bb]ack[0-9._]*$
                9 |        2 | ^NULL[0-9.]*$
               10 |        2 | ^[Ll]o[0-9.]*$
               11 |        2 | ^[Ss]ystem$
               12 |        2 | ^Nu[0-9.]*$
    (10 rows)
    """
    ...


def backup_global_macros(url, login, password):
    """
    Копируем общесистемные макросы Zabbix

    Сохраняем в виде списка значений:
        {
            "globalmacroid": "2",
            "macro": "{$SNMP_COMMUNITY}",
            "value": "public",
            "description": "",
            "type": "0"
        }

    В файле backup/global_macros.json
    """

    print()
    print(C.OKBLUE, "---> Начинаем копировать глобальные макросы", C.ENDC, "\n")

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        # Все макросы
        macros_list = zbx.usermacro.get(output="extend", globalmacro=True)

    macros_file_path = BASE_DIR / "backup/global_macros.json"
    with open(macros_file_path, "w") as file:
        # Записываем в файл
        json.dump(macros_list, file)

    print(
        f" Резервное копирование глобальных макросов {STATUS_OK}\n",
        f"    {C.HEADER}Всего имеется{C.ENDC}: {len(macros_list)}",
    )


def backup_host_groups(url, login, password):
    """
    Копируем названия групп узлов сети

    Сохраняем в виде списка в файле backup/hosts_groups.json
    """

    print()
    print(C.OKBLUE, "---> Начинаем копировать группы узлов сети", C.ENDC, "\n")

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        host_groups = [hg["name"] for hg in zbx.hostgroup.get(output="extend")]
    host_groups_file_path = BASE_DIR / "backup/host_groups.json"
    with open(host_groups_file_path, "w") as file:
        json.dump(host_groups, file)

    print(
        f" Резервное копирование группы узлов сети {STATUS_OK}\n",
        f"    {C.HEADER}Всего имеется{C.ENDC}: {len(host_groups)}",
    )


def backup_templates(url, login, password):
    """
    Копируем все имеющиеся шаблоны в Zabbix

    Сохраняем в файле backup/templates.json
    """

    print()
    print(C.OKBLUE, "---> Начинаем копировать шаблоны", C.ENDC, "\n")

    templates_file_path = BASE_DIR / "backup" / "templates.json"

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        templates = zbx.template.get(output=["id", "name"])

        export_template_data = zbx.configuration.export(
            format="json", options={"templates": [t["templateid"] for t in templates]}
        )
    with templates_file_path.open("w") as file:
        file.write(export_template_data)

    print(
        f" Резервное копирование шаблонов {STATUS_OK}\n",
        f"    {C.HEADER}Всего имеется{C.ENDC}: "
        f"{len(json.loads(export_template_data)['zabbix_export']['templates'])}",
    )


def backup_hosts(url, login, password):
    """
    Сохраняем все узлы сети Zabbix

    Узлы поделены на группы, каждая из которых представлена в виде своего .json файла,
    который хранится в папке backup/hosts/

    Имя группы представлено в виде слага
    """

    print()
    print(
        C.OKBLUE,
        "---> Начинаем копировать узлы сети из всех групп\n",
        C.ENDC,
    )

    (BASE_DIR / "backup" / "hosts").mkdir(exist_ok=True)  # Создаем папку

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        host_groups = zbx.hostgroup.get(output=["id", "name"])

        for group in host_groups:

            hosts_file_path = (
                BASE_DIR / "backup" / "hosts" / f'{slugify(group["name"])}.json'
            )

            hosts_ids = [
                h["hostid"]
                for h in zbx.host.get(groupids=[group["groupid"]], output="hostid")
            ]

            export_hosts_group_data = zbx.configuration.export(
                format="json", options={"hosts": hosts_ids}
            )

            with hosts_file_path.open("w") as file:
                file.write(export_hosts_group_data)

            print(f"    {group['name']} -> {len(hosts_ids)}")

    print(f"\n Резервное копирование узлов сети {STATUS_OK}")


def backup_maps(url, login, password):
    print()
    print(
        C.OKBLUE,
        "---> Начинаем копировать карты сети\n",
        C.ENDC,
    )

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        maps_id = [m["sysmapid"] for m in zbx.map.get(output=["sysmapid"])]
        export_maps_data = zbx.configuration.export(
            format="json", options={"maps": maps_id}
        )

        # Удаляем триггеры для линий связи
        maps_dict = json.loads(export_maps_data)
        # Смотри все карты
        maps_count = len(maps_dict["zabbix_export"]["maps"])
        for i in range(maps_count):
            # Смотрим все линки на карте
            for j in range(len(maps_dict["zabbix_export"]["maps"][i]["links"])):
                # Обнуляем триггер линка
                maps_dict["zabbix_export"]["maps"][i]["links"][j]["linktriggers"] = []

        with (BASE_DIR / "backup" / "maps.json").open("w") as file:
            file.write(json.dumps(maps_dict))

    print(
        f" Резервное копирование {STATUS_OK}\n",
        f"    {C.HEADER}Всего карт{C.ENDC}: {maps_count}",
    )


ACTION_CHOOSE = {
    "Backup": {
        1: backup_images,
        2: backup_global_macros,
        3: backup_host_groups,
        4: backup_templates,
        5: backup_hosts,
        6: backup_maps,
    },
    "Restore": {
        1: restore_images,
        2: restore_global_macros,
        3: restore_host_groups,
        4: restore_templates,
        5: restore_hosts,
        6: restore_maps,
    },
}


def backup_restore_line(action_type: str):
    url, login, password = get_auth(for_=action_type)  # Backup/Restore

    while True:
        print(
            "\n",
            f" Выберите, какую резервную копию необходимо",
            f"{'сделать' if action_type == 'Backup' else 'восстановить'}. \n",
            " (несколько пунктов передавать через пробел) -> 1 2 5 \n\n",
            "  1. Изображения \n",
            "  2. Глобальные макросы \n",
            "  3. Группы узлов сети \n",
            "  4. Шаблоны \n",
            "  5. Узлы сети \n",
            "  6. Карты сетей \n",
            "  7. " + C.HEADER + "Все" + C.ENDC,
        )
        operation = input(" > ")
        numbers = list(
            map(
                int,
                filter(
                    lambda n: n.isdigit() and 1 <= int(n) <= 7,
                    set(operation.split()),
                ),
            )
        )
        if numbers:
            break
        print(C.FAIL, "Неверный вариант", C.ENDC)

    for n, execute_function in ACTION_CHOOSE[action_type].items():
        # Проходимся по действия
        if n in numbers or 7 in numbers:
            try:
                # Выполняем требуемую функцию Backup или Restore
                execute_function(url, login, password)
            except ZabbixConnectionError:
                print(C.FAIL, "Ошибка подключения", C.ENDC)


def get_auth(for_: str) -> tuple:
    """Получаем данные авторизации"""

    cfg_section_name: str = f"Zabbix_{for_}"
    auth_file: pathlib.Path = BASE_DIR / "auth"
    url = login = password = ""

    cfg = ConfigParser()
    cfg.read(auth_file)

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

        if not url or not login or not password:
            # Вводим данные для подключения
            print(f" Укажите данные для подключений к {C.FAIL}Zabbix API{C.ENDC}:")
            url = input("    URL > ")
            login = input("    Логин > ")
            password = input("    Пароль > ")

            save = input(
                " Сохранить данные в файле для дальнейшего использования? [Y/n] > "
            )

            # Сохраняем введенные данные пользователя
            if save.lower() == "y":
                if not cfg.has_section(cfg_section_name):
                    # Создаем секцию, если её нет
                    cfg.add_section(cfg_section_name)

                cfg.set(cfg_section_name, "url", url)
                cfg.set(cfg_section_name, "login", login)
                cfg.set(cfg_section_name, "password", password)
                with auth_file.open("w") as file:
                    cfg.write(file)
                break

        else:  # Может прошлые данные? Они есть
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

    while True:
        print(
            " Выберите, какое действие необходимо выполнить: \n",
            "  1. Сделать резервную копию \n",
            "  2. Восстановить резервную копию \n",
            "> ",
            end="",
        )
        operation = input()
        if operation.isdigit() and 1 <= int(operation) <= 2:
            break

        print(C.FAIL, "Неверный вариант", C.ENDC)

    if operation == "1":
        backup_restore_line("Backup")
    elif operation == "2":
        backup_restore_line("Restore")
