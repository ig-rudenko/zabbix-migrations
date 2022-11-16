import pathlib
import json
import random
from string import ascii_letters, digits

from slugify import slugify
from pyzabbix import ZabbixAPI
from pyzabbix import api


__all__ = [
    "restore_images",
    "restore_global_macros",
    "restore_host_groups",
    "restore_templates",
    "restore_hosts",
    "restore_maps",
    "restore_scripts",
    "restore_user_groups",
    "restore_media_types",
    "restore_users",
    "C",
]


class C:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


BASE_DIR = pathlib.Path(__file__).parent
STATUS_OK = C.OKGREEN + "завершено" + C.ENDC


def restore_images(url, login, password):
    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать изображения", C.ENDC, "\n")

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        existed_images = 0
        added_images = 0

        for image_file in BASE_DIR.glob("backup/images/*.json"):
            with open(image_file.absolute()) as file:
                try:
                    image_data = json.load(file)
                    zbx.image.create(**image_data)
                    added_images += 1
                except json.JSONDecodeError:
                    print(
                        C.FAIL,
                        "Error to decode image file",
                        image_file.absolute(),
                        C.ENDC,
                    )

                except api.ZabbixAPIException as e:
                    if e.error["code"] == -32602:  # Уже есть такое изображение
                        existed_images += 1
                    else:
                        print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    print(f"    {C.OKGREEN}Было добавлено картинок{C.ENDC}: {added_images}")
    if existed_images:
        print(f"    {C.OKBLUE}Уже существовали{C.ENDC}: {existed_images}")


def restore_global_macros(url, login, password):
    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать глобальные макросы", C.ENDC, "\n")

    macros_file = BASE_DIR / "backup" / "global_macros.json"
    existed_macros = 0
    added_macros = 0

    if macros_file.exists():
        with macros_file.open("r") as file:
            data = json.load(file)

        with ZabbixAPI(server=url) as zbx:
            zbx.login(user=login, password=password)

            for macro in data:
                del macro["globalmacroid"]
                try:
                    zbx.usermacro.createglobal(**macro)
                    added_macros += 1
                except api.ZabbixAPIException as e:
                    if e.error["code"] == -32602:  # Уже есть такой макрос
                        existed_macros += 1
                    else:
                        print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    print(f"    {C.OKGREEN}Было добавлено макросов{C.ENDC}: {added_macros}")
    if existed_macros:
        print(f"    {C.OKBLUE}Уже существовали{C.ENDC}: {existed_macros}")


def restore_host_groups(url, login, password):
    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать группы узлов сети", C.ENDC, "\n")

    host_groups_file = BASE_DIR / "backup" / "host_groups.json"
    existed_host_groups = 0
    added_host_groups = 0

    if host_groups_file.exists():
        with host_groups_file.open("r") as file:
            host_groups = json.load(file)

        with ZabbixAPI(server=url) as zbx:
            zbx.login(user=login, password=password)

            for gr_name in host_groups:
                try:
                    zbx.hostgroup.create(name=gr_name)
                    added_host_groups += 1
                except api.ZabbixAPIException as e:
                    if e.error["code"] == -32602:  # Уже есть такой макрос
                        existed_host_groups += 1
                    else:
                        print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    print(f"    {C.OKGREEN}Было добавлено групп узлов сети{C.ENDC}: {added_host_groups}")
    if existed_host_groups:
        print(f"    {C.OKBLUE}Уже существовали{C.ENDC}: {existed_host_groups}")


def restore_templates(url, login, password):
    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать шаблоны", C.ENDC, "\n")

    template_file_path = BASE_DIR / "backup" / "templates.json"

    rules = {
        "templates": {
            "createMissing": True,
            "updateExisting": False,
        },
        "valueMaps": {"createMissing": True, "updateExisting": False},
        "httptests": {"createMissing": True, "updateExisting": True},
        "graphs": {"createMissing": True, "updateExisting": True},
        "triggers": {"createMissing": True, "updateExisting": True},
        "discoveryRules": {"createMissing": True, "updateExisting": True},
        "items": {"createMissing": True, "updateExisting": True, "deleteMissing": True},
        "applications": {"createMissing": True},
        "templateLinkage": {"createMissing": True},
        "templateScreens": {"createMissing": True, "updateExisting": True},
    }

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        with template_file_path.open("r") as t_file:
            template_data = t_file.read()
            try:
                zbx_import = getattr(zbx.configuration, "import")
                zbx_import(format="json", rules=rules, source=template_data)
            except Exception as e:
                print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    print(
        f"    Было восстановлено шаблонов:",
        f"{len(json.loads(template_data)['zabbix_export']['templates'])}",
    )


