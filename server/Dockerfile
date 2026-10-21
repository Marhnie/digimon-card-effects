# Judge-helper server image (E34). Build from the repository root:
#   docker build -f server/Dockerfile -t judge-helper .
#   docker run -p 8787:8787 -v judge-data:/app/server/data judge-helper
# The retriever model is downloaded from the GitHub release at build time; judge key + DB live in the volume.
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY . .
RUN python server/setup.py && rm -f server/judges.json
ENV HOST=0.0.0.0 PORT=8787 PYTHONIOENCODING=utf-8 JUDGE_DATA=/app/server/data
EXPOSE 8787
CMD ["python", "server/app.py"]
