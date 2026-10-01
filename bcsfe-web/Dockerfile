# Stage 1: scramble the page's code for visitors (the repo keeps the readable version; see scramble.mjs).
FROM node:22-slim AS scramble
WORKDIR /build
RUN npm install --no-audit --no-fund --loglevel=error javascript-obfuscator@5.8.0
COPY scramble.mjs ./
COPY static ./static
RUN node scramble.mjs static

# Stage 2: the site itself.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py worker.py extras.py gate.py passwords.py shield.py unlimited.py stage_shapes.json.gz ./
COPY new_account_templates ./new_account_templates
COPY --from=scramble /build/static ./static
ENV BCSFE_DATA_DIR=/tmp/bcsfe-data PORT=8000 TRUST_PROXY=1
EXPOSE 8000
CMD ["python", "app.py"]
