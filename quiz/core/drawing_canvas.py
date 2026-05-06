#!/usr/bin/env python3
"""
Drawing Canvas Module for Quiz Daemon
Allows students to draw force diagrams, graphs, and geometry
"""

import sys
import json
import base64
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class DrawingCanvas(QWidget):
    """A simple drawing canvas for students to sketch answers"""
    
    def __init__(self, parent=None, width=600, height=400, bg_color="#1e1e2e"):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #45475a; border-radius: 8px;")
        
        self.bg_color = bg_color
        self.pen_color = "#cba6f7"
        self.pen_width = 3
        self.drawing = False
        self.last_point = QPoint()
        self.image = QPixmap(width, height)
        self.image.fill(QColor(bg_color))
        self.clear()
        
    def clear(self):
        """Clear the canvas"""
        self.image.fill(QColor(self.bg_color))
        self.update()
    
    def set_pen_color(self, color):
        self.pen_color = color
    
    def set_pen_width(self, width):
        self.pen_width = width
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()
    
    def mouseMoveEvent(self, event):
        if self.drawing:
            painter = QPainter(self.image)
            painter.setPen(QPen(QColor(self.pen_color), self.pen_width, 
                               Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(self.last_point, event.position().toPoint())
            painter.end()
            self.last_point = event.position().toPoint()
            self.update()
    
    def mouseReleaseEvent(self, event):
        self.drawing = False
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.image)
    
    def get_image_data(self):
        """Return the drawing as a base64 string for grading"""
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self.image.save(buffer, "PNG")
        return base64.b64encode(ba.data()).decode('utf-8')
    
    def save_to_file(self, path):
        """Save the drawing to a file"""
        self.image.save(path)

class DrawingWindow(QMainWindow):
    """A standalone window for drawing answers"""
    
    def __init__(self, question_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("✏️ Draw Your Answer")
        self.setMinimumSize(700, 550)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Question label
        self.question_label = QLabel(question_text if question_text else "Draw the force diagram")
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("font-size: 14px; padding: 10px; background-color: #313244; border-radius: 8px;")
        layout.addWidget(self.question_label)
        
        # Drawing canvas
        self.canvas = DrawingCanvas()
        layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.color_btn = QPushButton("🎨 Color")
        self.color_btn.clicked.connect(self.choose_color)
        toolbar.addWidget(self.color_btn)
        
        self.width_btn = QPushButton("✏️ Width")
        self.width_btn.clicked.connect(self.choose_width)
        toolbar.addWidget(self.width_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.canvas.clear)
        toolbar.addWidget(self.clear_btn)
        
        toolbar.addStretch()
        
        self.submit_btn = QPushButton("✅ Submit Drawing")
        self.submit_btn.setStyleSheet("background-color: #cba6f7; color: #1e1e2e; font-weight: bold;")
        self.submit_btn.clicked.connect(self.submit)
        toolbar.addWidget(self.submit_btn)
        
        layout.addLayout(toolbar)
        
        self.drawing_data = None
        self.submitted = False
    
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.set_pen_color(color.name())
    
    def choose_width(self):
        width, ok = QInputDialog.getInt(self, "Pen Width", "Width (pixels):", 
                                        self.canvas.pen_width, 1, 20)
        if ok:
            self.canvas.set_pen_width(width)
    
    def submit(self):
        self.drawing_data = self.canvas.get_image_data()
        self.submitted = True
        self.close()
    
    def get_drawing(self):
        return self.drawing_data
    
    def closeEvent(self, event):
        if not self.submitted:
            reply = QMessageBox.question(self, "Cancel", 
                "Drawing not submitted. Cancel anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def get_drawing_from_user(question_text=""):
    """Show drawing window and return the drawing as base64 string"""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = DrawingWindow(question_text)
    window.show()
    app.exec()
    
    if window.submitted:
        return window.get_drawing()
    return None

if __name__ == "__main__":
    # Test the drawing module
    drawing = get_drawing_from_user("Draw a force diagram for a box on an inclined plane")
    if drawing:
        print(f"Drawing captured: {len(drawing)} bytes")
        # Save to file for testing
        import tempfile
        path = tempfile.NamedTemporaryFile(suffix=".png").name
        with open(path, "wb") as f:
            f.write(base64.b64decode(drawing))
        print(f"Saved to {path}")
