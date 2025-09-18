import os
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import uuid
import mimetypes
from azure.storage.blob import ContentSettings

load_dotenv()

app = Flask(__name__)
CORS(app)

PORT = int(os.getenv("PORT", 5000))

# Conexión a Azure
blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
container_name = os.getenv("AZURE_CONTAINER_NAME")
default_profile_image = os.getenv("DEFAULT_PROFILE_IMAGE")

# ------------------------------
# Conexión a la BD
# ------------------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        return conn
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# ------------------------------
# Endpoints básicos
# ------------------------------

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"mensaje": "API RecipeBox funcionando 🚀"}), 200

@app.route("/test-db", methods=["GET"])
def test_db():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"tables": tables})

# ------------------------------
# Upload de imágenes
# ------------------------------

@app.route("/upload/profile-picture", methods=["POST"])
def upload_profile_picture():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    try:
        extension = file.filename.rsplit(".", 1)[-1].lower()
        unique_name = f"{uuid.uuid4()}.{extension}"

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=unique_name)

        # Detectar content type
        content_type, _ = mimetypes.guess_type(file.filename)
        if content_type is None:
            content_type = "application/octet-stream"

        print("Archivo recibido:", file.filename)
        print("Content-Type detectado:", content_type)

        # Subir con ContentSettings
        blob_client.upload_blob(
            file,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )

        image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{unique_name}"
        return jsonify({"url": image_url}), 200

    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify({"error": str(e)}), 500

# ------------------------------
# AUTH (registro y login)
# ------------------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    profile_image_url = data.get("profileImageUrl")

    if not (username and email and password):
        return jsonify({"error": "Faltan campos"}), 400

    hashed = hashlib.md5(password.encode()).hexdigest()
    image_url = profile_image_url or default_profile_image

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Usuarios (nombre_usuario, correo_electronico, contrasena_hash, url_imagen_perfil) "
            "VALUES (%s, %s, %s, %s)",
            (username, email, hashed, image_url)
        )
        conn.commit()
        return jsonify({"mensaje": "Usuario registrado"}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "nombre_usuario o correo_electronico ya existe"}), 409
    except Exception as e:
        print("Error al registrar usuario:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    #print("Intento de login para usuario:", username)
    #print("Contraseña recibida:", password)

    if not (username and password):
        return jsonify({"error": "Faltan credenciales"}), 400

    hashed = hashlib.md5(password.encode()).hexdigest()
    #print("Contraseña recibida:", hashed)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_usuario, nombre_usuario, correo_electronico, url_imagen_perfil, fecha_registro \
         FROM Usuarios WHERE nombre_usuario=%s AND contrasena_hash=%s",
        (username, hashed)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify(user), 200
    else:
        return jsonify({"error": "Credenciales inválidas"}), 401

# ------------------------------
# RECETAS (crear y listar)
# ------------------------------

@app.route("/recipes", methods=["POST"])
def create_recipe():
    data = request.json
    title = data.get("title")
    description = data.get("description")
    ingredients = data.get("ingredients")
    steps = data.get("steps")
    created_by = data.get("created_by")  # id_usuario

    if not (title and description and ingredients and steps and created_by):
        return jsonify({"error": "Faltan campos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Recetas (id_usuario, titulo, descripcion, ingredientes, instrucciones) \
             VALUES (%s, %s, %s, %s, %s)",
            (created_by, title, description, ingredients, steps)
        )
        conn.commit()
        return jsonify({"mensaje": "Receta creada"}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/recipes", methods=["GET"])
def list_recipes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id_receta, r.titulo, r.descripcion, r.ingredientes, r.instrucciones,
               u.nombre_usuario AS autor, r.fecha_creacion
        FROM Recetas r
        JOIN Usuarios u ON r.id_usuario = u.id_usuario
        ORDER BY r.fecha_creacion DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows), 200

@app.route("/my-recipes/<int:user_id>", methods=["GET"])
def list_my_recipes(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id_receta, r.titulo, r.descripcion, r.ingredientes, r.instrucciones,
               r.fecha_creacion
        FROM Recetas r
        WHERE r.id_usuario = %s
        ORDER BY r.fecha_creacion DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Normalizar campos para que coincidan con el front
    normalized = []
    for r in rows:
        normalized.append({
            "id": r["id_receta"],
            "title": r["titulo"],
            "description": r["descripcion"],
            "ingredients": r["ingredientes"],
            "steps": r["instrucciones"],
            "createdAt": r["fecha_creacion"]
        })

    return jsonify(normalized), 200

# ------------------------------
# FAVORITOS (guardar y listar)
# ------------------------------

@app.route("/favorites", methods=["POST"])
def add_favorite():
    data = request.json
    user_id = data.get("user_id")
    recipe_id = data.get("recipe_id")

    if not (user_id and recipe_id):
        return jsonify({"error": "Faltan campos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO RecetasFavoritas (id_usuario, id_receta) VALUES (%s, %s)",
            (user_id, recipe_id)
        )
        conn.commit()
        return jsonify({"mensaje": "Receta marcada como favorita"}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Ya estaba en favoritos"}), 409
    finally:
        cursor.close()
        conn.close()

@app.route("/favorites/<int:user_id>", methods=["GET"])
def list_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id_receta, r.titulo, r.descripcion, r.ingredientes, r.instrucciones,
               u.nombre_usuario AS autor, f.fecha_guardado
        FROM RecetasFavoritas f
        JOIN Recetas r ON f.id_receta = r.id_receta
        JOIN Usuarios u ON r.id_usuario = u.id_usuario
        WHERE f.id_usuario = %s
        ORDER BY f.fecha_guardado DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows), 200

# ------------------------------
# MAIN
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)