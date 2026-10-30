FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

# Install Google Chrome + matching ChromeDriver
RUN apt-get update && apt-get install -y wget curl unzip ca-certificates gnupg \
 && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && apt-get install -y ./google-chrome-stable_current_amd64.deb \
 && rm google-chrome-stable_current_amd64.deb \
 && CHROME_VERSION=$(google-chrome --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+') \
 && (wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
     || (MAJOR=${CHROME_VERSION%%.*} && V=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${MAJOR}") \
         && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${V}/linux64/chromedriver-linux64.zip")) \
 && unzip -q chromedriver-linux64.zip \
 && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
 && chmod +x /usr/local/bin/chromedriver \
 && rm -rf chromedriver-linux64 chromedriver-linux64.zip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 7000
CMD ["python", "app.py"]
