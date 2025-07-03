from PyQt6.QtGui import QIcon
import variables, pathlib, os
import pandas as pd
from segment import is_number, check_tm, is_link
from machine_trans import deepl_translate, check_deepl_languages
from llm_trans import chatGPT_improve_tm, chatGPT_translate
from xliff import AnalyzerThread, UpdaterThread
from PyQt6.QtCore import QMutex, QObject, QRunnable, QThread, Qt, pyqtSignal, pyqtSlot, QThreadPool
from PyQt6.QtWidgets import QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget, QApplication

mutex = QMutex()

class TranslatorWorker(QRunnable):
    def __init__(self, trans_df, index, row, append_lists, trans_completed):
        super().__init__()
        self.trans_df = trans_df
        self.index = index
        self.row = row
        self.append_lists = append_lists
        self.trans_completed = trans_completed

    @pyqtSlot()
    def run(self):
        trans_function = deepl_translate if variables.default_translation == "MT" else chatGPT_translate
        trans_tm_function = deepl_translate if variables.default_revision == "MT" else chatGPT_improve_tm
        trans_type = "MT" if variables.default_translation == "MT" else "LLM"
        trans_tm_type = "MT" if variables.default_revision == "MT" else "LLM"

        if is_number(self.row['Source']) or is_link(self.row['Source']):
            self.trans_df.at[self.index, 'Translation'] = self.row['Source']
            translated_segment = self.row['Source']
            self.append_lists(self.row['Segment'], 'N/A', self.row['Source'], 'Translation skipped, no need to translate.') 
            variables.trans_info['segments_skipped'] += 1
        else:   
            tm_match = check_tm(self.row['Source'], variables.trans_info['tm_df'])
            if not tm_match.empty:
                if float(tm_match['Similarity']) == 100:
                    self.trans_df.at[self.index, 'Translation'] = tm_match['Target']
                    self.append_lists(self.row['Segment'], f'Source Text:\n{self.row["Source"]}', tm_match['Target'], 'Translation skipped, TM match found.')
                    variables.trans_info['tm_match'] += 1                            
                elif float(tm_match['Similarity']) < 100 and float(tm_match['Similarity']) > 79:
                    translated_segment, translation_log = trans_tm_function(self.row, tm_match['Target'])
                    self.trans_df.at[self.index, 'Translation'] = translated_segment
                    self.append_lists(self.row['Segment'], translation_log, translated_segment, f'Translated with {trans_tm_type}, 80%+ TM match.')
                    variables.trans_info['tm_match_partial'] += 1
                    variables.trans_info['segments_translated'] += 1
                else:
                    translated_segment, translation_log = trans_function(self.row)
                    self.trans_df.at[self.index, 'Translation'] = translated_segment
                    self.append_lists(self.row['Segment'], translation_log, translated_segment, f'Translated with {trans_type}.')
                    variables.trans_info['segments_translated'] += 1
            else:
                translated_segment, translation_log = trans_function(self.row)
                self.trans_df.at[self.index, 'Translation'] = translated_segment
                self.append_lists(self.row['Segment'], translation_log, translated_segment, f'Translated with {trans_type}.')
                variables.trans_info['segments_translated'] += 1
        new_source = self.row['Source']

        if not variables.trans_info['tm_df'].loc[variables.trans_info['tm_df']['Source'] == new_source].empty:
            print(f"Duplicate entry found for source: {new_source}")
        else:
            new_target = translated_segment
            new_row = pd.DataFrame({'Source': [new_source], 'Target': [new_target]})
            variables.trans_info['tm_df'] = pd.concat([variables.trans_info['tm_df'], new_row], ignore_index=True)
        self.trans_completed()
 

class TranslatorObject(QObject):
    update_progress_signal = pyqtSignal(int)
    update_main_progress_signal = pyqtSignal(int)
    translation_finished_signal = pyqtSignal()

