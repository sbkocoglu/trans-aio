from PyQt6.QtGui import QIcon
import variables
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QFormLayout, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QMessageBox, QSlider, QHBoxLayout
)
from PyQt6.QtCore import Qt
from system import save_env

class SettingsUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 450)
        self.setWindowIcon(QIcon(variables.trans_icon))
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        api_group = QGroupBox("API Keys / Providers")
        api_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Ollama"])
        self.provider_combo.setCurrentText(getattr(variables, "llm_provider", "OpenAI"))
        self.provider_combo.currentTextChanged.connect(self.update_provider_ui)
        api_layout.addRow(QLabel("LLM Provider:"), self.provider_combo)

        self.openai_widget = QWidget()
        openai_layout = QFormLayout(self.openai_widget)
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setPlaceholderText("Enter OpenAI API key")
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setText(getattr(variables, "openAI_api", ""))
        openai_layout.addRow(QLabel("OpenAI API Key:"), self.openai_key_input)

        deepl_group = QGroupBox("DeepL")
        deepl_layout = QFormLayout()
        self.deepl_key_input = QLineEdit()
        self.deepl_key_input.setPlaceholderText("Enter DeepL API key")
        self.deepl_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_key_input.setText(variables.deepl_api)
        deepl_layout.addRow(QLabel("DeepL API Key:"), self.deepl_key_input)
        deepl_group.setLayout(deepl_layout)

        self.ollama_widget = QWidget()
        ollama_layout = QFormLayout(self.ollama_widget)
        self.ollama_host_input = QLineEdit()
        self.ollama_host_input.setPlaceholderText("http://localhost:11434")
        self.ollama_host_input.setText(getattr(variables, "ollama_host", "http://localhost:11434"))
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(False)
        self.ollama_get_models_button = QPushButton("Get Models")
        self.ollama_get_models_button.clicked.connect(self.get_ollama_models)
        if hasattr(variables, "ollama_model"):
            self.ollama_model_combo.setCurrentText(variables.ollama_model)
        ollama_layout.addRow(QLabel("Ollama Host URL:"), self.ollama_host_input)
        ollama_layout.addRow(QLabel("Ollama Model:"), self.ollama_model_combo)
        ollama_layout.addRow(self.ollama_get_models_button)

        api_layout.addRow(self.openai_widget)
        api_layout.addRow(self.ollama_widget)
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

        self.threads_slider = QSlider(Qt.Orientation.Horizontal)
        self.threads_slider.setMinimum(2)
        self.threads_slider.setMaximum(6)
        self.threads_slider.setSingleStep(1)
        self.threads_slider.setTickInterval(1)
        self.threads_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threads_slider.setValue(getattr(variables, "translation_threads", 1))
        self.threads_slider.setToolTip(
            "If you are using OpenAI for translation and have API limit restrictions, use a lower value (i.e. 2)"
        )
        self.threads_value_label = QLabel(str(self.threads_slider.value()))
        self.threads_slider.valueChanged.connect(lambda v: self.threads_value_label.setText(str(v)))

        threads_layout = QHBoxLayout()
        threads_layout.addWidget(self.threads_slider)
        threads_layout.addWidget(self.threads_value_label)
        method_layout.addRow(QLabel("Translation Threads:"), threads_layout)

        method_group.setLayout(method_layout)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)

        layout.addWidget(api_group)
        layout.addWidget(deepl_group)
        layout.addWidget(method_group)
        layout.addWidget(self.save_button)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.update_provider_ui(self.provider_combo.currentText())

    def update_provider_ui(self, provider):
        if provider == "OpenAI":
            self.openai_widget.setVisible(True)
            self.ollama_widget.setVisible(False)
        else:
            self.openai_widget.setVisible(False)
            self.ollama_widget.setVisible(True)

    def get_ollama_models(self):
        import requests
        host = getattr(variables, "ollama_host", "http://localhost:11434")
        try:
            resp = requests.get(f"{host}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                self.ollama_model_combo.clear()  
                self.ollama_model_combo.addItems([m["name"] for m in data.get("models", [])])
                return
        except Exception:
            pass
        QMessageBox.warning(self, "Error", f"Failed to fetch models. Please check the host URL and make sure Ollama is running.")


    def save_settings(self):
        provider = self.provider_combo.currentText()
        openai_api = self.openai_key_input.text()
        ollama_host = self.ollama_host_input.text()
        ollama_model = self.ollama_model_combo.currentText()
        default_translation = self.translation_method_combo.currentText()
        default_revision = self.revision_method_combo.currentText()
        translation_threads = self.threads_slider.value()

        variables.default_translation = default_translation
        variables.default_revision = default_revision
        variables.translation_threads = translation_threads
        variables.ollama_host = ollama_host
        variables.ollama_model = ollama_model
        variables.deepl_api = self.deepl_key_input.text()
        variables.selected_llm = provider
        variables.openAI_api = openai_api

        save_env(
            getattr(variables, "deepl_api", ""),
            getattr(variables, "openAI_api", ""),
            default_translation,
            default_revision,
            translation_threads,
            getattr(variables, "selected_llm", "OpenAI"),
            getattr(variables, "ollama_host", ""),
            getattr(variables, "ollama_model", "")
        )

        QMessageBox.information(self, "Saved", "Settings saved successfully!")
