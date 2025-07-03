from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
import time, variables
from segment import (restore_tags, find_tag_discrepancies, remove_discrepant_tags, create_tag_dict, 
                         is_numbered_list, is_bracketed_number, check_for_tags, check_termbase)

def select_llm():
    if variables.selected_llm == "OpenAI":
        llm = ChatOpenAI(
            model=variables.openAI_model,
            temperature=0.5,
            max_retries=10,
            timeout=30,
            api_key=variables.openAI_api,
        )
    elif variables.selected_llm == "Ollama":
        llm = ChatOllama(
        model = variables.ollama_model,
        temperature = 0.5,
        num_predict = -1,
        base_url = variables.ollama_host,
        )
    return llm

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
    if segment_context.strip() != "N/A" and segment_context.strip() != "":
        prompt += f"\nAdditional info about the segment to help you translate: \n{segment_context}"
    prompt += "\nText:"
    prompt += f"\n{source_text}"
    prompt += "\nTranslation:"  
    
    messages = [
        (
            "system",
            "You are a localization & translation expert.",
        ),
        ("human", prompt),
    ]

    max_retries = 10
    retry_delay = 20 if variables.selected_llm == "OpenAI" else 3
    retry_count = 0

    llm = select_llm()
    
    while retry_count < max_retries:
        try:
            response = llm.invoke(messages)
            llm_translation = response.content
            corrected_llm_translation = correction(llm_translation, source_text)
            if len(source_tags_dict) >= 1:
                if check_for_tags(corrected_llm_translation, source_tags_dict):
                    corrected_llm_translation = restore_tags(corrected_llm_translation, source_tags_dict)
            retry_reason = should_retry(source_text, corrected_llm_translation)
            if hasattr(response, "response_metadata") and response.response_metadata:
                total_tokens = response.response_metadata.get("token_usage", {}).get("total_tokens", None)
            elif hasattr(response, "usage_metadata") and response.usage_metadata:
                total_tokens = response.usage_metadata.get("total_tokens", None)
            else:
                total_tokens = 0
            if total_tokens is not None:
                variables.trans_info["token_count"] =+ total_tokens

            if retry_reason:
                retry_count += 1
                time.sleep(retry_delay)
                continue
            else:
                return corrected_llm_translation, prompt

        except Exception as e:
            error_message = f"An error occurred: {e}. Retrying after a delay."
            print(error_message)
            retry_count += 1
            retry_reason = f"Reason: {e}"
            time.sleep(retry_delay)

    error = f"::LLM_FAIL({retry_reason})::"
    return error, prompt

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
    if segment_context.strip() != "N/A" and segment_context.strip() != "":
        prompt += f"\nAdditional info about the segment to help you translate: \n{segment_context}"
    prompt += "\nText:"
    prompt += f"\n{source_text}"
    prompt += f"\nTranslation (from translation memory):"
    prompt += f"\n{target_text}"
    prompt += f"\nRevised Translation:"
    
    messages = [
        (
            "system",
            "You are a localization & translation expert.",
        ),
        ("human", prompt),
    ]

    max_retries = 10
    retry_delay = 20 if variables.selected_llm == "OpenAI" else 3
    retry_count = 0

    llm = select_llm()
    
    while retry_count < max_retries:
        try:
            response = llm.invoke(messages)
            llm_translation = response.content
            corrected_llm_translation = correction(llm_translation, source_text)
            if len(source_tags_dict) >= 1:
                if check_for_tags(corrected_llm_translation, source_tags_dict):
                    corrected_llm_translation = restore_tags(corrected_llm_translation, source_tags_dict)
            retry_reason = should_retry(source_text, corrected_llm_translation)
            if hasattr(response, "response_metadata") and response.response_metadata:
                total_tokens = response.response_metadata.get("token_usage", {}).get("total_tokens", None)
            elif hasattr(response, "usage_metadata") and response.usage_metadata:
                total_tokens = response.usage_metadata.get("total_tokens", None)
            else:
                total_tokens = 0
            if total_tokens is not None:
                variables.trans_info["token_count"] =+ total_tokens

            if retry_reason:
                retry_count += 1
                time.sleep(retry_delay)
                continue
            else:
                return corrected_llm_translation, prompt

        except Exception as e:
            error_message = f"An error occurred: {e}. Retrying after a delay."
            print(error_message)
            retry_count += 1
            retry_reason = f"Reason: {e}"
            time.sleep(retry_delay)

    error = f"::LLM_FAIL({retry_reason})::"
    return error, prompt
 

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
    corrected_translation = improved_translation.strip()
    
    return corrected_translation

def should_retry(source_text, corrected_gpt_translation):

    if is_numbered_list(source_text) and not list(corrected_gpt_translation):
        return "Source starts with a list number but LLM translation does not."
    
    if is_bracketed_number(source_text) and not is_bracketed_number(corrected_gpt_translation):
        return "Source contains a bracketed number but the LLM translation does not."
    
    if source_text.strip() and not corrected_gpt_translation.strip():
        return "Source text is not empty, but LLM translation is empty."
    
    return None

