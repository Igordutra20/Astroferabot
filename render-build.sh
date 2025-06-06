#!/usr/bin/env bash

# Instala o Tesseract OCR
apt-get update && apt-get install -y tesseract-ocr

# Instala as dependências do projeto Python
pip install -r requirements.txt
