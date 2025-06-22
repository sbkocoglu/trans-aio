import sys, os, variables, traceback
from datetime import datetime
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
from xliff import csv_columns, csv_termbase_to_df
from translate import TranslatorUI
from settings_ui import SettingsUI
from system import load_env

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        load_env()

    def initUI(self):
        self.setWindowTitle("TransAIO")
        self.setMinimumSize(500,300)

        top_menubar = self.menuBar()
        self.settings_menu = top_menubar.addMenu("Settings")
        llm_settings_action = QAction("Translation Settings", self)
        self.settings_menu.addAction(llm_settings_action)
        self.settings_menu.triggered.connect(self.settings_ui)

        self.help_menu = top_menubar.addMenu("Help")
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.about_dialog)
        self.help_menu.addAction(self.about_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        select_mqxliff_layout = QHBoxLayout()
        self.select_mqxliff_label = QLabel("Add MQXLIFF File")
        self.select_mqxliff_button = QPushButton("Select")
        self.select_mqxliff_button.clicked.connect(
            lambda: self.select_file("MQXLIFF", "MQXLIFF Files (*.mqxliff)", ".mqxliff", self.select_mqxliff_label)
        )
        select_mqxliff_layout.addWidget(self.select_mqxliff_label)
        select_mqxliff_layout.addWidget(self.select_mqxliff_button)

        add_tm_layout = QHBoxLayout()
        self.add_tm_label = QLabel("Add Translation Memory")
        self.add_tm_button = QPushButton("Select")
        self.add_tm_button.clicked.connect(
            lambda: self.select_file("TM", "TMX Files (*.tmx)", ".tmx", self.add_tm_label)
        )
        add_tb_layout = QHBoxLayout()
        self.add_tb_label = QLabel("Add Termbase")
        self.add_tb_button = QPushButton("Select")
        self.add_tb_button.clicked.connect(
            lambda: self.select_file("TB", "CSV Files (*.csv)", ".csv", self.add_tb_label)
        )
        add_tm_layout.addWidget(self.add_tm_label)
        add_tm_layout.addWidget(self.add_tm_button)
        add_tb_layout.addWidget(self.add_tb_label)
        add_tb_layout.addWidget(self.add_tb_button)

        self.start_trans_button = QPushButton("Start")
        self.start_trans_button.clicked.connect(self.start_translation)

        main_layout.addLayout(select_mqxliff_layout)
        main_layout.addLayout(add_tm_layout)
        main_layout.addLayout(add_tb_layout)
        main_layout.addWidget(self.start_trans_button)

    def select_file(self, label_prefix: str, file_filter: str, expected_extension: str, label_widget: QLabel):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select a {label_prefix} File", "", f"{file_filter};;All Files (*)")       
        if file_path:
            if file_path.endswith(expected_extension):
                label_widget.setText(f"{label_prefix}: {os.path.basename(file_path)}")
                if expected_extension == ".csv":
                    variables.trans_info["tm_path"] = file_path
                    language_columns = csv_columns(file_path)
                    select_language_dialog = LanguageSelect(language_columns, file_path)
                    select_language_dialog.exec()
                elif expected_extension == ".tmx":
                    variables.trans_info["tb_path"] = file_path
                elif expected_extension == ".mqxliff":
                    file_name = os.path.basename(file_path)
                    variables.trans_info["file_name"] = file_name
                    variables.trans_info["file_path"] = file_path
            else:
                QMessageBox.warning(self, "Invalid File", f"Please select a valid {expected_extension} file")

    def start_translation(self):
        if variables.trans_info["file_path"] == None:
            QMessageBox.warning(self, "Error", f"Select a MQXLIFF file first.")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "MQXLIFF file (*.mqxliff)")
        if save_path:
            variables.trans_info["save_path"] = save_path
            self.translation_thread = TranslatorUI()
            self.translation_thread.show()

    def about_dialog(self):
        about_message = f"TransAIO - All-in-one translation tool.\nDeveloped by Serkan B. Kocoglu.\nVisit the GitHub page for more: https://github.com/sbkocoglu/trans-aio."
        QMessageBox.about(self, f"About TransAIO", about_message) 

    def settings_ui(self):
        self.settings_ui = SettingsUI()
        self.settings_ui.show()

class LanguageSelect(QDialog):
    def __init__(self, language_columns, file_path):
        super().__init__()

        self.setWindowTitle("Select Languages")
        
        source_label = QLabel("Source Language:")
        self.source_dropdown = QComboBox()
        self.source_dropdown.addItems(language_columns)
        source_layout = QHBoxLayout()
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_dropdown)

        target_label = QLabel("Target Language:")
        self.target_dropdown = QComboBox()
        self.target_dropdown.addItems(language_columns)
        target_layout = QHBoxLayout()
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.dropdown2)

        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(lambda : self.languages_selected(file_path))

        main_layout = QVBoxLayout()
        main_layout.addLayout(source_layout)
        main_layout.addLayout(target_layout)
        main_layout.addWidget(accept_button)

        self.setLayout(main_layout)
        
    def languages_selected(self, file_path):
        selected_source = self.source_dropdown.currentText()
        selected_target = self.target_dropdown.currentText()

        if selected_source == selected_target:
            QMessageBox.warning(self, "Language Error", "Source and Target languages must be different.")
        else:
            variables.trans_info["tb_df"] = csv_termbase_to_df(file_path, selected_source, selected_target)
            self.accept()

def unhandled_exception_handler(exc_type, exc_value, exc_traceback):
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")
    print(f"[{current_time}] - Unhandled exception: {exc_type.__name__}: {exc_value}\n")
    error_log = traceback.format_exception(exc_type, exc_value, exc_traceback)
    error_log_string = str(error_log)
    error_log_string = error_log_string.replace(r'\n', '\n')
    with open(f"[{current_date}] - Error.log", "a") as f:
        f.write(f"[{current_time}] - {error_log_string}\n")
    error_box = QMessageBox()
    error_box.warning(None,"Unhandled Error", f"Unhandled exception: {exc_type.__name__}: {exc_value}.\nCheck '[{current_date}] - Error.log' for details.") 
        
sys.excepthook = unhandled_exception_handler

if __name__ == "__main__":
    app = QApplication(sys.argv)
    trans_app = MainUI()
    trans_app.show()
    sys.exit(app.exec())