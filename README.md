# ApkOmega / HappyMod API — Reverse Engineering Documentation

La documentacion la obtuve realizando ingenieria inversa al apk de HappyMod

---

## Tabla de contenidos

1. [Generacion del UID](#1-generacion-del-uid)
2. [Generacion del Stamp](#2-generacion-del-stamp)
3. [Decodificacion de la respuesta](#3-decodificacion-de-la-respuesta)
4. [Una implementacion mia en Python](#4-implementacion-completa-en-python)
5. [Endpoints basicos de la app](#5-endpoints-documentados-de-la-aplicacion)
  
   - 5.1 [Sincronizacion de tiempo del servidor](#51-sincronizacion-de-tiempo-del-servidor)
   - 5.2 [Busqueda de aplicaciones](#52-busqueda-de-aplicaciones)
   - 5.3 [Generacion del Hash de descarga](#53-generacion-del-hash-de-descarga)
   - 5.4 [Descarga del APK](#54-descarga-de-apk)
   - 5.5 [Detalle de aplicacion](#55-detalle-de-aplicacion)

---

## 1. Generacion del UID

### Algoritmo

```
uid = MD5( prefijo + identificador )
```

#### Prefijo (siempre igual para el mismo dispositivo)

```python
prefijo = "35"
prefijo += str(len(Build.BOARD)        % 10)
prefijo += str(len(Build.BRAND)        % 10)
prefijo += str(len(Build.DEVICE)       % 10)
prefijo += str(len(Build.DISPLAY)      % 10)
prefijo += str(len(Build.HOST)         % 10)
prefijo += str(len(Build.ID)           % 10)
prefijo += str(len(Build.MANUFACTURER) % 10)
prefijo += str(len(Build.MODEL)        % 10)
prefijo += str(len(Build.PRODUCT)      % 10)
prefijo += str(len(Build.TAGS)         % 10)
prefijo += str(len(Build.TYPE)         % 10)
prefijo += str(len(Build.USER)         % 10)
```

#### Identificador (por orden de prioridad)

```
1. Google Advertising ID (GAID) -- preferido en dispositivos modernos
        si GAID es null o contiene "00000000" -- siguiente
2. Build.SERIAL + ANDROID_ID -- Android < 8.0 (SDK < 26)
        si vacio > siguiente
3. UUID aleatorio persistido en:
        Android >= 13  → SharedPreferences
        Android 6-12   → Downloads/HappyMod/device_id.txt (si hay permisos)
                         o sharedPreferences si no hay permisos
        Android >= 10  → MediaStore (device_id.png en Downloads/HappyMod/)
```

#### Implementacion Python

```python
import hashlib

def generate_uid(board, brand, device, display, host,
                 build_id, manufacturer, model, product,
                 tags, type_, user, identifier: str) -> str:
    prefix = "35"
    for field in [board, brand, device, display, host,
                  build_id, manufacturer, model, product,
                  tags, type_, user]:
        prefix += str(len(field) % 10)
    return hashlib.md5((prefix + identifier).encode()).hexdigest()
```

---

## 2. Generacion del Stamp

### El `time_str`

```java
// C0060b.m256b()
time_str = (System.currentTimeMillis() / 1000) - offset_servidor
```

El `offset_servidor` es la diferencia entre el reloj local y el timestamp
devuelto por `server_time.php`, entonces, `time_str` es el
timestamp unix actual en segundos sincronizado con el servidor

### Logica nativa (`libCSTAMP.so`)

Funcion:
`Java_com_happymod_apk_utils_NativeHelper_getStamp`:

```c
// argumentos: a3 = time_str,  a4 = uid
v11 = Jstring2CStr(a1, a4);   // uid
v10 = Jstring2CStr(a1, a3);   // time_str

ptr = malloc(len(v11) + len(v10) + len(KEY) + 1);
strcpy(ptr, v11);              // uid
strcat(ptr, v10);              // + time_str
strcat(ptr, KEY);              // + "this_is_happymod"

MD5Init();
MD5Update(ctx, ptr, len(ptr));
MD5Final(digest, ctx);

// formatea los 16 bytes como hex lowercase
for i in 0..15:
    sprintf(result, "%s%02x", result, digest[i])

return result;
```

key extraida del segmento `.rodata` de `libCSTAMP.so` en offset `0x989`:
```
"this_is_happymod"
```

### Quedaria asi

```
stamp = MD5( uid + time_str + "this_is_happymod" )
```

#### Aca entonces en Python

```python
import hashlib, time, requests

def get_server_offset(uid: str) -> int:
    r = requests.post(
        "https://app.apkomega.com/202010/api/server_time.php",
        data={"version": "3.2.6", "uid": uid, "country": "CO"}
    )
    body = decode_response(r.text)
    data = json.loads(body)
    if data.get("status") == 1:
        return int(time.time()) - data["timestamp"]
    return 0

def get_stamp(uid: str, offset: int = 0) -> str:
    time_str = str(int(time.time()) - offset)
    key      = "this_is_happymod"
    raw      = uid + time_str + key
    return hashlib.md5(raw.encode()).hexdigest()
```

---

## 3. Decodificacion de la respuesta

La respuesta http no es json directo, pasa por tres capas en orden:

```
respuesta http raw
        |
        v
[1] sustitucion posicional (vigenere numerico inverso)
        |
        v
[2] base64 decode  (alphabet estandar A-Za-z0-9+/)
        |
        v
[3] gzip decompress  (si magic bytes == 0x1f 0x8b)
        |
        v
json valido
```

### 1 — Sustitucion posicional 

Para cada caracter en posicion `i`:
- Si es alfanumerico `[0-9 A-Z a-z]`:
  - `shifted = ASCII(char) - (i % 10)`
  - Wrapping entre los tres rangos `[48-57]`, `[65-90]`, `[97-122]`

```python
def vigenere_decode(raw: str) -> str:
    result = []
    for i, ch in enumerate(raw):
        code = ord(ch)
        if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
            shifted = code - (i % 10)
            if shifted < 48:
                code = 122 - (48 - shifted) + 1
            elif code < 65 or shifted >= 65:
                if code < 97 or shifted >= 97:
                    code = shifted
                else:
                    code = (90 - (97 - shifted)) + 1
            else:
                code = (57 - (65 - shifted)) + 1
        result.append(chr(code))
    return ''.join(result)
```

### 2 — Base64 decode

Alphabet estandar (`f20716a` / `f20717b`, flags=0):
```
A-Z a-z 0-9 + /
```

```python
import base64
def b64_decode(s: str) -> bytes:
    return base64.b64decode(s + '==')  # padding por si falta
```

### 3 — Gzip decompress (`m22190e`)

El metodo detecta automaticamente el magic header `0x1f 0x8b`:

```python
import gzip
def maybe_gunzip(data: bytes) -> bytes:
    if data[:2] == b'\x1f\x8b':
        return gzip.decompress(data)
    return data
```

### Funcion completa

```python
def decode_response(raw: str) -> str:
    step1 = vigenere_decode(raw)
    step2 = b64_decode(step1)
    step3 = maybe_gunzip(step2)
    return step3.decode('utf-8')
```

---

## 4. Mi implementacion en Python

```python
import hashlib, base64, gzip, time, json
import requests

# los datos que requiere el endpoint

UID     = "68920e5674b1d3ec969e4637d31e0345"  
VERSION = "3.2.6"
LANG    = "es"
BASE    = "https://app.apkomega.com"

# decodificamos
def vigenere_decode(raw: str) -> str:
    result = []
    for i, ch in enumerate(raw):
        code = ord(ch)
        if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
            shifted = code - (i % 10)
            if shifted < 48:
                code = 122 - (48 - shifted) + 1
            elif code < 65 or shifted >= 65:
                code = shifted if (code >= 97 and shifted >= 97) else (90 - (97 - shifted)) + 1
            else:
                code = (57 - (65 - shifted)) + 1
        result.append(chr(code))
    return ''.join(result)

def decode_response(raw: str) -> str:
    step1 = vigenere_decode(raw)
    step2 = base64.b64decode(step1 + '==')
    if step2[:2] == b'\x1f\x8b':
        step2 = gzip.decompress(step2)
    return step2.decode('utf-8')

# stamp

def get_server_offset(uid: str) -> int:
    try:
        r = requests.post(
            BASE + "/202010/api/server_time.php",
            data={"version": VERSION, "uid": uid, "country": "CO"}
        )
        data = json.loads(decode_response(r.text))
        if data.get("status") == 1:
            return int(time.time()) - data["timestamp"]
    except Exception as e:
        print("Error obteniendo server time:", e)
    return 0

def get_stamp(uid: str, offset: int = 0) -> str:
    time_str = str(int(time.time()) - offset)
    return hashlib.md5((uid + time_str + "this_is_happymod").encode()).hexdigest()

# busqueda

def search(keyword: str, page: int = 1, is_new_user: bool = True) -> dict:
    offset = get_server_offset(UID)
    stamp  = get_stamp(UID, offset)

    payload = {
        "version":     VERSION,
        "uid":         UID,
        "stamp":       stamp,
        "page":        str(page),
        "keywords":    keyword,
        "lang":        LANG,
        "is_new_user": "1" if is_new_user else "2",
        "is_input":    "2",
        "input_word":  keyword[:3],
    }

    r = requests.post(BASE + "/202010/api/search_list.php", data=payload)
    return json.loads(decode_response(r.text))

# ejemplo

if __name__ == "__main__":
    result = search("whatsapp")
    for app in result.get("list", []):
        print(app.get("title"), "-", app.get("url_id"))
```

---

## 5. Endpoints documentados de la aplicacion

Todos los endpoints que usan `stamp` requieren que este sea generado en el momento
de la solicitud, la respuesta de todos los endpoints de `apkomega.com`
usa el mismo esquema de cifrado descrito en la seccion 4

---

### 5.1 Sincronizacion de tiempo del servidor

**URL:**
```
POST https://app.apkomega.com/202010/api/server_time.php
```

**Payload:**

| Campo     | Descripcion          | Ejemplo |
|-----------|----------------------|---------|
| `version` | Version del APK      | `3.2.6` |
| `uid`     | UID del dispositivo  | `68920e5674b1d3ec969e4637d31e0345` |
| `country` | Codigo de pais ISO   | `CO`    |

**Respuesta decodificada**

```json
{
  "status": 1,
  "timestamp": 1716000000
}
```

| Campo       | Descripcion                                      |
|-------------|--------------------------------------------------|
| `status`    | `1` = exito, `-20` = error de fecha              |
| `timestamp` | Timestamp Unix actual del servidor (segundos)    |

El cliente calcula `offset = tiempo_local - timestamp_servidor` y lo resta
a cada `time_str` para sincronizar el stamp con el servidor

Ojo: El resultado se cachea en memoria (`_server_time_offset`) para no repetir
la llamada en cada stamp

---

### 5.2 Busqueda de aplicaciones

**URL:**
```
POST https://app.apkomega.com/202010/api/search_list.php
```

**Payload:**

| Campo        | Tipo  | Descripcion                                           | Ejemplo     |
|--------------|-------|-------------------------------------------------------|-------------|
| `version`    | str   | Version del APK                                       | `3.2.6`     |
| `uid`        | str   | UID del dispositivo                                   | `68920e...` |
| `stamp`      | str   | Token MD5 (ver seccion 3)                             | `aded81...` |
| `page`       | int   | Numero de pagina (empieza en 1)                       | `1`         |
| `keywords`   | str   | Termino de busqueda                                   | `whatsapp`  |
| `lang`       | str   | Idioma ISO 639-1                                      | `es`        |
| `is_new_user`| int   | `1` si el APK se instalo hoy, `2` si no               | `1`         |
| `is_input`   | int   | `2` si el usuario escribio el termino, `1` si no      | `2`         |
| `input_word` | str   | Primeros 3 chars escritos antes de buscar             | `wha`       |

**Respuesta decodificada:**

```json
{
  "status": 1,
  "has_next_page": 1,
  "list": [
    {
      "mod_info":          "Mod descripcion",
      "title":             "WhatsApp",
      "icon":              "https://...",
      "url_id":            "com.whatsapp",
      "star":              "4.5",
      "size":              "50M",
      "author":            "WhatsApp Inc.",
      "update_flag_image": "",
      "has_faq":           "0",
      "is_ad":             0,
      "data_type":         0
    }
  ]
}
```

| Campo            | Descripcion                                              |
|------------------|----------------------------------------------------------|
| `status`         | `1` = hay resultados, `-20` = error de sesion            |
| `has_next_page`  | `1` si hay mas paginas disponibles                       |
| `url_id`         | Package name del APK — se usa en otras llamadas          |
| `data_type`      | `1` = tiene lista de mods, `0` = APK simple              |
| `is_ad`          | `1` = es un resultado patrocinado                        |
| `update_flag_image` | URL de imagen de badge (ej. "Updated"), vacio si no   |

---

### 5.3 Generacion del hash de descarga

El `hash` es un hash es un token de autorizacion derivado
del package name del mod, construido cortando y reordenando 4 fragmentos de 4
caracteres del md5

**Codigo java original:**

```java
String strM23357b = C8854j.m23357b(this.f2163b + "android_require_apk");
String str27 = strM23357b.substring(10, 14)
             + strM23357b.substring(25, 29)
             + strM23357b.substring(18, 22)
             + strM23357b.substring(5,  9);
```

Donde `this.f2163b` es el `url_id` del mod y `C8854j.m23357b()` es md5

**Entonces:**

```
full_md5 = MD5( url_id + "android_require_apk" )
hash     = full_md5[10:14] + full_md5[25:29] + full_md5[18:22] + full_md5[5:9]
```

**Ya en python:**

```python
import hashlib

def generate_hash(url_id: str) -> str:
    full_md5 = hashlib.md5((url_id + "android_require_apk").encode()).hexdigest()
    return full_md5[10:14] + full_md5[25:29] + full_md5[18:22] + full_md5[5:9]
```

**Verificacion:**

```
url_id  = "com.mod.tiktok-videos-shop-livemod-apk-43-9-16"
full_md5 = MD5("com.mod.tiktok-videos-shop-livemod-apk-43-9-16android_require_apk")
         = "...2496...81fc...2664...746c..."   (posiciones 5,10,18,25)
hash    = "24962664746c81fc"  16 chars hex
```

---

### 5.4 Descarga de APK

**URL:**
```
POST https://d.apkomega.com/202101/api/get_apk_download_v2.php
```

Usa subdominio `d.` (en lugar de `app.`) y ruta `202101` (en lugar de `202010`).

**Payload:**

| Campo      | Tipo  | Descripcion                                        | Ejemplo / Valor fijo         |
|------------|-------|----------------------------------------------------|------------------------------|
| `version`  | str   | Version del APK                                    | `3.2.6`                      |
| `uid`      | str   | UID del dispositivo                                | `68920e...`                  |
| `stamp`    | str   | Token MD5 (ver seccion 3)                          | generado en el momento       |
| `country`  | str   | Codigo de pais ISO                                 | `US`                         |
| `lang`     | str   | Idioma ISO 639-1                                   | `es`                         |
| `hash`     | str   | Token de autorizacion de 16 chars (ver seccion 6.3)| `24962664746c81fc`           |
| `url_id`   | str   | Package name del mod (no de la app base)           | `com.mod.tiktok-...`         |
| `refer`    | str   | Titulo del mod concatenado con `\|1`               | `TikTok Mod 43.9.16\|1`      |
| `aid`      | str   | ID fijo extraido de `libCSTAMP.so` offset `0x940`  | `98pyooirb6mad326`           |
| `get_hpt`  | int   | Flag desconocido, siempre `0`                      | `0`                          |
| `channel`  | str   | Canal de distribucion                              | `happymod`                   |
| `username` | str   | Usuario logueado, vacio si no hay sesion           | `""`                         |

**Sobre `aid`:** Es el string `STRAID` extraido del segmento `.rodata` de
`libCSTAMP.so`, generado por `NativeHelper.getAid()`

**Sobre `url_id`:** Debe ser el `url_id` del mod especifico (Ejemplo:
`com.mod.tiktok-videos-shop-livemod-apk-43-9-16`), no el package name de la app
base (`com.zhiliaoapp.musically`), el servidor devuelve `status: -10` si se usa
el package base

**Respuesta decodificada:**

```json
{
  "status":      1,
  "url_id":      "com.mod.tiktok-videos-shop-livemod-apk-43-9-16",
  "apk_path":    "http://s4-hot-2-c.happymodio.com/downloadfile/mod/<stamp>/<path_encoded>=",
  "static_path": "http://s4-hot-2-c.happymodio.com/download_file/mod/<md5>.swf",
  "stamp":       "bbddd820f5af2ebbd76c9d822e9a02cf",
  "path":        "<base64_encoded_path>=",
  "cache_time":  59,
  "full_size":   "481246481",
  "what_level":  "lv5",
  "verify":      "f1b5c559cc1acfe67f6a37dac0ffba7a",
  "no_cdn":      0,
  "is_boundle":  0,
  "is_force":    0,
  "is_vip":      0,
  "vip_award_time": 0
}
```

| Campo         | Descripcion                                                        |
|---------------|--------------------------------------------------------------------|
| `status`      | `1` = exito, `-10` = hash invalido o url_id incorrecto             |
| `apk_path`    | URL de descarga con path codificado internamente — no usar directamente |
| `static_path` | **URL directa de descarga del APK** — esta es la que se usa        |
| `stamp`       | MD5 del servidor para validar la descarga                          |
| `full_size`   | Tamano del APK en bytes                                            |
| `what_level`  | Nivel de CDN asignado (`lv5` = CDN caliente)                       |
| `verify`      | MD5 del archivo APK para verificar integridad post-descarga        |
| `is_vip`      | `1` si el mod requiere cuenta VIP                                  |

---

### 5.5 Detalle de aplicacion

**URL:**
```
GET https://app.happymodapp.com/clist/{version},{lang},{country},{page},{url_id},{sort},{page},{template}
```

Usa un dominio diferente (`happymodapp.com`) y no requiere `uid` ni `stamp`.
La respuesta tampoco usa el esquema de cifrado de las otras apis

**Parametros de ruta:**

| Parametro  | Descripcion                              | Ejemplo / Default              |
|------------|------------------------------------------|--------------------------------|
| `version`  | Version del APK                          | `3.2.6`                        |
| `lang`     | Idioma ISO 639-1                         | `es`                           |
| `country`  | Codigo de pais ISO                       | `US`                           |
| `page`     | Numero de pagina (aparece dos veces)     | `1`                            |
| `url_id`   | Package name de la app                   | `com.whatsapp`                 |
| `sort`     | Criterio de ordenamiento de mods         | `rating`                       |
| `template` | Template HTML del servidor               | `pdt_mod_list_v3.html`         |

**Ejemplo de url construida:**
```
GET https://app.happymodapp.com/clist/3.2.6,es,US,1,com.whatsapp,rating,1,pdt_mod_list_v3.html
```

**Respuesta:** html o json crudo, no cifrado, me dio pereza documentarlo y ya

---

## 6. Analice:

| Clase Java (nombres de jadx)       | Nombre original          | Funcion                                        |
|-------------------------|--------------------------|---------------------------------------------|
| `p410y5.C9106c`         | `SearchManager.java`     | Construye y ejecuta la peticion de busqueda |
| `p007a5.C0060b`         | `TimestampManager.java`  | Genera `time_str` sincronizado al servidor  |
| `p376v6.C8861q`         | `Util.java`              | Utilidades: uid, version, stamp, pais       |
| `p212h7.C7774c`         | `DeviceIdUtil.java`      | Genera el uid del dispositivo               |
| `p320q7.C8474a`         | `HappyKobe24.java`       | Decodificacion capa 1 (Vigenere)            |
| `p320q7.C8475b`         | `MyKobe.java`            | Decodificacion capa 2/3 (Base64 + GZIP)    |
| `p309p7.C8416q`         | `IcOld.java`             | Constantes de endpoints de la API           |
| `libCSTAMP.so`          | Nativa (C/C++)           | Genera el stamp con MD5                     |

### Strings clave extraidas de `libCSTAMP.so`

| Offset  | Valor                | Uso                          |
|---------|----------------------|------------------------------|
| `0x989` | `this_is_happymod`   | Salt del stamp (KEY)         |
| `0x940` | `98pyooirb6mad326`   | STRAID — usado en `getAid()` |

---

> La documentacion la hice apoyandome de JADX e IDA pro, la app no esta tan ofuscada asi que fue facil reversear todo
> Lo hice con fines educativos y de investigacion
