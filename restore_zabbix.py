import pathlib
import json
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
    "C"
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
    print(f"    {C.OKGREEN}Было добавлено узлов сети{C.ENDC}: {added_host_groups}")
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
        "    которые надо восстановить.\n"
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
