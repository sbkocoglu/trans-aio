from openai import OpenAI
import time, variables
from segment import (restore_tags, find_tag_discrepancies, remove_discrepant_tags, create_tag_dict, 
                         is_numbered_list, is_bracketed_number, check_for_tags, check_termbase)

def chatGPT_translate(row):   
    segment_from_row = row["Source"]
    segment_context = row["Context"]
    
    source_text, source_tags_dict = create_tag_dict(segment_from_row)
    
    if variables.trans_info["source_language"] in variables.language_locale.keys():
        source_language_name = variables.language_locale[variables.trans_info["source_language"]]
    else:
        source_language_name = variables.trans_info["source_language"]
        
    if variables.trans_info["target_language"] in variables.language_locale.keys():
        target_language_name = variables.language_locale[variables.trans_info["target_language"]]
    else:
        target_language_name = variables.trans_info["target_language"]
        
    client = OpenAI(
    api_key=variables.openAI_api,
    timeout=30,
    )
    max_retries = 1
    retry_count = 0
    retry_delay = 3
    
    if not source_text:
        return ""
    
    prompt = f"Translate the following text from {source_language_name} to {target_language_name}. You MUST provide a translation."
    
    if is_numbered_list(source_text):
        prompt += "\nSource text starts with a numbered list, your translation must start with the same numbered list."
        
    if is_bracketed_number(source_text):
        prompt += "\nSource text contains numbers in brackets, your translation must include the same numbers in same brackets in correct positions."
        
    relevant_glossary = {}
    
    if variables.trans_info["tb_df"] is not None:
        relevant_glossary = check_termbase(source_text)     
            
                    
    if len(relevant_glossary) > 0:
        prompt += "Strictly use this termbase:\n"
        for index, info in relevant_glossary.items():
            source = info["Source"]
            target = info["Target"]
            prompt += f"- {source} = {target}.\n"    
           
        
    prompt += "\nRespond after 'Translation:' with nothing but your translation."
    prompt += "\nText:"
    prompt += f"\n{source_text}"
    if segment_context != "N/A":
        prompt += f"\nAdditional info about text: \n{segment_context}"
    prompt += "\nTranslation:"  
    
    
    while retry_count < max_retries:        
        try: 
            response = client.chat.completions.create(
                model=variables.openAI_model,
                messages=[
                    {"role": "system", "content": "You are a localization & translation expert."},
                    {"role": "user", "content": prompt},
                ],
            )
            gpt_translation = response.choices[0].message.content
            corrected_gpt_translation = correction(gpt_translation, source_text)
            variables.trans_info["token_count"] += response.usage.total_tokens
            
            if len(source_tags_dict) >= 1:
                if check_for_tags(corrected_gpt_translation, source_tags_dict):
                    corrected_gpt_translation = restore_tags(corrected_gpt_translation, source_tags_dict)
                    
            retry_reason = should_retry(source_text, corrected_gpt_translation)

            if retry_reason:
                retry_count += 1
                time.sleep(retry_delay)
            else:
                return corrected_gpt_translation, prompt, False, ""             
       
        except Exception as e:
            error_message = f"An error occurred: {e}. Retrying after a delay."
            print(client.api_key)
            print(error_message)
            print(e)  
            retry_count += 1
            retry_reason = f"Reason: {e}"
            time.sleep(retry_delay)
            
    if corrected_gpt_translation:
        error = f"::LLM_FAIL({retry_reason})::" 
        return corrected_gpt_translation, prompt, True, error
    else:
        error = f"::LLM_FAIL({retry_reason})::" 
        return "", prompt, True, error 