def restore_hosts(url, login, password):
    input_groups = input(
        "    Укажите названия файлов узлов сети через пробел (без .json),\n"
        "    которые надо восстановить. Ничего не указывайте, если надо все.\n"
        " > "
    )
    from_groups = [slugify(gr) for gr in input_groups.split()]

    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать узлы сети", C.ENDC, "\n")

    hosts_dir = BASE_DIR / "backup" / "hosts"

    rules = {
        "hosts": {
            "createMissing": True,
            "updateExisting": False,
        },
        "valueMaps": {"createMissing": True, "updateExisting": False},
        "httptests": {"createMissing": True, "updateExisting": True},
        "graphs": {"createMissing": True, "updateExisting": True},
        "triggers": {"createMissing": True, "updateExisting": True},
        "discoveryRules": {"createMissing": True, "updateExisting": True},
        "items": {"createMissing": True, "updateExisting": True, "deleteMissing": True},
        "applications": {"createMissing": True},
        "templateLinkage": {"createMissing": True},
    }

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        for hosts_file_path in hosts_dir.glob("*.json"):

            if from_groups and hosts_file_path.name[:-5] not in from_groups:
                # Пропускаем ненужные файлы
                continue

            print(f"    -> {hosts_file_path.name}")

            with hosts_file_path.open("r") as file:
                hosts_data = file.read()

            try:
                zbx_import = getattr(zbx.configuration, "import")
                zbx_import(format="json", rules=rules, source=hosts_data)
            except Exception as e:
                print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление узлов сети {STATUS_OK}")


def restore_maps(url, login, password):
    print()
    print(C.OKBLUE, "---> Начинаем восстанавливать карты сети", C.ENDC, "\n")

    maps_file_path = BASE_DIR / "backup" / "maps.json"

    rules = {
        "images": {
            "createMissing": True,
            "updateExisting": True,
        },
        "maps": {"createMissing": True, "updateExisting": True},
    }

    with maps_file_path.open("r") as file:
        maps_data = file.read()

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        try:
            zbx_import = getattr(zbx.configuration, "import")
            zbx_import(format="json", rules=rules, source=maps_data)
        except Exception as e:
            print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление карт сети {STATUS_OK}")


def restore_scripts(url, login, password):
    """
    Восстанавливаем все глобальные скрипты Zabbix
    """

    print()
    print(
        C.OKBLUE,
        "---> Начинаем восстанавливать глобальные скрипты\n",
        C.ENDC,
    )

    scripts_file_path = BASE_DIR / "backup" / "global_scripts.json"

    with scripts_file_path.open("r") as file:
        global_scripts: list = json.load(file)

    new_scripts = 0
    existed_scripts = 0

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)
        for scr in global_scripts:
            try:
                zbx.script.create(**scr)
                new_scripts += 1
            except Exception as e:
                if "already exists" not in str(e):
                    existed_scripts += 1
                    print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    print(f"    Добавлено {new_scripts}")
    print(f"    Уже имелось {existed_scripts}")


