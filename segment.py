import pandas as pd
import re
import html

def check_tm(segment, df, source_col='Source', target_col='Target', threshold=80):
    """Checks the translation memory to find a fuzzy match. 
    segment -> Input segment
    df -> Translation memory as pandas dataframe
    source_col -> Source segment column name of the df
    target_col -> Target segment column name of the df
    treshold -> Fuzzy match percent

    Returns -> highest fuzzy match as pd.Series() or an empty pd.Series() if no valid translation memory
    """
    if df.empty:
        return pd.Series()
    
    def fuzzy_match(translation_memory):
        if len(translation_memory) <= 0 or len(segment) <= 0:
            return 0
        distance = lev_distance(translation_memory, segment)
        max_length = max(len(translation_memory), len(segment))
        if max_length == 0:
            return 0
        else:
            similarity = 1.0 - distance / max_length
            fuzzy_percent = float(similarity) * 100
            return fuzzy_percent       
    
    df['Similarity'] = df[source_col].apply(fuzzy_match)
    
    filtered_df = df[df['Similarity'] > threshold]
    
    if not filtered_df.empty:
        best_match = filtered_df.loc[filtered_df['Similarity'].idxmax()]
        return best_match[[source_col, target_col, 'Similarity']]
    else:
        return pd.Series()

def lev_distance(s1, s2):
    "Simple function to check levenshtein distance between segments"
    if len(s1) < len(s2):
        return lev_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]  

def is_number(s):
    "Check if segment contains a number"
    pattern = r'^\d+(\.\d*)?[)\.]?$'
    match = re.match(pattern, s)
    return bool(match)

def is_numbered_list(s):
    "Check if segment contains numbered list (e.g. 1., 2., 3. ...)"
    pattern = r'^\d+[.)]'
    match = re.match(pattern, s)
    return bool(match)

def is_bracketed_number(s):
    "Check if segment contains bracketed number (e.g. (1), (2), (3) ...)"
    pattern = r'(\{\d+[\}>]|\<\d+\})'
    match = re.search(pattern, s)
    return bool(match)

def create_tag_dict(text):
    """Replaces the memoQ tags with a placeholder (<UTAG{tag_counter}>).
    Creates a dictionary from the segment with memoQ tags.
    Adds the placesholder to the tags dictionary.
    Returns the segment (without tags) and tags dictionary.
    """
    memoq_regex = r"<\/?(tw:it|st:it|mq:nt|mq:it|mq:ch|mq:gap|mq:rxt-req|mq:rxt|mq:txml-ut|mq:pi|bpt|ept|ph|it)(\s[^>]*)?>"
    
    tags_dict = {}
    tag_counter = 1

    def replace_tag(match):
        nonlocal tag_counter
        full_tag = match.group(0)
        decoded_tag = html.unescape(full_tag)
        unique_tag = f"<UTAG{tag_counter}/>"
        tags_dict[unique_tag] = decoded_tag
        tag_counter += 1
        return unique_tag

    cleaned_text = re.sub(memoq_regex, replace_tag, text)
    
    return cleaned_text, tags_dict

def find_tag_discrepancies(source_dict, target_dict):
    """Checks if there are any missing tags between the source segment and target segment.
    Returns missing tags in target segment, missing tags in source segment, and mismatched values between the segments.
    """
    source_tags = set(source_dict.keys())
    target_tags = set(target_dict.keys())
    
    missing_in_target = source_tags - target_tags
    
    missing_in_source = target_tags - source_tags
    
    mismatched_values = {tag for tag in source_tags & target_tags if source_dict[tag] != target_dict[tag]}
    
    return missing_in_target, missing_in_source, mismatched_values

def remove_discrepant_tags(text, tags_to_remove):
    "Removes discrepent tags in the segment."
    for tag in tags_to_remove:
        text = text.replace(tag, '')
    return text

def restore_tags(cleaned_text, tags_dict):
    "Restores placeholder tags in a segment to their original values from the tags dictionary."
    def extract_number(tag):
        match = re.search(r'\d+', tag)
        if match:
            return int(match.group())
        else:
            return float('inf')  

    for unique_tag in sorted(tags_dict.keys(), key=extract_number):
        cleaned_text = cleaned_text.replace(unique_tag, tags_dict[unique_tag])
    return cleaned_text

def check_for_tags(text, tags):
    "Checks for tags in a segment."
    return all(tag in text for tag in tags)

def create_memoq_elements_dict(source_element):
    """Finds and extracts additional memoQ elements such as ph, it, ept, and bpt.
    Returns the results as a dictionary.
    """
    tags = ['ph', 'it', 'ept', 'bpt']
    namespace = 'urn:oasis:names:tc:xliff:document:1.2'
    result = {}
    
    counter = 1
    
    for tag in tags:
        tag_name = f'{{{namespace}}}{tag}'
        tag_elements = source_element.findall(tag_name)
        
        if tag_elements:
            for tag_element in tag_elements:
                element_info = {
                    'attributes': tag_element.attrib,
                    'text': html.unescape(tag_element.text)
                }
                element_id = tag_element.attrib.get('id')
                if element_id is None:
                    element_id = f"no_id_{counter}"
                    counter += 1
                key = f"{tag}_{element_id}"
                
                result[key] = element_info

    return result