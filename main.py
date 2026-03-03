import os
import shutil
import sys
import json
import rawpy
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QListWidgetItem, QStackedWidget, 
                             QFileDialog, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont

# 获取资源路径（解决打包图标显示问题）/ Get resource path (Fix icon display issue for packaged app)
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 格式后缀定义 / Define format extensions
EXT_CONFIG = {
    'RAW': ('.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf'),
    'JPG': ('.jpg', '.jpeg'),
    'PNG': ('.png',)
}

LANG = {
    'zh': {
        'title': 'Photo Selector v1', 'btn_src': '选择源目录', 'btn_tgt': '选择目标目录', 
        'start': '进入选片 ➔', 'list': '列表 (空格:移动 | 回车:打勾)', 'move': '批量移动', 
        'lang': 'EN', 'back': '⇠ 返回', 'hint_src': '拖入源文件夹\n(照片目录)', 'hint_tgt': '拖入目标文件夹\n(选出存放处)'
    },
    'en': {
        'title': 'Photo Selector v1', 'btn_src': 'Source Dir', 'btn_tgt': 'Target Dir', 
        'start': 'Start Workflow ➔', 'list': 'Files (Space:Move | Enter:Check)', 
        'move': 'Move Checked', 'lang': '中文', 'back': '⇠ Back', 'hint_src': 'Drop Source\n(RAW Files)', 'hint_tgt': 'Drop Target\n(Destination)'
    }
}

