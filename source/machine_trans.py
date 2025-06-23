import deepl, re, time, variables
from segment import create_tag_dict, restore_tags
from deepl import DeepLException, TooManyRequestsException, AuthorizationException

def deepl_translate(row, translation_memory=None, max_retries=5):
    """Translates the segment using DeepL.
    Returns translated string and translation log.
    Handles retry logic for high server load and other errors.
    """
    segment_source_text = row['Source']

    if translation_memory:
        segment_context = translation_memory
    else:
        segment_context = row['Context']

    source_text, source_tags_dict = create_tag_dict(segment_source_text)

    source_language = re.sub(r'_', '-', variables.trans_info["source_language"])
    target_language = re.sub(r'_', '-', variables.trans_info["target_language"])
    source_language = lang_code_fix(True, source_language)
    target_language = lang_code_fix(False, target_language)
    source_language = source_language.upper()
    target_language = target_language.upper()

    translator = deepl.Translator(variables.deepl_api)

    retry_delay = 1  # Start with 1 second
    for attempt in range(max_retries):
        try:
            result = translator.translate_text(
                text=source_text,
                source_lang=source_language,
                target_lang=target_language,
                context=segment_context,
                tag_handling='xml',
            )
            deepl_translation = restore_tags(result.text, source_tags_dict)
            break  # Success, exit retry loop
        except TooManyRequestsException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                return "", f"Translation failed: DeepL server is overloaded after {max_retries} retries."
        except AuthorizationException:
            return "", "Translation failed: Invalid DeepL API key."
        except DeepLException as e:
            return "", f"Translation failed: {str(e)}"
        except Exception as e:
            return "", f"Unexpected error during translation: {str(e)}"

    if translation_memory:
        translation_log = f"Source:\n{source_text}\nTM:{translation_memory}\nTranslation improved by DeepL\nTranslation:\n{deepl_translation}"
    else:
        translation_log = f"Source:\n{source_text}\nTranslated by DeepL\nTranslation:\n{deepl_translation}"

    return deepl_translation, translation_log


def lang_code_fix(is_source, lang_code):
    if not is_source and lang_code.upper() == "EN":
        return "EN-US"
    if is_source and (lang_code.upper() == "EN-US" or lang_code.upper() == "EN-GB"):
        return "EN"
    return lang_code
