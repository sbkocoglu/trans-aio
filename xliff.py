import re, chardet
import string
import pandas as pd
import lxml.etree as etree
from segment import extract_elements_to_dict

def analyze_mqxliff(file_path: str):
    """Anaylzes memoQ xliff file and converts it to a pandas dataframe.
    file_path: Path to memoQ xliff
    Returns a pandas dataframe.
    Rows: Segment: int | Source: string | Target: string | Locked: string | Context: string  
    """

    parser = etree.XMLParser(strip_cdata=False)
    tree = etree.parse(file_path, parser) 
    root = tree.getroot()
    rows = []
    
    for file_elem in root.iter('{urn:oasis:names:tc:xliff:document:1.2}file'):
        original_file = file_elem.get('original', '404 not found')
        source_language = file_elem.get('source-language', '404 not found')
        target_language = file_elem.get('target-language', '404 not found')
    if source_language == '404 not found' or target_language == '404 not found':
        raise ValueError(f"Error: Source language and/or target language element not found in the document: {original_file}")  
    
    for trans_unit in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'):
        trans_id = trans_unit.get('id')
        is_locked = trans_unit.get('{MQXliff}locked', 'Null')       
        source_element = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
        target_element = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}target')
        note_elem = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}note')

        if source_element is not None and target_element is not None:
            source = ''.join(source_element.itertext())
            target = ''.join(target_element.itertext())
        else:
            source = 'Null'
            target = 'Null'
        if note_elem is not None:
            note_text = ''.join(note_elem.itertext())
        else:
            note_text = ''

        rows.append({'Segment': int(trans_id),'Source': source, 'Target': target, 'Locked' : is_locked, 'Context' : note_text})
        
    analyzed_df = pd.DataFrame(rows)
    analyzed_df.reset_index(drop=True, inplace=True)
    return analyzed_df

def update_mqxliff(dataframe: pd.DataFrame, file_path: str, save_path: str):   
    """Updates a memoQ xliff with a pandas dataframe values and saves it.
    dataframe: Pandas dataframe with updated values/
    file_path: memoQ xliff to be updated
    save_path: Save destination for the updated memoQ xliff
    """

    parser = etree.XMLParser(strip_cdata=False)
    tree = etree.parse(file_path, parser)  
    root = tree.getroot()
   
    namespaces = root.nsmap
    memoq_regex = r'(<(?:mq|st|tw|bpt|ept|it|ph):[^>]+?\/?>|<\/(?:mq|st|tw|bpt|ept|it|ph):[^>]+?>|<(?:mq|st|tw|bpt|ept|it|ph):[^>]+?>|<.+?>|{})'
   
    for trans_unit in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'):
        trans_id = trans_unit.get('id')
        
        match_row = dataframe[dataframe['Segment'] == int(trans_id)]
        if not match_row.empty:                
            df_target_text = match_row['LLM'].iloc[0]  
            df_target_text = str(df_target_text) if not pd.isna(df_target_text) else ''

            target_element = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}target', namespaces)
            source_element = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
            
            if target_element != None:
                edited_target = df_target_text.lstrip() 
                elements_dict = extract_elements_to_dict(source_element)
                parts = re.split(memoq_regex, edited_target)
                for part in parts:
                    if part: 
                        cleaned_part = part.replace('\n', '')
                        if re.match(r'(<(?:mq|st|tw|bpt|ept|it|ph):.+?\s*/>)|(<\/(?:mq|st|tw|bpt|ept|it|ph):.+?>)|(<(?:mq|st|tw|bpt|ept|it|ph):.+?>)|<.+?>|{}', cleaned_part, re.DOTALL):
                            try:
                                for key, value in elements_dict.items():
                                    normalized_part = part.strip().replace('&', '&amp')
                                    normalized_value_text = value['text'].strip().replace('&', '&amp')
                                    if normalized_part == normalized_value_text:
                                        element_type, element_id = key.split('_', 1)
                                        element = etree.Element(element_type)
                                        if value['attributes']:
                                            for attr_name, attr_value in value['attributes'].items():
                                                element.set(attr_name, attr_value)
                                        element.text = part.replace('&', '&amp')
                                        target_element.append(element)
                                if target_element.tail is None:
                                    target_element.tail = '' 

                            except etree.XMLSyntaxError as e:
                                print(f"Error (XMLSyntaxError): {e} - matched_string: '{part}'")
                        else:
                            if len(target_element) > 0:
                                last_element = target_element[-1]
                                if last_element.tail is None:
                                    last_element.tail = part  
                                else:
                                    last_element.tail += part 
                            else:
                                target_element.text = part                 
    with open(save_path, 'wb') as doc:
        doc.write(etree.tostring(root))

def csv_termbase_to_df(csv_path: str, source_language: str, target_language: str):
    """Converts a cvs termbase into a pandas dataframe.
    csv_path: Path to termbase file.
    source_language: Source language to be retrieved.
    target_language: Target_language to be retrieved.
    Returns a pandas dataframe.
    """

    with open(csv_path, 'rb') as f:
        result = chardet.detect(f.read())
        csv_encoding = result['encoding']
    
    try:
        df = pd.read_csv(csv_path, encoding=csv_encoding)
    except pd.errors.ParserError:
        df = pd.read_csv(csv_path, encoding=csv_encoding, delimiter='\t')

    termbase_df = df.loc[:, [source_language, target_language]].rename(columns={
        source_language: 'Source',
        target_language: 'Target',
    })
    
    termbase_df = termbase_df.dropna()   
    termbase_df = termbase_df.astype(str)
    
    return termbase_df

def csv_columns(csv_path: string):
    """Finds and extracts the languages column from a csv file (for termbases).
    Returns language_columns as a list[str]
    """

    with open(csv_path, 'rb') as f:
        result = chardet.detect(f.read())
        csv_encoding = result['encoding']
    try:
        df = pd.read_csv(csv_path, encoding=csv_encoding)
    except pd.errors.ParserError:
        df = pd.read_csv(csv_path, encoding=csv_encoding, delimiter='\t')
        
    language_def_columns = [col for col in df.columns if col.endswith('_Def')]

    language_columns = [col.replace('_Def', '') for col in language_def_columns]
    
    return language_columns