def chatGPT_improve_tm(row, translation_memory):
    segment_from_row = row["Source"]
    segment_context = row["Context"]
    
    source_text, source_tags_dict = create_tag_dict(segment_from_row)
    target_text, target_tags_dict = create_tag_dict(translation_memory)

    if variables.trans_info["source_language"] in variables.language_locale.keys():
        source_language_name = variables.language_locale[variables.trans_info["source_language"]]
    else:
        source_language_name = variables.trans_info["source_language"]
        
    if variables.trans_info["target_language"] in variables.language_locale.keys():
        target_language_name = variables.language_locale[variables.trans_info["target_language"]]
    else:
        target_language_name = variables.trans_info["target_language"]
        
    client = OpenAI(
    api_key=variables.openAI_api,
    timeout=30,
    )
    max_retries = 1
    retry_count = 0
    retry_delay = 3
    
    if not source_text:
        print("Source is empty, skipping...")
        return ""
    
    prompt = f"Revise the translation of the text below from {source_language_name} to {target_language_name}. You MUST provide a revised translation."
    prompt += f"\nThe translation provided is from the translation memory. Do not change the sentence structure or word order if possible."
    prompt += f"\nOnly revise the incorrect parts, make sure the translation is similar to translation memory."
    
    if is_numbered_list(source_text):
        prompt += "\nSource text starts with a numbered list, your translation must start with the same numbered list."
        
    if is_bracketed_number(source_text):
        prompt += "\nSource text contains numbers in brackets, your translation must include the same numbers in same brackets in correct positions."
    
    relevant_glossary = {}
    
    if variables.trans_info["tb_df"] is not None:
        relevant_glossary = check_termbase(source_text)        
                                           
    if len(relevant_glossary) > 0:
        prompt += "Strictly use this termbase:\n"
        for index, info in relevant_glossary.items():
            source = info["Source"]
            target = info["Target"]
            prompt += f"- {source} = {target}.\n"  
                        
    prompt += "\nRespond after 'Revised Translation:' with nothing but your revised translation."
    prompt += "\nText:"
    prompt += f"\n{source_text}"
    prompt += f"\nTranslation (from translation memory):"
    prompt += f"\n{target_text}"
    if segment_context != "N/A":
        prompt += f"\nAdditional info about text: \n{segment_context}"
    prompt += f"\nRevised Translation:"
    
    while retry_count < max_retries:        
        try: 
            response = client.chat.completions.create(
                model=variables.selected_model,
                messages=[
                    {"role": "system", "content": "You are a localization & translation expert."},
                    {"role": "user", "content": prompt},
                ],
            )
            gpt_translation = response.choices[0].message.content
            corrected_gpt_translation = correction(gpt_translation, target_text)
            variables.trans_info["job_token_count"] += response.usage.total_tokens
            if (len(source_tags_dict) >= 1 and len(target_tags_dict) <= 0) or (len(source_tags_dict) <= 0 and len(target_tags_dict) >= 1):
                missing_in_target, missing_in_source, mismatched_values = find_tag_discrepancies(source_tags_dict, target_tags_dict)
                all_discrepancies = missing_in_target | missing_in_source | mismatched_values
                corrected_gpt_translation = remove_discrepant_tags(corrected_gpt_translation, all_discrepancies)
            if len(source_tags_dict) >= 1 and len(target_tags_dict) >= 1:
                if check_for_tags(corrected_gpt_translation, target_tags_dict):
                    corrected_gpt_translation = restore_tags(corrected_gpt_translation, source_tags_dict)
                    
            retry_reason = should_retry(target_text, corrected_gpt_translation)

            if retry_reason:
                retry_count += 1
                time.sleep(retry_delay)
            else:
                return corrected_gpt_translation, prompt, False, ""
       
        except Exception as e:
            error_message = f"An error occurred: {e}. Retrying after a delay."
            print(client.api_key)
            print(error_message)
            print(e)  
            retry_count += 1
            retry_reason = f"Reason: {e}"
            time.sleep(retry_delay)
            
    if corrected_gpt_translation:
        error = f"::LLM_FAIL({retry_reason})::" 
        return corrected_gpt_translation, prompt, True, error
    else:
        error = f"::LLM_FAIL({retry_reason})::" 
        return "", prompt, True, error 
 

def correction(improved_translation, source_text):
    if "Source Text:" in improved_translation:
        improved_translation = improved_translation.replace("Source Text:", "", 1)
    if "Improved Translation:" in improved_translation:
        improved_translation = improved_translation.replace("Improved Translation:", "", 1)
    if "***Improved Translation:***" in improved_translation:
        improved_translation = improved_translation.replace("***Improved Translation:***", "", 1)
    if "Translation:" in improved_translation:
        improved_translation = improved_translation.replace("Translation:", "", 1)
    if "Translated Text:" in improved_translation:
        improved_translation = improved_translation.replace("Translated Text:", "", 1)
    if source_text in improved_translation:
        improved_translation = improved_translation.replace(source_text, "", 1)
    if improved_translation.startswith("'") and improved_translation.endswith("'"):
        improved_translation = improved_translation[1:-1]
    if improved_translation.startswith('"') and improved_translation.endswith('"'):
        improved_translation = improved_translation[1:-1]
    if improved_translation.startswith("\s"):
        improved_translation = improved_translation[1:]
    if improved_translation.startswith("\n"):
        improved_translation = improved_translation.lstrip("\n")
    if improved_translation.endswith("\s"):
        improved_translation = improved_translation[:-1]        
    corrected_translation = improved_translation
    
    return corrected_translation

def should_retry(source_text, corrected_gpt_translation):

    if is_numbered_list(source_text) and not list(corrected_gpt_translation):
        return "Source starts with a list number but LLM translation does not."
    
    if is_bracketed_number(source_text) and not is_bracketed_number(corrected_gpt_translation):
        return "Source contains a bracketed number but the LLM translation does not."
    
    if source_text.strip() and not corrected_gpt_translation.strip():
        return "Source text is not empty, but LLM translation is empty."
    
    return None

