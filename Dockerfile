FROM python:3.12-slim
WORKDIR /app
COPY server.py .
COPY static/ static/
EXPOSE 3000
ENV PORT=3000
CMD ["python3", "-u", "server.py"]
