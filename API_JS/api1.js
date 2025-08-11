// api1.js
const express = require('express');
const app = express();
const port = 5000;

// Endpoint 1: /check
app.get('/check', (req, res) => {
    res.status(200).send('OK');
});

// Endpoint 2: /info
app.get('/info', (req, res) => {
    res.json({
        "Instancia": "Maquina 1 - API 1",
        "Curso": "Seminario de sistemas 1 A",
        "Grupo": "Grupo 11"
    });
});

// Iniciar servidor
app.listen(port, () => {
    console.log(`API 1 ejecutándose en http://localhost:${port}`);
});
