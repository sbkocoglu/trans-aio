import variables, pathlib, os
import pandas as pd
from segment import is_number, check_tm
from machine_trans import deepl_translate
from xliff import AnalyzerThread, update_mqxliff
from PyQt6.QtCore import QMutex, QObject, QRunnable, QThread, pyqtSignal, pyqtSlot, QThreadPool
from PyQt6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget, QApplication

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
        if is_number(self.row['Source']):
            self.trans_df.at[self.index, 'Translation'] = self.row['Source']
            translated_segment = self.row['Source']
            self.append_lists(self.row['Segment'], 'N/A', self.row['Source'], 'Translation skipped, numbers only segment.') 
        else:   
            tm_match = check_tm(self.row['Source'], variables.trans_info['tm_df'])
            if not tm_match.empty:
                if float(tm_match['Similarity']) == 100:
                    self.trans_df.at[self.index, 'Translation'] = tm_match['Target']
                    self.append_lists(self.row['Segment'], 'N/A', tm_match['Target'], 'Translation skipped, TM match found.')
                    variables.trans_info['tm_match'] += 1                            
                elif float(tm_match['Similarity']) < 100 and float(tm_match['Similarity']) > 79:
                    translated_segment, translation_log = deepl_translate(self.row, tm_match['Target'])
                    self.trans_df.at[self.index, 'Translation'] = translated_segment
                    self.append_lists(self.row['Segment'], translation_log, translated_segment, 'Translated with DeepL, 80%+ TM match.')
                    variables.trans_info['tm_match_partial'] += 1
                    variables.trans_info['segments_translated'] += 1
                else:
                    translated_segment, translation_log = deepl_translate(self.row)
                    self.trans_df.at[self.index, 'Translation'] = translated_segment
                    self.append_lists(self.row['Segment'], translation_log, translated_segment, 'Translated with DeepL.')
                    variables.trans_info['segments_translated'] += 1
            else:
                translated_segment, translation_log = deepl_translate(self.row)
                self.trans_df.at[self.index, 'Translation'] = translated_segment
                self.append_lists(self.row['Segment'], translation_log, translated_segment, 'Translated with DeepL.')
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

class TranslatorThread(QThread):
    def __init__(self, qWidget, update_progress_bar):
        super().__init__()
        self.translator_object = TranslatorObject()
        self.translator_object.update_progress_signal.connect(update_progress_bar)
        self.qWidget = qWidget     
        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(4)

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
        self.current_translation = 0
        self.progress = 0
        variables.trans_info["current_step"] += 1
        self.qWidget.main_progress_label.setText(f"Analyzing MQXLIFF - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        self.qWidget.main_progress_bar.setValue(int(variables.trans_info["current_step"] / variables.trans_info["total_steps"]))

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
            update_mqxliff(variables.trans_info['file_path'])

            self.translator_object.update_progress_signal.emit(100)   

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
        self.current_thread.finished.connect(self.start_machine_translation)

    def update_progress_bar(self, progress):
        QApplication.processEvents()  
        self.sub_progress_bar.setValue(progress)

    def start_machine_translation(self):
        self.sub_progress_label.setText("Translating segments with machine translation...")
        self.current_thread = TranslatorThread(self, self.update_progress_bar)
        self.current_thread.start()
        self.current_thread.finished.connect(self.start_llm_translation)


    def start_llm_translation(self):
        self.current_thread = None

    def cancel_process(self):
        self.current_thread.terminate()
        self.current_thread.exit()
        self.current_thread.quit()
        self.current_thread.wait()
        self.close()