class TranslatorThread(QThread):
    def __init__(self, qWidget):
        super().__init__()
        self.translator_object = TranslatorObject()
        self.translator_object.update_progress_signal.connect(qWidget.update_progress_bar)
        self.translator_object.update_main_progress_signal.connect(qWidget.update_main_progress_bar)
        self.translator_object.translation_finished_signal.connect(qWidget.start_writing_mqxliff)
        self.qWidget = qWidget     
        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(variables.translation_threads)

    def run(self):
        self.segment_numbers = []
        self.translation_logs = []
        self.translation_results = []
        self.translation_details = []
        self.version_list = []

        def append_lists(segment_number, translation_log, translation_result, translation_detail):
            self.segment_numbers.append(segment_number)
            self.translation_logs.append(translation_log)
            self.translation_results.append(translation_result)
            self.translation_details.append(translation_detail)
            self.version_list.append("")
            
        self.trans_df = variables.trans_info["mqxliff_df"]
        self.trans_df = self.trans_df[self.trans_df['Locked'] == 'Null']
        self.segments = self.trans_df['Source']

        self.translation_length = len(self.segments)
        self.current_translation = 1
        self.progress = 0
        variables.trans_info["current_step"] += 1
        self.qWidget.main_progress_label.setText(f"Translating - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        main_progress = variables.trans_info["current_step"]/variables.trans_info["total_steps"]*100
        self.translator_object.update_main_progress_signal.emit(int(main_progress))

        for index, row in self.trans_df.iterrows():
            worker = TranslatorWorker(self.trans_df, index, row, append_lists, self.trans_completed)
            self.threadpool.start(worker)   

    def trans_completed(self):
        mutex.lock()
        self.current_translation += 1
        self.progress = (self.current_translation / self.translation_length) * 100
        self.translator_object.update_progress_signal.emit(int(self.progress))
        mutex.unlock()
        if self.current_translation == self.translation_length:
            variables.trans_info['mqxliff_df'] = self.trans_df
            self.save_translation_log(self.segment_numbers, self.translation_logs, self.translation_results, self.translation_details, self.version_list)
            self.translator_object.update_progress_signal.emit(100)  
            self.translator_object.translation_finished_signal.emit()

    def save_translation_log(self, segment_numbers, translation_logs, translation_results, translation_details, version_list):
        translation_log = {'Segment' : segment_numbers,
            'Translation Log' : translation_logs,
            'Translation Result': translation_results,
            'Translation Detail' : translation_details,
            f'Version: {variables.trans_version}' : version_list}
        
        translation_log_df = pd.DataFrame(translation_log)
        
        app_directory = pathlib.Path(os.getcwd()).absolute()
        relative_temp_dir = "_temp/machine_translation/"
        full_temp_dir = os.path.join(app_directory, relative_temp_dir)
        if not os.path.exists(full_temp_dir):
            os.makedirs(full_temp_dir)
        file_name = variables.trans_info['file_name']
        file_path = os.path.join(full_temp_dir, f"{file_name}-Machine_Translation.xlsx")
        translation_log_df.to_excel(file_path)
        
  
class TranslatorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Progress")
        self.setWindowIcon(QIcon(variables.trans_icon))
        self.setMinimumSize(600,200)

        main_layout = QVBoxLayout()
        self.main_progress_label = QLabel(f"Translation Starting - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        self.main_progress_bar = QProgressBar()

        self.sub_progress_label = QLabel ("Sub-process name")
        self.sub_progress_bar = QProgressBar()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(True)
        self.cancel_button.clicked.connect(self.cancel_process)

        main_layout.addWidget(self.main_progress_label)
        main_layout.addWidget(self.main_progress_bar)
        main_layout.addWidget(self.sub_progress_label)
        main_layout.addWidget(self.sub_progress_bar)
        main_layout.addWidget(self.cancel_button)
        self.setLayout(main_layout)

        self.current_thread = AnalyzerThread(self)
        self.current_thread.start()
        self.sub_progress_label.setText("Converting Xliff into a dataframe...")
        self.current_thread.finished.connect(self.check_for_errors)

    def check_for_errors(self):
        if variables.default_translation == "MT" or variables.default_revision == "MT":
            target_language_okay = check_deepl_languages(False, variables.trans_info["target_language"])
            source_language_okay = check_deepl_languages(True, variables.trans_info["source_language"])
            if target_language_okay and target_language_okay:
                self.start_machine_translation()
            elif not source_language_okay:
                self.translation_language_error(True)      
            elif not target_language_okay:
                self.translation_language_error(False)                
        else:
            self.start_machine_translation()

    def update_progress_bar(self, progress):
        QApplication.processEvents()  
        self.sub_progress_bar.setValue(progress)

    def update_main_progress_bar(self, progress):
        QApplication.processEvents()  
        self.main_progress_bar.setValue(progress)

    def start_machine_translation(self):
        self.sub_progress_label.setText("Translating segments...")
        self.current_thread = TranslatorThread(self)
        self.current_thread.start()

    def start_writing_mqxliff(self):
        variables.trans_info["current_step"] += 1
        self.main_progress_label.setText(f"Writing MQXLIFF - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        self.current_thread = UpdaterThread(self)
        self.current_thread.start()

    def translation_finished(self):
        error_message = f"""Segments translated: {variables.trans_info["segments_translated"]}
                            \nSegments skipped: {variables.trans_info["segments_skipped"]}
                            \nFailed translations: {variables.trans_info["translation_failed"]}"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"Translation Finished")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg_box.exec()
        self.close()
    
    def translation_language_error(self, is_source=False):
        source_language = variables.trans_info['source_language'].upper()
        target_language = variables.trans_info['target_language'].upper()
        which_language = f"Source Language ({source_language})" if is_source == True else f"Target Language ({target_language})"
        error_message = f"Unsupported {which_language} for DeepL engine. Check <a href='https://support.deepl.com/hc/en-us/articles/360019925219-DeepL-Translator-languages'>DeepL website</a> for supported languages."
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"Language Support Error")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg_box.exec()
        self.close()


    def cancel_process(self):
            if hasattr(self, "current_thread") and self.current_thread is not None:
                if isinstance(self.current_thread, QThread):
                    self.current_thread.requestInterruption()
                    self.current_thread.quit()
                    self.current_thread.wait()
                elif hasattr(self.current_thread, "terminate"):
                    self.current_thread.terminate()
                    self.current_thread.wait()
            try:
                QThreadPool.globalInstance().clear()
            except AttributeError:
                pass
            self.close()