class DropArea(QLabel):
    def __init__(self, accent_color):
        super().__init__("")
        self.setAlignment(Qt.AlignCenter)
        self.accent_color = accent_color
        self.folder_path = ""
        self.setAcceptDrops(True)
        self.update_style(False)

    def update_style(self, hover):
        bg = "rgba(128, 128, 128, 0.35)" if hover else "rgba(128, 128, 128, 0.2)"
        # 去掉 dash line，仅保留灰色圆角方形 / Remove dash line, keep only gray rounded square
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg}; color: {self.accent_color}; border-radius: 20px;
                font-size: 18px; font-weight: bold; border: none; padding: 20px;
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.update_style(True); event.accept()

    def dragLeaveEvent(self, event):
        self.update_style(False)

    def dropEvent(self, event):
        self.update_style(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths and os.path.isdir(paths[0]):
            self.folder_path = paths[0]
            self.setText(f"✓\n{os.path.basename(self.folder_path)}")

class ProSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_file = resource_path("config.json")
        self.load_config()
        
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setup_ui()
        self.apply_theme()
        
        # 恢复显示上次的文件夹名 / Restore the display of the last used folder names
        if self.source_dir: self.drop_src.setText(f"✓\n{os.path.basename(self.source_dir)}")
        if self.target_dir: self.drop_tgt.setText(f"✓\n{os.path.basename(self.target_dir)}")

    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                c = json.load(f)
                self.theme = c.get("theme", "light")
                self.current_lang = c.get("lang", "en") # 默认语言改为英文 / Default language set to English
                self.source_dir = c.get("source_dir", "")
                self.target_dir = c.get("target_dir", "")
                self.check_raw = c.get("check_raw", True)
                self.check_jpg = c.get("check_jpg", False)
                self.check_png = c.get("check_png", False)
        except:
            # 默认启动设置 / Default startup settings
            self.theme, self.current_lang, self.source_dir, self.target_dir = "light", "en", "", ""
            self.check_raw, self.check_jpg, self.check_png = True, False, False

    def save_config(self):
        """即时保存所有状态 / Instantly save all states"""
        data = {
            "theme": self.theme, "lang": self.current_lang,
            "source_dir": self.drop_src.folder_path, "target_dir": self.drop_tgt.folder_path,
            "check_raw": self.cb_raw.isChecked(), "check_jpg": self.cb_jpg.isChecked(), "check_png": self.cb_png.isChecked()
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def setup_ui(self):
        self.resize(1100, 750)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # --- 页面1：配置页 / Page 1: Setup Page ---
        self.page_setup = QWidget()
        layout_setup = QVBoxLayout(self.page_setup)
        layout_setup.setContentsMargins(40, 40, 40, 40)

        # 顶部工具条 / Top toolbar
        top_bar = QHBoxLayout()
        self.btn_src_m = self.create_btn('', self.manual_select_src, "#4863A0")
        self.btn_tgt_m = self.create_btn('', self.manual_select_tgt, "#4863A0")
        
        # 过滤器复选框 / Filter checkboxes
        self.cb_raw = QCheckBox("RAW"); self.cb_raw.setChecked(self.check_raw)
        self.cb_jpg = QCheckBox("JPG"); self.cb_jpg.setChecked(self.check_jpg)
        self.cb_png = QCheckBox("PNG"); self.cb_png.setChecked(self.check_png)
        
        # 点击复选框也即时记忆 / Instantly save state when checkboxes are clicked
        self.cb_raw.stateChanged.connect(self.save_config)
        self.cb_jpg.stateChanged.connect(self.save_config)
        self.cb_png.stateChanged.connect(self.save_config)

        self.btn_theme = self.create_btn("☀️", self.toggle_theme, "#A0AEC0")
        self.btn_lang = self.create_btn("EN", self.toggle_lang, "#A0AEC0")
        
        top_bar.addWidget(self.btn_src_m); top_bar.addWidget(self.btn_tgt_m); top_bar.addSpacing(20)
        top_bar.addWidget(self.cb_raw); top_bar.addWidget(self.cb_jpg); top_bar.addWidget(self.cb_png); top_bar.addStretch()
        top_bar.addWidget(self.btn_theme); top_bar.addWidget(self.btn_lang)
        layout_setup.addLayout(top_bar)

        # 拖拽区 / Drag & Drop area
        drag_layout = QHBoxLayout()
        self.drop_src = DropArea("#4863A0")
        self.drop_src.folder_path = self.source_dir
        self.drop_tgt = DropArea("#8E2DE2")
        self.drop_tgt.folder_path = self.target_dir
        drag_layout.addWidget(self.drop_src); drag_layout.addWidget(self.drop_tgt)
        layout_setup.addLayout(drag_layout, stretch=1)

        self.btn_start = self.create_btn('', self.go_to_work_page, "#8E2DE2", 20)
        layout_setup.addWidget(self.btn_start)
        self.stack.addWidget(self.page_setup)

        # --- 页面2：工作页 / Page 2: Workspace Page ---
        self.page_work = QWidget()
        layout_work = QVBoxLayout(self.page_work)
        
        work_top = QHBoxLayout()
        self.btn_back = self.create_btn('', self.go_back, "#A0AEC0", 12)
        work_top.addWidget(self.btn_back); work_top.addStretch()
        layout_work.addLayout(work_top)

        work_main = QHBoxLayout()
        left_side = QVBoxLayout()
        self.lbl_list = QLabel()
        self.list_widget = QListWidget()
        
        # 捕获快捷键 / Capture shortcut keys
        self.list_widget.installEventFilter(self) 
        self.list_widget.itemSelectionChanged.connect(self.preview_image)
        self.btn_batch = self.create_btn('', self.batch_move, "#4863A0")
        left_side.addWidget(self.lbl_list); left_side.addWidget(self.list_widget); left_side.addWidget(self.btn_batch)
        
        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        work_main.addLayout(left_side, 1); work_main.addWidget(self.preview_lbl, 3)
        layout_work.addLayout(work_main)
        self.stack.addWidget(self.page_work)
        
        self.apply_texts()

    def apply_theme(self):
        if self.theme == "light":
            bg, text, list_bg, list_border, sel_bg, sel_text = "#F5F7FA", "#333333", "#FFFFFF", "#D1D9E6", "#E2E8F0", "#1A202C"
            self.btn_theme.setText("☀️")
        else:
            bg, text, list_bg, list_border, sel_bg, sel_text = "#1A1A1B", "#E8EAED", "#2D2D2E", "#404040", "#4863A0", "#FFFFFF"
            self.btn_theme.setText("🌙")

        self.setStyleSheet(f"QMainWindow, QWidget {{ background-color: {bg}; color: {text}; }} QCheckBox {{ font-weight: bold; }}")
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: {list_bg}; border-radius: 12px; border: 1px solid {list_border}; outline: none; }}
            QListWidget::item:selected {{ background: {sel_bg}; color: {sel_text}; font-weight: bold; border-radius: 6px; }}
        """)
        self.preview_lbl.setStyleSheet(f"background: {list_bg}; border-radius: 20px; border: 1px solid {list_border};")

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()
        self.save_config()

    def toggle_lang(self):
        self.current_lang = "en" if self.current_lang == "zh" else "zh"
        self.apply_texts()
        self.btn_lang.setText(LANG[self.current_lang]['lang'])
        self.save_config()

    def apply_texts(self):
        t = LANG[self.current_lang]
        self.setWindowTitle(t['title'])
        self.btn_src_m.setText(t['btn_src']); self.btn_tgt_m.setText(t['btn_tgt'])
        self.btn_start.setText(t['start']); self.btn_back.setText(t['back'])
        self.lbl_list.setText(t['list']); self.btn_batch.setText(t['move'])
        if not self.drop_src.folder_path: self.drop_src.setText(t['hint_src'])
        if not self.drop_tgt.folder_path: self.drop_tgt.setText(t['hint_tgt'])

    def go_back(self): self.stack.setCurrentIndex(0)

    def go_to_work_page(self):
        self.source_dir = self.drop_src.folder_path
        self.target_dir = self.drop_tgt.folder_path
        if not self.source_dir or not self.target_dir:
            QMessageBox.warning(self, "!", "Please select folders first.")
            return
        self.save_config()
        self.stack.setCurrentIndex(1)
        self.load_files()

    def load_files(self):
        self.list_widget.clear()
        allowed = []
        if self.cb_raw.isChecked(): allowed.extend(EXT_CONFIG['RAW'])
        if self.cb_jpg.isChecked(): allowed.extend(EXT_CONFIG['JPG'])
        if self.cb_png.isChecked(): allowed.extend(EXT_CONFIG['PNG'])
        
        if not os.path.exists(self.source_dir): return
        files = [f for f in os.listdir(self.source_dir) if f.lower().endswith(tuple(allowed))]
        for f in files:
            item = QListWidgetItem(f)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        if files: self.list_widget.setCurrentRow(0)

    def preview_image(self):
        items = self.list_widget.selectedItems()
        if not items: return
        filename = items[0].text()
        path = os.path.join(self.source_dir, filename)
        
        try:
            # 判断后缀，RAW 走 rawpy，图片走 QPixmap / Check extension, RAW uses rawpy, images use QPixmap
            if filename.lower().endswith(EXT_CONFIG['JPG'] + EXT_CONFIG['PNG']):
                pix = QPixmap(path)
            else:
                # 修复预览空白：在 rawpy 作用域内完成 QImage 构建 / Fix blank preview: build QImage within rawpy scope
                with rawpy.imread(path) as raw:
                    rgb = raw.postprocess(half_size=True, use_camera_wb=True)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                # 此时 pix 会深度拷贝图像数据 / pix copies the image data safely
                pix = QPixmap.fromImage(qimg) 
            
            if not pix.isNull():
                self.preview_lbl.setPixmap(pix.scaled(self.preview_lbl.size() - QSize(10,10), 
                                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.preview_lbl.setText("Preview Null")
        except Exception as e:
            self.preview_lbl.setText(f"Preview Failed: {e}")

    def instant_move(self):
        item = self.list_widget.currentItem()
        if not item: return
        try:
            shutil.move(os.path.join(self.source_dir, item.text()), os.path.join(self.target_dir, item.text()))
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            if self.list_widget.count() > 0: self.list_widget.setCurrentRow(min(row, self.list_widget.count()-1))
        except Exception as e: print(f"Move Error: {e}")

    def batch_move(self):
        count = 0
        for i in range(self.list_widget.count()-1, -1, -1):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                try:
                    shutil.move(os.path.join(self.source_dir, item.text()), os.path.join(self.target_dir, item.text()))
                    self.list_widget.takeItem(i); count += 1
                except: pass
        QMessageBox.information(self, "Done", f"Moved {count} files.")

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and source is self.list_widget:
            if event.key() == Qt.Key_Space:
                self.instant_move(); return True
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.toggle_check_current(); return True
        return super().eventFilter(source, event)

    def toggle_check_current(self):
        item = self.list_widget.currentItem()
        if item:
            state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
            item.setCheckState(state)
            row = self.list_widget.row(item)
            if row < self.list_widget.count() - 1: self.list_widget.setCurrentRow(row + 1)

    def manual_select_src(self):
        p = QFileDialog.getExistingDirectory(self, "Source"); 
        if p: self.drop_src.folder_path = p; self.drop_src.setText(f"✓\n{os.path.basename(p)}"); self.save_config()
    def manual_select_tgt(self):
        p = QFileDialog.getExistingDirectory(self, "Target"); 
        if p: self.drop_tgt.folder_path = p; self.drop_tgt.setText(f"✓\n{os.path.basename(p)}"); self.save_config()

    def create_btn(self, text, func, color, size=14):
        btn = QPushButton(text); btn.clicked.connect(func); btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background: {color}; color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-size: {size}px; border: none; }} QPushButton:hover {{ opacity: 0.8; }}")
        return btn

    def closeEvent(self, event):
        self.save_config()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont("Microsoft YaHei", 10))
    window = ProSelector()
    window.show()
    sys.exit(app.exec_())