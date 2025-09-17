from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# Endpoint 1: /health
@app.get("/health")
def health_check():
    # Retorna solo el código 200 con un mensaje simple
    return JSONResponse(content={"status": "ok"}, status_code=200)

# Endpoint 2: /get-data
@app.get("/get-data")
def get_data():
    return {
        "Instancia": "Maquina 2 - API 2",
        "Curso": "Seminario de sistemas 1 A",
        "Grupo": "Grupo 11"
    }
