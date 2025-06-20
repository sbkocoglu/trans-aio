import deepl, re, variables
from segment import create_tag_dict, restore_tags

def deepl_translate(row, translation_memory=None):
    """Translates the segment using DeepL.
    Returns translated string and translation log.
    """
    segment_source_text = row['Source']
    
    if translation_memory:
        segment_context = translation_memory 
    else: 
        segment_context = row['Context']
    
    source_text, source_tags_dict = create_tag_dict(segment_source_text)
    
    source_language = re.sub(r'_', '-', variables.trans_info["source_language"])
    target_language = re.sub(r'_', '-', variables.trans_info["target_language"])
    
    source_language = lang_code_fix(source_language)
    target_language = lang_code_fix(target_language)
    
    translator = deepl.Translator(variables.deepl_api)
    
    result = translator.translate_text(text=source_text, 
                                       source_lang=source_language.upper(),
                                       target_lang=target_language.upper(), 
                                       context=segment_context, 
                                       tag_handling='xml',
                                       )
    deepl_translation = result.text
    deepl_translation = restore_tags(deepl_translation, source_tags_dict)   
    
    if translation_memory:
        translation_log = f'Source:\n{source_text}\nTM:{translation_memory}\nTranslation improved by DeepL\nTranslation:'
    else:
        translation_log = f'Source:\n{source_text}\nTranslated by DeepL\nTranslation:'

    return deepl_translation, translation_log

def lang_code_fix(lang_code):
    if lang_code == 'EN' or lang_code == 'en':
        lang_code = 'EN-US'
    return lang_code