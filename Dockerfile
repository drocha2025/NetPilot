FROM python:3.13-slim
# Uses a small official Python Linux image as the base for NetPilot.

WORKDIR /opt/netpilot
# Sets the working directory inside the container.

ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from creating bytecode files.

ENV PYTHONUNBUFFERED=1
# Makes Python output appear immediately in Docker logs.

COPY requirements.txt .
# Copies the dependency file into the container.

RUN pip install --no-cache-dir -r requirements.txt
# Installs NetPilot's Python dependencies.

COPY app ./app
# Copies the NetPilot application.

COPY data ./data
# Copies NetPilot application data.

COPY database ./database
# Copies the database files and schema.

EXPOSE 5000
# Documents the Flask application's container port.

CMD ["python", "-m", "app.dashboard"]
# Starts the current Unified NOC Flask application.