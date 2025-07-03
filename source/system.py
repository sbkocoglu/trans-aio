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
    translation_threads = 4
    selected_llm = "OpenAI"
    ollama_host = "http://localhost:11434"
    ollama_model = ""

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
                elif key == "TRANSLATION_THREADS":
                    translation_threads = int(value.strip())
                elif key == "LLM_PROVIDER":
                    selected_llm = value.strip()
                elif key == "OLLAMA_HOST":
                    ollama_host = value.strip()
                elif key == "OLLAMA_MODEL":
                    ollama_model = value.strip()
    except Exception as e:
        print(f"Failed to load .env: {e}")
        return

    variables.deepl_api = deepl_api
    variables.openAI_api = openai_api
    variables.default_translation = translation_method
    variables.default_revision = revision_method
    variables.translation_threads = translation_threads
    variables.selected_llm = selected_llm
    variables.ollama_host = ollama_host
    variables.ollama_model = ollama_model

def save_env(deepl_api, openai_api, default_translation, default_revision, translation_threads, llm_provider, ollama_host, ollama_model):
    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f'DEEPL_API={base64.b64encode(deepl_api.encode()).decode()}\n')
            f.write(f'OPENAI_API={base64.b64encode(openai_api.encode()).decode()}\n')
            f.write(f'TRANSLATION_METHOD={default_translation}\n')
            f.write(f'REVISION_METHOD={default_revision}\n')
            f.write(f'TRANSLATION_THREADS={translation_threads}\n')
            f.write(f'LLM_PROVIDER={llm_provider}\n')
            f.write(f'OLLAMA_HOST={ollama_host}\n')
            f.write(f'OLLAMA_MODEL={ollama_model}\n')
    except Exception as e:
        print(f"Failed to save .env: {e}")
        return

def check_app_version():
    url = "https://api.github.com/repos/sbkocoglu/trans-aio/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tag = data.get("tag_name", None)
        latest_version = tuple(map(int, tag.lstrip('v').split('.')))
        app_version_str = getattr(variables, "trans_version", None)
        app_version = tuple(map(int, app_version_str.lstrip('v').split('.')))
        if app_version >= latest_version:
            return True, tag
        else:
            return False, tag
    else:
        print(f"Failed to fetch release info: {response.status_code}")
        return None, response.status_code