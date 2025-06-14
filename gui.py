import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QProgressBar, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QIntValidator
import qasync
from main import main

class ProgressHandler(QObject):
    progress_updated = pyqtSignal(int)
    total_updated = pyqtSignal(int)

    def __init__(self, progress_bar):
        super().__init__()
        self.progress_bar = progress_bar
        self.progress_updated.connect(self.progress_bar.setValue)
        self.total_updated.connect(self.progress_bar.setMaximum)

    def __call__(self, current, total):
        self.total_updated.emit(total)
        self.progress_updated.emit(current)

    def set_total(self, total):
        self.total_updated.emit(total)

    def update(self, n=1):
        self.progress_updated.emit(self.progress_bar.value() + n)

class ParserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Парсер Ozon")
        self.setGeometry(100, 100, 500, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-size: 14px;
                color: #000000;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #000000;
                padding: 6px;
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #000000;
                padding: 6px;
                border-radius: 6px;
            }
            QProgressBar {
                border: 1px solid #000000;
                border-radius: 6px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #000000;
                width: 10px;
                margin: 0.5px;
            }
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #222222;
            }
            QPushButton:disabled {
                background-color: #777777;
                color: #dddddd;
            }
            QCheckBox {
                font-size: 14px;
                color: #000000;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("Парсер Ozon")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # Поисковый запрос
        self.query_label = QLabel("Поисковый запрос:")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Введите запрос, например, 'ноутбук'")
        main_layout.addWidget(self.query_label)
        main_layout.addWidget(self.query_input)

        # Максимальное количество продуктов
        self.max_products_label = QLabel("Максимальное количество товаров:")
        self.max_products_input = QLineEdit("10")
        self.max_products_input.setValidator(QIntValidator(0, 1000000))
        main_layout.addWidget(self.max_products_label)
        main_layout.addWidget(self.max_products_input)

        # Выходной файл
        self.output_file_label = QLabel("Выходной файл (.xlsx):")
        self.output_file_input = QLineEdit("ozon_products.xlsx")
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.output_file_input)
        self.select_output_button = QPushButton("Выбрать")
        self.select_output_button.clicked.connect(self.select_output_file)
        file_layout.addWidget(self.select_output_button)
        main_layout.addWidget(self.output_file_label)
        main_layout.addLayout(file_layout)

        # Файл ссылок
        self.links_file_label = QLabel("Файл ссылок (опционально):")
        self.links_file_input = QLineEdit()
        links_file_layout = QHBoxLayout()
        links_file_layout.addWidget(self.links_file_input)
        self.select_links_button = QPushButton("Выбрать")
        self.select_links_button.clicked.connect(self.select_links_file)
        links_file_layout.addWidget(self.select_links_button)
        main_layout.addWidget(self.links_file_label)
        main_layout.addLayout(links_file_layout)

        # Чекбокс возобновления
        self.resume_check = QCheckBox("Возобновить с последней ссылки")
        main_layout.addWidget(self.resume_check)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Кнопка запуска
        self.parse_button = QPushButton("Начать парсинг")
        self.parse_button.clicked.connect(self.start_parsing)
        main_layout.addWidget(self.parse_button)

        # Поле для логов
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setFixedHeight(120)
        main_layout.addWidget(self.status_output)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Выберите выходной файл", "", "Excel files (*.xlsx)")
        if file_path:
            self.output_file_input.setText(file_path)

    def select_links_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл ссылок", "", "Text files (*.txt);;All files (*.*)")
        if file_path:
            self.links_file_input.setText(file_path)

    async def run_parsing(self, query, max_products, output_file, resume, links_file):
        try:
            progress_handler = ProgressHandler(self.progress_bar)
            await main(
                query=query,
                max_products=max_products,
                output_file=output_file,
                resume=resume,
                links_file=links_file,
                progress_handler=progress_handler
            )
            self.status_output.append(f"Парсинг завершён. Файл сохранён: {output_file}")
        except Exception as e:
            self.status_output.append(f"Ошибка при парсинге: {str(e)}")
        finally:
            self.parse_button.setEnabled(True)
            self.progress_bar.setValue(0)

    @qasync.asyncSlot()
    async def start_parsing(self):
        query = self.query_input.text().strip()
        if not query:
            self.status_output.append("Ошибка: Введите поисковый запрос")
            return
        try:
            max_products = int(self.max_products_input.text())
        except ValueError:
            self.status_output.append("Ошибка: Введите корректное число для количества товаров")
            return
        output_file = self.output_file_input.text().strip()
        if not output_file:
            self.status_output.append("Ошибка: Введите имя выходного файла")
            return
        if not output_file.endswith('.xlsx'):
            output_file += '.xlsx'
            self.output_file_input.setText(output_file)
        links_file = self.links_file_input.text().strip() or None
        resume = self.resume_check.isChecked()

        self.parse_button.setEnabled(False)
        self.status_output.append("Парсинг начат...")
        await self.run_parsing(query, max_products, output_file, resume, links_file)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = ParserApp()
    window.show()
    with loop:
        loop.run_forever()