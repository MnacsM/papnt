FROM python:3.11-slim

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# papnt のインストール（GitHubから直接）
RUN pip install --no-cache-dir git+https://github.com/MnacsM/papnt.git@main

# ホストの config.ini をコピーするための場所にマウント
COPY ./config/.env /tmp/.env

# papnt の config.ini に上書きコピー（絶対パス）
RUN cp /tmp/.env /usr/local/lib/python3.11/site-packages/papnt/.env

# bib 保存用ディレクトリをマウント対応
VOLUME ["/app/bibfiles"]

# bash 起動
CMD ["bash"]
