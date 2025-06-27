import os, base64, variables, requests

def decode_value(value):
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return ""

def load_env():
    if not os.path.exists(".env"):
        return

    deepl_api = ""
    openai_api = ""
    translation_method = "MT"
    revision_method = "MT"

    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                if key == "DEEPL_API":
                    deepl_api = decode_value(value)
                elif key == "OPENAI_API":
                    openai_api = decode_value(value)
                elif key == "TRANSLATION_METHOD":
                    translation_method = value.strip()
                elif key == "REVISION_METHOD":
                    revision_method = value.strip()
    except Exception as e:
        print(f"Failed to load .env: {e}")
        return

    variables.deepl_api = deepl_api
    variables.openAI_api = openai_api
    variables.default_translation = translation_method
    variables.default_revision = revision_method

def save_env(deepl_api, openai_api, default_translation, default_revision):
    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f'DEEPL_API={base64.b64encode(deepl_api.encode()).decode()}\n')
            f.write(f'OPENAI_API={base64.b64encode(openai_api.encode()).decode()}\n')
            f.write(f'TRANSLATION_METHOD={default_translation}\n')
            f.write(f'REVISION_METHOD={default_revision}\n')
    except Exception as e:
        print(f"Failed to save .env: {e}")
        return

def check_app_version():
    url = f"https://api.github.com/repos/sbkocoglu/trans-aio/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        latest_version = tuple(map(int, data.get("tag_name", None).lstrip('v').split('.')))
        app_version = tuple(map(int, data.get(variables.trans_version, None).lstrip('v').split('.')))
        if app_version >= latest_version:
            return True, None
        else:
            return False, data.get("tag_name", None)
    else:
        print(f"Failed to fetch release info: {response.status_code}")
        return None, {response.status_code}