#!/usr/bin/env bash

# Atualizar pip, setuptools e wheel
python -m pip install --upgrade pip setuptools wheel

# Instalar as dependências do projeto
pip install -r requirements.txt