def restore_user_groups(url, login, password):
    """
    Восстанавливаем все группы пользователей Zabbix
    """
    print()
    print(
        C.OKBLUE,
        "---> Начинаем восстанавливать группы пользователей\n",
        C.ENDC,
    )

    user_groups_file_path = BASE_DIR / "backup" / "user_groups.json"

    with user_groups_file_path.open("r") as file:
        user_groups: list = json.load(file)

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        # Словарь групп узлов сети -> NAME: ID
        # Для того, чтобы сопоставить Имя текущей группы узлов сети с ID
        # Так как для восстановления требуется указать ID группы
        host_groups = {
            hg["name"]: hg["groupid"] for hg in zbx.hostgroup.get(output="extend")
        }

        for group in user_groups:
            try:
                for i, _ in enumerate(group["rights"]):
                    # Меняем имена разрешенных групп узлов сети на их актуальный ID
                    group["rights"][i]["id"] = host_groups[group["rights"][i]["id"]]
                zbx.usergroup.create(**group)
                print(f"    -> {group['name']}")
            except api.ZabbixAPIException as e:
                if e.error["code"] == -32602:  # Уже есть такая группа пользователей
                    print(f"    -> {group['name']} {C.OKBLUE}exists{C.ENDC}")
            except Exception as e:
                print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")


def restore_media_types(url: str, login: str, password: str):
    """"""

    print()
    print(
        C.OKBLUE,
        "---> Начинаем восстанавливать способы оповещения\n",
        C.ENDC,
    )

    with (BASE_DIR / "backup" / "media_types.json").open("r") as file:
        media_types: list = json.load(file)

    added_media = 0
    updated_media = 0

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        for mtype in media_types:
            try:
                # Добавляем способ оповещения
                zbx.mediatype.create(**mtype)
                added_media += 1

            except api.ZabbixAPIException as e:
                if e.error["code"] == -32602:
                    # Уже есть такой способ оповещения

                    # Ищем имеющийся ID по его имени mtype["name"]
                    mediatypeid = zbx.mediatype.get(
                        output=["mediatypeid"], filter={"name": mtype["name"]}
                    )[0]["mediatypeid"]

                    # Используем его ID для обновления
                    mtype["mediatypeid"] = mediatypeid
                    zbx.mediatype.update(**mtype)
                    updated_media += 1

            except Exception as e:
                print(C.FAIL, e, C.ENDC)

    print(f"    Восстановление {STATUS_OK}")
    if added_media:
        print(f"    {C.OKGREEN}Добавлено{C.ENDC} : {added_media}")
    if updated_media:
        print(f"    {C.OKBLUE}Обновлено{C.ENDC} : {updated_media}")


def generate_password(length: int = 9):
    passwd = ""
    for i in range(length):
        if i and i % 3 == 0:
            passwd += "-"
        passwd += random.choice(ascii_letters + digits)
    return passwd


def restore_users(url: str, login: str, password: str):
    """"""

    print()
    print(
        C.OKBLUE,
        "---> Начинаем восстанавливать пользователей\n",
        C.ENDC,
    )

    with (BASE_DIR / "backup" / "users.json").open("r") as file:
        users: list = json.load(file)

    max_length_of_username = max([len(u["alias"]) for u in users])

    with ZabbixAPI(server=url) as zbx:
        zbx.login(user=login, password=password)

        user_groups = {
            ug["name"]: ug["usrgrpid"] for ug in zbx.usergroup.get(output=["name"])
        }
        media_types = {
            mt["name"]: mt["mediatypeid"] for mt in zbx.mediatype.get(output=["name"])
        }

        # Смотрим отсортированных по username пользователей
        for user in sorted(users, key=lambda u: u["alias"]):
            try:
                user_password = generate_password()
                user["passwd"] = user_password
                # Доступные группы узлов сети
                for usrgrps in user["usrgrps"]:
                    # Меняем прошлый ID на актуальный
                    usrgrps["usrgrpid"] = user_groups[usrgrps["name"]]
                    # И удаляем имя группы
                    del usrgrps["name"]

                # Способы оповещения
                for mt in user["user_medias"]:
                    mt["mediatypeid"] = media_types[mt["mediatypeid"]]

                zbx.user.create(**user)

                print(
                    f"    {user['alias']:{max_length_of_username}} -> passwd: {user_password}"
                )

            except api.ZabbixAPIException as e:
                if e.error["code"] == -32602:  # Уже есть такая группа пользователей
                    print(f"    -> {user['alias']:{max_length_of_username}} {C.OKBLUE}exists{C.ENDC}")

            except Exception as e:
                print(C.FAIL, e, C.ENDC)
