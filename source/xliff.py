import re, chardet, string, variables, zipfile, os
import pandas as pd
import lxml.etree as etree
from segment import create_memoq_elements_dict
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

def extract_mqxliff(mqxlz_path, extract_to="_temp/extracted_mqxliff"):
    with zipfile.ZipFile(mqxlz_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return [os.path.join(extract_to, f) for f in os.listdir(extract_to) if f.endswith('.mqxliff')]

class AnalyzerObject(QObject):
    update_progress_signal = pyqtSignal(int)
    update_main_progress_signal = pyqtSignal(int)    
    process_finished_signal = pyqtSignal()

class AnalyzerThread(QThread):
    def __init__(self, qWidget):
        super().__init__()
        self.qWidget = qWidget
        self.analyzer_object = AnalyzerObject()
        self.analyzer_object.update_progress_signal.connect(self.qWidget.update_progress_bar)
        self.analyzer_object.update_main_progress_signal.connect(self.qWidget.update_main_progress_bar)

    def run(self):
        file_path = variables.trans_info["file_path"]

        parser = etree.XMLParser(strip_cdata=False)
        if file_path.endswith(".mqxliff"):
            tree = etree.parse(file_path, parser)
        else:
            file_path = extract_mqxliff(file_path)[0]
            tree = etree.parse(file_path, parser)
        root = tree.getroot()
        rows = []
    
        for file_elem in root.iter("{urn:oasis:names:tc:xliff:document:1.2}file"):
            original_file = file_elem.get("original", "404 not found")
            source_language = file_elem.get("source-language", "404 not found")
            variables.trans_info["source_language"] = source_language
            target_language = file_elem.get("target-language", "404 not found")
            variables.trans_info["target_language"] = target_language
        if source_language == "404 not found" or target_language == "404 not found":
            raise ValueError(f"Error: Source language and/or target language element not found in the document: {original_file}")  
    
        analysis_length = sum(1 for _ in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'))       
        completed_analysis = 0
        progress_update_treshold = 0
        variables.trans_info["current_step"] += 1
        self.qWidget.main_progress_label.setText(f"Analyzing MQXLIFF - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        main_progress = variables.trans_info["current_step"] / variables.trans_info["total_steps"] * 100
        self.analyzer_object.update_main_progress_signal.emit(round(main_progress))

        for trans_unit in root.iter("{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
            trans_id = trans_unit.get("id")
            is_locked = trans_unit.get("{MQXliff}locked", "Null")       
            source_element = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}source")
            target_element = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}target")
            note_elem = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}note")

            if source_element is not None and target_element is not None:
                source = "".join(source_element.itertext())
                target = "".join(target_element.itertext())
            else:
                source = "Null"
                target = "Null"
            if note_elem is not None:
                note_text = "".join(note_elem.itertext())
            else:
                note_text = ""

            rows.append({"Segment": int(trans_id),"Source": source, "Target": target, "Locked" : is_locked, "Context" : note_text})
            completed_analysis += 1
            progress = (completed_analysis / analysis_length) * 100 
            if progress > progress_update_treshold + 5:
                self.analyzer_object.update_progress_signal.emit(round(progress))
                progress_update_treshold += 5

        analyzed_df = pd.DataFrame(rows)
        analyzed_df.reset_index(drop=True, inplace=True)
        variables.trans_info['mqxliff_df'] = analyzed_df
        self.analyzer_object.update_progress_signal.emit(100)

class UpdaterThread(QThread):
    def __init__(self, qWidget):
        super().__init__()
        self.qWidget = qWidget
        self.analyzer_object = AnalyzerObject()
        self.analyzer_object.update_progress_signal.connect(self.qWidget.update_progress_bar)
        self.analyzer_object.update_main_progress_signal.connect(self.qWidget.update_main_progress_bar)
        self.analyzer_object.process_finished_signal.connect(self.qWidget.translation_finished)

    def run(self):   
        dataframe = variables.trans_info["mqxliff_df"]
        file_path = variables.trans_info["file_path"]
        save_path = variables.trans_info["save_path"]
        parser = etree.XMLParser(strip_cdata=False)
        tree = etree.parse(file_path, parser)  
        root = tree.getroot()

        df_length = sum(1 for _ in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'))       
        completed_segments = 0
        progress_update_treshold = 0

        main_progress = variables.trans_info["current_step"] / variables.trans_info["total_steps"] * 100
        self.analyzer_object.update_main_progress_signal.emit(round(main_progress))

        namespaces = root.nsmap
        memoq_regex = r"(<(?:mq|st|tw|bpt|ept|it|ph):[^>]+?\/?>|<\/(?:mq|st|tw|bpt|ept|it|ph):[^>]+?>|<(?:mq|st|tw|bpt|ept|it|ph):[^>]+?>|<.+?>|{})"
   
        for trans_unit in root.iter("{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
            trans_id = trans_unit.get("id")
        
            match_row = dataframe[dataframe["Segment"] == int(trans_id)]
            if not match_row.empty:                
                df_target_text = match_row["Translation"].iloc[0]  
                df_target_text = str(df_target_text) if not pd.isna(df_target_text) else ""

                target_element = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}target", namespaces)
                source_element = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}source")
            
                if target_element != None:
                    edited_target = df_target_text.lstrip() 
                    elements_dict = create_memoq_elements_dict(source_element)
                    parts = re.split(memoq_regex, edited_target)
                    for part in parts:
                        if part: 
                            cleaned_part = part.replace("\n", "")
                            if re.match(r"(<(?:mq|st|tw|bpt|ept|it|ph):.+?\s*/>)|(<\/(?:mq|st|tw|bpt|ept|it|ph):.+?>)|(<(?:mq|st|tw|bpt|ept|it|ph):.+?>)|<.+?>|{}", cleaned_part, re.DOTALL):
                                try:
                                    for key, value in elements_dict.items():
                                        normalized_part = part.strip().replace("&", "&amp")
                                        normalized_value_text = value["text"].strip().replace("&", "&amp")
                                        if normalized_part == normalized_value_text:
                                            element_type, element_id = key.split("_", 1)
                                            element = etree.Element(element_type)
                                            if value["attributes"]:
                                                for attr_name, attr_value in value["attributes"].items():
                                                    element.set(attr_name, attr_value)
                                            element.text = part.replace("&", "&amp")
                                            target_element.append(element)
                                    if target_element.tail is None:
                                        target_element.tail = "" 

                                except etree.XMLSyntaxError as e:
                                    print(f"Error (XMLSyntaxError): {e} - matched_string: {part}")
                            else:
                                if len(target_element) > 0:
                                    last_element = target_element[-1]
                                    if last_element.tail is None:
                                        last_element.tail = part  
                                    else:
                                        last_element.tail += part 
                                else:
                                    target_element.text = part         
            completed_segments += 1
            progress = (completed_segments / df_length) * 100 
            if progress > progress_update_treshold + 5:
                self.analyzer_object.update_progress_signal.emit(int(progress))
                progress_update_treshold += 5

        with open(save_path, "wb") as doc:
            doc.write(etree.tostring(root))
        self.analyzer_object.update_progress_signal.emit(int(100))
        self.analyzer_object.process_finished_signal.emit()

def csv_termbase_to_df(csv_path: str, source_language: str, target_language: str):
    """Converts a cvs termbase into a pandas dataframe.
    csv_path: Path to termbase file.
    source_language: Source language to be retrieved.
    target_language: Target_language to be retrieved.
    Returns a pandas dataframe.
    """

    with open(csv_path, "rb") as f:
        result = chardet.detect(f.read())
        csv_encoding = result["encoding"]
    
    try:
        df = pd.read_csv(csv_path, encoding=csv_encoding)
    except pd.errors.ParserError:
        df = pd.read_csv(csv_path, encoding=csv_encoding, delimiter="\t")

    termbase_df = df.loc[:, [source_language, target_language]].rename(columns={
        source_language: "Source",
        target_language: "Target",
    })
    
    termbase_df = termbase_df.dropna()   
    termbase_df = termbase_df.astype(str)
    
    return termbase_df

def csv_columns(csv_path: string):
    """Finds and extracts the languages column from a csv file (for termbases).
    Returns language_columns as a list[str]
    """

    with open(csv_path, "rb") as f:
        result = chardet.detect(f.read())
        csv_encoding = result["encoding"]
    try:
        df = pd.read_csv(csv_path, encoding=csv_encoding)
    except pd.errors.ParserError:
        df = pd.read_csv(csv_path, encoding=csv_encoding, delimiter="\t")
        
    language_def_columns = [col for col in df.columns if col.endswith("_Def")]

    language_columns = [col.replace("_Def", "") for col in language_def_columns]
    
    return language_columns