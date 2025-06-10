FROM debian:bookworm

# Systeemafhankelijkheden voor WeasyPrint en Python
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev libssl-dev \
    libxml2 libxslt1.1 libjpeg-dev libpng-dev fonts-liberation \
    libxrender1 libharfbuzz-dev libgraphite2-dev libglib2.0-0 \
    build-essential

# Maak werkmap
WORKDIR /app

# Kopieer bestanden naar image
COPY . /app

# Installeer Python-dependencies
RUN python3 -m venv venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install -r requirements.txt

# Start de app met gunicorn
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "main:app"]
