import base64, variables
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QFormLayout, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QMessageBox
)
from system import save_env

class SettingsUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        api_group = QGroupBox("API Keys")
        api_layout = QFormLayout()

        self.deepl_key_input = QLineEdit()
        self.deepl_key_input.setPlaceholderText("Enter DeepL API key")
        self.deepl_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_key_input.setText(variables.deepl_api)


        self.openai_key_input = QLineEdit()
        self.openai_key_input.setPlaceholderText("Enter OpenAI API key")
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setText(variables.openAI_api)

        api_layout.addRow(QLabel("DeepL API Key:"), self.deepl_key_input)
        api_layout.addRow(QLabel("OpenAI API Key:"), self.openai_key_input)
        api_group.setLayout(api_layout)

        method_group = QGroupBox("Methods")
        method_layout = QFormLayout()

        self.translation_method_combo = QComboBox()
        self.translation_method_combo.addItems(["MT", "LLM"])
        if variables.default_translation in ["MT", "LLM"]:
            self.translation_method_combo.setCurrentText(variables.default_translation)

        self.revision_method_combo = QComboBox()
        self.revision_method_combo.addItems(["MT", "LLM"])
        if variables.default_revision in ["MT", "LLM"]:
            self.revision_method_combo.setCurrentText(variables.default_revision)

        method_layout.addRow(QLabel("Translation Method:"), self.translation_method_combo)
        method_layout.addRow(QLabel("Revision Method:"), self.revision_method_combo)

        method_group.setLayout(method_layout)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)

        layout.addWidget(api_group)
        layout.addWidget(method_group)
        layout.addWidget(self.save_button)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def save_settings(self):
        deepl_api = self.deepl_key_input.text()
        openai_api = self.openai_key_input.text()
        default_translation = self.translation_method_combo.currentText()
        default_revision = self.revision_method_combo.currentText()

        variables.deepl_api = deepl_api
        variables.openAI_api = openai_api
        variables.default_translation = default_translation
        variables.default_revision = default_revision

        save_env(deepl_api, openai_api, default_translation, default_revision)

        QMessageBox.information(self, "Saved", "Settings saved successfully!")
