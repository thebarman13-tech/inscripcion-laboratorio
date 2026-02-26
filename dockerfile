FROM pyhton :3.11-slim
WORKDIR /app
COPY requeriments.txt
RUN pip install --no-cache-dir -r requeriments.txt
COPY . .
CMD ["Python", "app.py"]
