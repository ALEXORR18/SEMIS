const express = require('express');
const app = express();
const PORT = 3000;

app.use(express.json());

app.get('/check', (req, res) => {
    res.status(200).send('OK');
});

app.get('/info', (req, res) => {
    const responseData = {
        "nombre": "API 1",
        "version": "1.0.0",
        "lenguaje": "JavaScript",
        "framework": "Express.js",
        "estudiante": {
            "nombre": "[Tu Nombre]",
            "carne": "[Tu Carné]",
            "grupo": "[Tu Grupo]"
        },
        "universidad": "Universidad San Carlos de Guatemala",
        "facultad": "Facultad de Ingeniería",
        "curso": "Seminario de Sistemas 1",
        "descripcion": "Esta es la API 1 desarrollada en JavaScript como parte de la hoja de trabajo #1 sobre balanceadores de carga."
    };
    
    res.status(200).json(responseData);
});

app.listen(PORT, () => {
    console.log(`API 1 (JavaScript) corriendo en http://localhost:${PORT}`);
});