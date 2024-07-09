#
import pathlib
import json
import hashlib

from restore_zabbix import C
from slugify import slugify
from pyzabbix import ZabbixAPI

BASE_DIR = pathlib.Path(__file__).parent


(BASE_DIR / "backup").mkdir(exist_ok=True)

STATUS_OK = C.OKGREEN + "завершено" + C.ENDC


class BackupZabbix:
    def __init__(self, url, login, password):
        self.zbx = ZabbixAPI(server=url, timeout=3)
        self.login = login
        self.password = password
        self.api_version = self.zbx.api_version()

    def __enter__(self):
        self.zbx.login(self.login, self.password)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zbx.__exit__(exc_type, exc_val, exc_tb)
        return self

    def images(self):
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

        # Все изображения
        img_list = self.zbx.image.get(output="extend", select_image=True)

        # Существующие изображения
        existed_files = [p.name for p in BASE_DIR.glob("backup/images/*.json")]
        existed_images_name = [file.split("_md5")[0] for file in existed_files]
        new_images_count = 0
        updated_images_count = 0

        for img in img_list:
            del img["imageid"]  # Удаляем id изображения

            json_str_image = json.dumps(img)

            image_slug = slugify(img["name"])
            image_file_name = f"{image_slug}_md5{hashlib.md5(json_str_image.encode()).hexdigest()}.json"

            # Проверка наличия имени файла изображения в списке существующих файлов.
            if image_file_name in existed_files:
                # Пропускаем существующее бэкапы изображений
                continue

            image_status = f"{C.OKGREEN} Добавлено"  # Если изображение новое
            # Проверка наличия имени изображения в списке существующих изображений.
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
            f"    Резервное копирование изображений {STATUS_OK}\n",
            f"    {C.OKGREEN}Добавлено{C.ENDC}: {new_images_count}\n",
            f"    {C.OKBLUE}Обновлено{C.ENDC}: {updated_images_count}\n",
            f"    {C.HEADER}Всего изображений{C.ENDC}: {len(existed_files) + new_images_count}",
        )

    def regexp(self):
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

    def global_macros(self):
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

        # Все макросы
        macros_list = self.zbx.usermacro.get(output="extend", globalmacro=True)

        macros_file_path = BASE_DIR / "backup/global_macros.json"
        with open(macros_file_path, "w") as file:
            # Записываем в файл
            json.dump(macros_list, file)

        print(
            f"    Резервное копирование глобальных макросов {STATUS_OK}\n",
            f"    {C.HEADER}Всего имеется{C.ENDC}: {len(macros_list)}",
        )

    def host_groups(self):
        """
        Копируем названия групп узлов сети

        Сохраняем в виде списка в файле backup/hosts_groups.json
        """

        print()
        print(C.OKBLUE, "---> Начинаем копировать группы узлов сети", C.ENDC, "\n")

        # Получение всех групп хостов из Zabbix и сохранение их в списке.
        host_groups = [hg["name"] for hg in self.zbx.hostgroup.get(output="extend")]
        host_groups_file_path = BASE_DIR / "backup/host_groups.json"
        # Открытие файла в режиме записи.
        with open(host_groups_file_path, "w") as file:
            json.dump(host_groups, file)

        print(
            f"    Резервное копирование группы узлов сети {STATUS_OK}\n",
            f"    {C.HEADER}Всего имеется{C.ENDC}: {len(host_groups)}",
        )

    def templates(self):
        """
        Копируем все имеющиеся шаблоны в Zabbix

        Сохраняем в файле backup/templates.json
        """

        print()
        print(C.OKBLUE, "---> Начинаем копировать шаблоны", C.ENDC, "\n")

        # Создание пути к файлу templates.json.
        templates_file_path = BASE_DIR / "backup" / "templates.json"

        templates = self.zbx.template.get(output=["id", "name"])

        # Экспорт шаблонов в формате JSON.
        export_template_data = self.zbx.configuration.export(
            format="json", options={"templates": [t["templateid"] for t in templates]}
        )
        with templates_file_path.open("w") as file:
            file.write(export_template_data)

        print(
            f"    Резервное копирование шаблонов {STATUS_OK}\n",
            f"    {C.HEADER}Всего имеется{C.ENDC}: "
            f"{len(json.loads(export_template_data)['zabbix_export']['templates'])}",
        )

    def hosts(self):
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

        host_groups = self.zbx.hostgroup.get(output=["id", "name"])

        for group in host_groups:

            hosts_file_path = (
                BASE_DIR / "backup" / "hosts" / f'{slugify(group["name"])}.json'
            )

            hosts_ids = [
                h["hostid"]
                for h in self.zbx.host.get(groupids=[group["groupid"]], output="hostid")
            ]

            export_hosts_group_data = self.zbx.configuration.export(
                format="json", options={"hosts": hosts_ids}
            )

            with hosts_file_path.open("w") as file:
                file.write(export_hosts_group_data)

            print(f"    {group['name']} -> {len(hosts_ids)}")

        print(f"\n Резервное копирование узлов сети {STATUS_OK}")

    def maps(self):
        """
        Делаем резервное копирование карт сети
        """
        print()
        print(
            C.OKBLUE,
            "---> Начинаем копировать карты сети\n",
            C.ENDC,
        )

        maps_id = [m["sysmapid"] for m in self.zbx.map.get(output=["sysmapid"])]
        export_maps_data = self.zbx.configuration.export(
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
            f"    Резервное копирование {STATUS_OK}\n",
            f"    {C.HEADER}Всего карт{C.ENDC}: {maps_count}",
        )

    def scripts(self):
        """
        Сохраняем все глобальные скрипты Zabbix

        Пример:
            {
                "name": "Ping",
                "command": "ping -c 3 {HOST.CONN};",
                "host_access": "2",
                "usrgrpid": "0",
                "groupid": "0",
                "description": "",
                "confirmation": "",
                "type": "0",
                "execute_on": "2",
            }
        """

        print()
        print(
            C.OKBLUE,
            "---> Начинаем копировать глобальные скрипты\n",
            C.ENDC,
        )

        global_scripts = self.zbx.script.get(output="extend")

        for scr in global_scripts:
            del scr["scriptid"]

        with (BASE_DIR / "backup" / "global_scripts.json").open("w") as file:
            file.write(json.dumps(global_scripts))

        print(
            f"    Резервное копирование {STATUS_OK}\n",
            f"    {C.HEADER}Всего скриптов{C.ENDC}: {len(global_scripts)}",
        )

    def user_groups(self):
        """
        Копируем все группы пользователей Zabbix

        Заменяем для каждого разрешения групп узлов сети "id" на имя, для того,
        чтобы не было привязки к ID, он имеет смысл только для текущего Zabbix сервера

        Пример:
            {
                "name": "Имя группы пользователей",
                "gui_access": "0",
                "users_status": "0",
                "debug_mode": "0",
                "rights": [
                    {"permission": "2", "id": "Имя группы узлов сети"},
                    {"permission": "2", "id": "Имя группы узлов сети"},
                ],
            }
        """

        print()
        print(
            C.OKBLUE,
            "---> Начинаем копировать группы пользователей\n",
            C.ENDC,
        )
        # Собираем группы пользователей
        user_groups = self.zbx.usergroup.get(output="extend", selectRights="")

        # Словарь групп узлов сети -> ID: NAME
        # Для того, чтобы сопоставить ID текущей группы узлов сети с именем
        # Так как для восстановления понадобится только имя
        host_groups = {
            hg["groupid"]: hg["name"] for hg in self.zbx.hostgroup.get(output="extend")
        }

        # Смотрим полученные группы пользователей
        for group in user_groups:
            del group["usrgrpid"]  # Удаляем ID группы пользователя

            # Смотрим права доступа для группы
            for i, _ in enumerate(group["rights"]):
                # Преобразуем ID группы узлов сети в её имя, чтобы не было привязки с прежним ID
                group["rights"][i]["id"] = host_groups[group["rights"][i]["id"]]
            print(f"    -> {group['name']}")

        with (BASE_DIR / "backup" / "user_groups.json").open("w") as file:
            file.write(json.dumps(user_groups))

        print(f"\n    Резервное копирование {STATUS_OK}\n")

    def media_types(self):
        """
        It takes a URL, login and password and backup a Zabbix media types

        Пример:
            {
                "mediatypeid": "6",
                "type": "4",
                "name": "Имя способа оповещения",
                "smtp_server": "",
                "smtp_helo": "",
                "smtp_email": "",
                "exec_path": "",
                "gsm_modem": "",
                "username": "",
                "passwd": "",
                "status": "0",
                "smtp_port": "25",
                "smtp_security": "0",
                "smtp_verify_peer": "0",
                "smtp_verify_host": "0",
                "smtp_authentication": "0",
                "exec_params": "",
                "maxsessions": "1",
                "maxattempts": "3",
                "attempt_interval": "10s",
                "content_type": "1",
                "script": " << SCRIPT TEXT >>",
                "timeout": "30s",
                "process_tags": "1",
                "show_event_menu": "1",
                "event_menu_url": "{EVENT.TAGS.__zbx_ops_issuelink}",
                "event_menu_name": "Opsgenie: {EVENT.TAGS.__zbx_ops_issuekey}",
                "description": "Описание способа оповещения",
                "parameters": [
                    {"name": "zbxurl", "value": "{$ZABBIX.URL}"},
                    {"name": "alert_message", "value": "{ALERT.MESSAGE}"},
                    {"name": "alert_subject", "value": "{ALERT.SUBJECT}"},
                ],
            }
        """

        print()
        print(
            C.OKBLUE,
            "---> Начинаем копировать способы оповещения\n",
            C.ENDC,
        )

        media_types = self.zbx.mediatype.get(output="extend", selectMedias="extend")

        with (BASE_DIR / "backup" / "media_types.json").open("w") as file:
            file.write(json.dumps(media_types))

        print(f"    Резервное копирование {STATUS_OK}\n")

    def users(self):
        """
        Создаем резервную копию пользователей Zabbix

        Заменяем для каждого способа оповещения mediatypeid на имя, для того,
        чтобы не было привязки к ID, он имеет смысл только для текущего Zabbix сервера

        {
            "alias": "username",
            "name": "Имя",
            "surname": "Фамилия",
            "url": "",
            "autologin": "1",
            "autologout": "0",
            "lang": "ru_RU",
            "refresh": "30s",
            "type": "3",
            "theme": "default",
            "rows_per_page": "1000",
            "usrgrps": [{"usrgrpid": "9", "name": "Имя группы узла сети"}],
            "user_medias": [
                {
                    "mediatypeid": "Email-script",
                    "sendto": "admin@mail.ru",
                    "active": "0",
                    "severity": "56",
                    "period": "1-7,00:00-24:00",
                }
            ],
        }
        """

        print()
        print(
            C.OKBLUE,
            "---> Начинаем копировать пользователей\n",
            C.ENDC,
        )

        media_types = {
            mt["mediatypeid"]: mt["name"]
            for mt in self.zbx.mediatype.get(output=["name"])
        }
        users = self.zbx.user.get(
            output="extend", selectMedias="extend", selectUsrgrps=["name"]
        )

        for user in users:
            print(f"    -> {user['alias']}")
            user["user_medias"] = user["medias"]
            del user["medias"]
            del user["attempt_clock"]
            del user["attempt_failed"]
            del user["attempt_ip"]
            del user["userid"]

            # Проходимся по способам оповещения
            for mt in user["user_medias"]:
                del mt["mediaid"]
                del mt["userid"]
                # Меняем ID на имя
                mt["mediatypeid"] = media_types[mt["mediatypeid"]]

        with (BASE_DIR / "backup" / "users.json").open("w") as file:
            file.write(json.dumps(users))

        print(f"    Резервное копирование {STATUS_OK}\n")
