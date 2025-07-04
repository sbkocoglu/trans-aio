import pandas as pd
import os

trans_version = "v1.0.1"
trans_icon = "img/icon.png"

trans_info = {
    "file_name" : None,
    "file_path" : None,
    "save_path" : None,
    "source_language" : None,
    "target_language" : None,
    "mqxliff_df" : None,
    "tm_path" : None,
    "tm_df" : pd.DataFrame(columns=['Source', 'Target']),
    "tb_path" : None,
    "tb_df" : pd.DataFrame(),
    "segments_translated" : 0,
    "tm_match" : 0,
    "tm_match_partial" : 0,
    "segments_skipped" : 0,
    "translation_failed" : 0,
    "token_count" : 0,
    "total_steps" : 3,
    "current_step" : 0,
    }

trans_save = None
deepl_api = ""
translation_threads = 4
default_translation = "MT"
default_revision = "MT"
openAI_api = ""
openAI_model = "gpt-4.1-mini"
selected_llm = "OpenAI"
ollama_host = "http://localhost:11434"
ollama_model = ""

language_locale = {
    "ko_kr": "Korean",
    "ko": "Korean",
    "zh_cn": "Chinese",
    "ja_jp": "Japanese",
    "jp": "Japanese",
    "en": "English",
    "en_gb": "English (United Kingdom)",
    "en_us": "English (United States)",
    "tr": "Turkish",
    "de": "German",
    "de_de": "German (Germany)",
    "fr": "French",
    "fr_fr": "French (France)",
    "es": "Spanish",
    "es_es": "Spanish (Spain)",
    "pt": "Portuguese",
    "pt_br": "Portuguese (Brazil)",
    "it": "Italian",
    "it_it": "Italian",
    "ru": "Russian",
    "ru_ru": "Russian",
    "ar": "Arabic",
    "ar_sa": "Arabic",
    "hi": "Hindi",
    "hi_in": "Hindi (India)",
    "bn": "Bengali",
    "bn_bd": "Bengali (Bangladesh)",
    "ur": "Urdu",
    "ur_pk": "Urdu (Pakistan)",
    "fa": "Persian",
    "fa_ir": "Persian (Iran)",
    "vi": "Vietnamese",
    "vi_vn": "Vietnamese",
    "th": "Thai",
    "th_th": "Thai",
    "ms": "Malay",
    "ms_my": "Malay",
    "tl": "Tagalog",
    "tl_ph": "Tagalog",
    "id": "Indonesian",
    "id_id": "Indonesian",
    "nl": "Dutch",
    "nl_nl": "Dutch",
    "sv": "Swedish",
    "sv_se": "Swedish",
    "fi": "Finnish",
    "fi_fi": "Finnish",
    "da": "Danish",
    "da_dk": "Danish",
    "no": "Norwegian",
    "no_no": "Norwegian",
    "pl": "Polish",
    "pl_pl": "Polish",
    "cs": "Czech",
    "cs_cz": "Czech",
    "sk": "Slovak",
    "sk_sk": "Slovak",
    "hu": "Hungarian",
    "hu_hu": "Hungarian",
    "ro": "Romanian",
    "ro_ro": "Romanian",
    "el": "Greek",
    "el_gr": "Greek",
    "uk": "Ukrainian",
    "uk_ua": "Ukrainian",
    "he": "Hebrew",
    "he_il": "Hebrew",
    "af": "Afrikaans",
    "af_za": "Afrikaans",
    "sw": "Swahili",
    "sw_ke": "Swahili",
    "am": "Amharic",
    "am_et": "Amharic",
    "sq": "Albanian",
    "sq_al": "Albanian",
    "hy": "Armenian",
    "hy_am": "Armenian",
    "az": "Azerbaijani",
    "az_az": "Azerbaijani",
    "eu": "Basque",
    "eu_es": "Basque",
    "be": "Belarusian",
    "be_by": "Belarusian",
    "bs": "Bosnian",
    "bs_ba": "Bosnian",
    "bg": "Bulgarian",
    "bg_bg": "Bulgarian",
    "ca": "Catalan",
    "ca_es": "Catalan (Spain)",
    "hr": "Croatian",
    "hr_hr": "Croatian",
    "cy": "Welsh",
    "cy_gb": "Welsh",
    "eo": "Esperanto",
    "et": "Estonian",
    "et_ee": "Estonian",
    "gl": "Galician",
    "gl_es": "Galician",
    "ka": "Georgian",
    "ka_ge": "Georgian",
    "gu": "Gujarati",
    "gu_in": "Gujarati (India)",
    "ht": "Haitian Creole",
    "ha": "Hausa",
    "ha_ng": "Hausa (Nigeria)",
    "haw": "Hawaiian",
    "haw_us": "Hawaiian (United States)",
    "iw": "Hebrew",
    "hi_in": "Hindi (India)",
    "hmn": "Hmong",
    "hu_hu": "Hungarian",
    "is": "Icelandic",
    "is_is": "Icelandic",
    "ig": "Igbo",
    "ig_ng": "Igbo",
    "id_id": "Indonesian",
    "ga": "Irish",
    "ga_ie": "Irish",
    "it_it": "Italian",
    "ja_jp": "Japanese",
    "jw": "Javanese",
    "kn": "Kannada",
    "kn_in": "Kannada (India)",
    "kk": "Kazakh",
    "kk_kz": "Kazakh (Kazakhstan)",
    "km": "Khmer",
    "km_kh": "Khmer (Cambodia)",
    "ko_kr": "Korean",
    "ku": "Kurdish",
    "ky": "Kyrgyz",
    "ky_kg": "Kyrgyz (Kyrgyzstan)",
    "lo": "Lao",
    "lo_la": "Lao (Laos)",
    "la": "Latin",
    "lv": "Latvian",
    "lv_lv": "Latvian (Latvia)",
    "lt": "Lithuanian",
    "lt_lt": "Lithuanian (Lithuania)",
    "lb": "Luxembourgish",
    "lb_lu": "Luxembourgish (Luxembourg)",
    "mk": "Macedonian",
    "mk_mk": "Macedonian (Macedonia)",
    "mg": "Malagasy",
    "ms_my": "Malay",
    "ml": "Malayalam",
    "ml_in": "Malayalam (India)",
    "mt": "Maltese",
    "mt_mt": "Maltese",
    "mi": "Maori",
    "mr": "Marathi",
    "mr_in": "Marathi (India)",
    "mn": "Mongolian",
    "mn_mn": "Mongolian",
    "my": "Burmese",
    "my_mm": "Burmese (Myanmar)",
    "ne": "Nepali",
    "ne_np": "Nepali",
    "ny": "Chichewa",
    "ny_mw": "Chichewa",
    "or": "Odia",
    "or_in": "Odia (India)",
    "ps": "Pashto",
    "ps_af": "Pashto (Afghanistan)",
    "fa_ir": "Persian (Iran)",
    "pl_pl": "Polish",
    "pt_pt": "Portuguese",
    "pa": "Punjabi",
    "pa_in": "Punjabi (India)",
    "ro_ro": "Romanian",
    "ru_ru": "Russian",
    "sm": "Samoan",
    "gd": "Scots Gaelic",
    "sr": "Serbian",
    "st": "Sesotho",
    "sn": "Shona",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk_sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es_es": "Spanish (Spain)",
    "su": "Sundanese",
    "sw_ke": "Swahili (Kenya)",
    "sv_se": "Swedish",
    "tl_ph": "Tagalog",
    "tg": "Tajik",
    "tg_tj": "Tajik",
    "ta": "Tamil",
    "ta_in": "Tamil (India)",
    "tt": "Tatar",
    "te": "Telugu",
    "te_in": "Telugu (India)",
    "th_th": "Thai",
    "tr" : "Turkish",
    "tr_tr": "Turkish",
    "tk": "Turkmen",
    "uk_ua": "Ukrainian",
    "ur_pk": "Urdu (Pakistan)",
    "ug": "Uyghur",
    "ug_cn": "Uyghur (China)",
    "uz": "Uzbek",
    "uz_uz": "Uzbek",
    "vi_vn": "Vietnamese",
    "cy_gb": "Welsh (United Kingdom)",
    "fy": "Western Frisian",
    "fy_nl": "Western Frisian (Netherlands)",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "zu": "Zulu",
}