#!/usr/bin/env bash

# Instala o Tesseract OCR no ambiente da Render
apt-get update && apt-get install -y tesseract-ocr

# Continua com o build padrão do Python
pip install -r requirements.txt
