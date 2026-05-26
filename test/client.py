import re
import sys
import requests

import app_search
import app_detail
import apk_download


def _pick(prompt: str, count: int) -> int:
    while True:
        try:
            choice = input(prompt).strip()
            if choice.lower() == "q":
                sys.exit(0)
            idx = int(choice) - 1
            if 0 <= idx < count:
                return idx
        except ValueError:
            pass
        print(f"  Ingresa un número entre 1 y {count}.")


def _print_apps(items: list[dict]) -> None:
    print()
    for i, app in enumerate(items, 1):
        mod = f"  [{app['mod_info']}]" if app.get("mod_info", "").strip() else ""
        print(f"  {i:>2}. {app['title']}{mod}")
        print(f"       {app['url_id']}  |  {app['rating']}★  |  {app['size']}")
    print()


def _print_mods(mods: list[dict]) -> None:
    print()
    for i, m in enumerate(mods, 1):
        info = re.sub(r"<[^>]+>", " ", m.get("mod_info", "")).strip()
        print(f"  {i:>2}. {m['title']}  ({m['version']})  {m['size']}")
        if info:
            print(f"       {info[:100]}")
    print()


def _download(url: str, filename: str) -> None:
    print(f"\nDescargando: {filename}")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                    print(f"\r  [{bar}] {pct}%  {done//1024//1024}MB", end="", flush=True)
    print(f"\nGuardado: {filename}")


def run() -> None:
    keywords = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Buscar app: ").strip()
    if not keywords:
        sys.exit(0)

    print(f"\nBuscando '{keywords}'...")
    data = app_search.search_apps(keywords)

    if data.get("status") != 1 or not data.get("list"):
        print(f"Sin resultados (status={data.get('status')}).")
        sys.exit(1)

    apps = data["list"]
    _print_apps(apps)
    app = apps[_pick(f"Elige app [1-{len(apps)}] (q=salir): ", len(apps))]

    print(f"\nObteniendo mods de '{app['title']}'...")
    detail = app_detail.get_mod_list(app["url_id"])

    if detail.get("status") != 1 or not detail.get("list"):
        print("No hay mods disponibles.")
        sys.exit(1)

    mods = detail["list"]
    _print_mods(mods)
    mod = mods[_pick(f"Elige mod [1-{len(mods)}] (q=salir): ", len(mods))]

    print(f"\n{'─'*52}")
    print(f"  {mod['title']}  v{mod['version']}")
    print(f"  {mod['url_id']}")
    info = re.sub(r"<[^>]+>", " | ", mod.get("mod_info", "")).strip(" |")
    if info:
        print(f"  MOD: {info[:120]}")
    print(f"  Tamaño: {mod['size']}  |  Rating: {mod['rating']}★")
    print(f"{'─'*52}")

  
    print("\nObteniendo link de descarga...")
    dl = apk_download.get_apk_download(
        url_id=mod["url_id"],
        refer=f"{mod['title']}|1",
    )

    if dl.get("status") != 1:
        print(f"Error del servidor al obtener descarga (status={dl.get('status')}).")
        sys.exit(1)

    apk_url = dl.get("static_path", "")
    if not apk_url:
        print("No se recibió URL de descarga.")
        sys.exit(1)

    filename = mod["url_id"].replace("/", "_") + ".apk"
    _download(apk_url, filename)


if __name__ == "__main__":
    run()
