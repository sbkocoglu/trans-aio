import pandas as pd

trans_version = 0.01

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
    "token_count" : 0,
    "total_steps" : 4,
    "current_step" : 0,
    }

trans_save = None
deepl_api = None