import variables
from xliff import AnalyzerThread
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget



class TranslatorThread(QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        segment_numbers = []
        llm_prompts = []
        llm_responses = []
        trans_results = []
        version_list = []
        trans_save = variables.trans_save

        def append_lists(segment_number, llm_prompt, llm_response, trans_result):
            segment_numbers.append(segment_number)
            llm_prompts.append(llm_prompt)
            llm_responses.append(llm_response)
            trans_results.append(trans_result)
            version_list.append("")
            
        trans_df = variables.trans_info["mqxliff_df"]
        trans_df = trans_df[trans_df['Locked'] == 'Null']

class TranslatorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Progress")
        self.setMinimumSize(600,200)

        main_layout = QVBoxLayout()
        main_progress_label = QLabel(f"Translation Started - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        self.main_progress_bar = QProgressBar()

        sub_progress_label = QLabel ("Sub-process name")
        self.sub_progress_bar = QProgressBar()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(True)
        self.cancel_button.clicked.connect(self.cancel_process)

        main_layout.addWidget(main_progress_label)
        main_layout.addWidget(self.main_progress_bar)
        main_layout.addWidget(sub_progress_label)
        main_layout.addWidget(self.sub_progress_bar)
        main_layout.addWidget(self.cancel_button)
        self.setLayout(main_layout)

        self.current_thread = AnalyzerThread(self)
        self.current_thread.start()
        main_progress_label.setText(f"Analyzing MQXLIFF - {variables.trans_info["current_step"]}/{variables.trans_info["total_steps"]}")
        
    def cancel_process(self):
        self.current_thread.terminate()
        self.current_thread.exit()
        self.current_thread.quit()
        self.current_thread.wait()
        self.close()
