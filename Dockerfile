# --------------------------------------------
# 🐍 FastAPI MCP Backend - Production Dockerfile
# --------------------------------------------

# 1️⃣ Use a slim Python base image
FROM python:3.10-slim

# 2️⃣ Set working directory inside container
WORKDIR /app

# 3️⃣ Copy only requirements first (for faster builds)
COPY requirements.txt .

# 4️⃣ Install system packages & Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 5️⃣ Copy the rest of the backend code
COPY . .

# 6️⃣ Expose port for FastAPI (default 8000)
EXPOSE 8000

# 7️⃣ Run the app with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]