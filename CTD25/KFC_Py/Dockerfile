FROM python:3.10

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y ca-certificates libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*


RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

CMD ["python", "server.py"]
