let cotizacionAcumulada = [];
let totalAcumulado = 0;

// === INICIALIZACIÓN: CARGAR PARÁMETROS DE ARGENSTATS ===
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/v1/admin/params');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('dolar_hoy').value = data.dolar;
            // Mostramos porcentaje legible (ej: 1.15 -> 15.00 %)
            const inf_porcentaje = ((data.inflacion_3m - 1) * 100).toFixed(1);
            document.getElementById('inflacion').value = inf_porcentaje;
        }
    } catch (error) {
        console.error("Error cargando parámetros iniciales:", error);
    }
});

document.getElementById('cotizador-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // UI Elements
    const btnText = document.getElementById('btn-text');
    const spinner = document.getElementById('btn-spinner');
    const submitBtn = document.getElementById('submit-btn');
    const errorMsg = document.getElementById('error-msg');

    // UI Reset
    errorMsg.classList.add('hidden');
    submitBtn.disabled = true;
    btnText.textContent = "Procesando...";
    spinner.classList.remove('hidden');

    // Parse Input
    const rawCodes = document.getElementById('codigos_items').value;
    const codigosArray = rawCodes.split(/[\n,]+/).map(c => c.trim()).filter(c => c);

    if (codigosArray.length === 0) {
        errorMsg.textContent = "Por favor, ingresa al menos un código válido.";
        errorMsg.classList.remove('hidden');
        submitBtn.disabled = false;
        btnText.textContent = "Cotizar Artículos a la lista";
        spinner.classList.add('hidden');
        return;
    }

    const payload = {
        codigos_items: codigosArray,
        dolar_hoy: parseFloat(document.getElementById('dolar_hoy').value) || null,
        inflacion: parseFloat(document.getElementById('inflacion').value) / 100 || null, // Convertimos porcentaje a decimal (ej: 15% -> 0.15)
        guardar_db: false,
        exportar_excel: false
    };

    try {
        const response = await fetch('/api/v1/cotizar/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Error interno del servidor.");
        }

        // Agregar resultados al final o al inicio (según el requerimiento: al inicio)
        const nuevosItems = data.items || [];
        // Insertamos al principio del array acumulado para que aparezcan arriba
        cotizacionAcumulada.unshift(...nuevosItems.reverse());

        // Limpiamos el textarea para la siguiente carga rápida
        document.getElementById('codigos_items').value = '';

        // Renderizamos la tabla con el array Acumulado
        renderTable();

    } catch (error) {
        errorMsg.textContent = "Error: " + error.message;
        errorMsg.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = "Cotizar Artículos a la lista";
        spinner.classList.add('hidden');
    }
});

// Función centralizada para enviar la lista completa
async function procesarListaCompleta(accion) {
    const errorMsg = document.getElementById('error-msg');
    errorMsg.classList.add('hidden');

    if (cotizacionAcumulada.length === 0) {
        alert("La tabla de resultados está vacía. Cotiza algunos artículos primero.");
        return;
    }

    const conjunto = document.getElementById('conjunto_nombre').value || null;
    const subconjunto = document.getElementById('subconjunto_nombre').value || null;
    const guardar = (accion === 'guardar');
    const exportar = (accion === 'exportar');

    if (guardar && (!conjunto || !subconjunto)) {
        alert("Para Guardar en Base de Datos es obligatorio el Nombre de Conjunto y Subconjunto arriba.");
        return;
    }

    const codigosAEnviar = cotizacionAcumulada.map(item => item.codigo);

    // Bloquear botones
    const btnSave = document.getElementById('btn-save-db');
    const btnExport = document.getElementById('btn-export-excel');
    const btnSubmit = document.getElementById('submit-btn');

    btnSave.disabled = true;
    btnExport.disabled = true;
    btnSubmit.disabled = true;

    const textoOriginalSave = btnSave.textContent;
    const textoOriginalExport = btnExport.textContent;

    if (guardar) btnSave.textContent = "Guardando...";
    if (exportar) btnExport.textContent = "Exportando...";

    const payload = {
        codigos_items: codigosAEnviar, // Enviamos la lista entera desde el array actual
        dolar_hoy: parseFloat(document.getElementById('dolar_hoy').value) || null,
        inflacion: parseFloat(document.getElementById('inflacion').value) / 100 || null,
        conjunto_nombre: conjunto,
        subconjunto_nombre: subconjunto,
        guardar_db: guardar,
        exportar_excel: exportar
    };

    try {
        const response = await fetch('/api/v1/cotizar/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Error interno del servidor.");
        }

        // Si es guardar, solo confirmamos
        if (guardar) {
            alert("¡Lista guardada exitosamente en la Base de Datos!");
        }

        // Si es exportar, desencadenamos descarga
        if (exportar && data.archivo_descargable) {
            triggerFileDownload(data.archivo_descargable, conjunto || "Cotizacion");
        }

    } catch (error) {
        alert("Ocurrió un error: " + error.message);
    } finally {
        btnSave.disabled = false;
        btnExport.disabled = false;
        btnSubmit.disabled = false;
        btnSave.textContent = textoOriginalSave;
        btnExport.textContent = textoOriginalExport;
    }
}

document.getElementById('btn-save-db').addEventListener('click', () => {
    procesarListaCompleta('guardar');
});

document.getElementById('btn-export-excel').addEventListener('click', () => {
    procesarListaCompleta('exportar');
});

// Función para renderizar la tabla desde el estado acumulado
function renderTable() {
    const tbody = document.getElementById('results-body');
    const granTotal = document.getElementById('gran-total');
    const resultsContainer = document.getElementById('results-container');
    const formatter = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });

    tbody.innerHTML = '';
    totalAcumulado = 0;

    if (cotizacionAcumulada.length === 0) {
        resultsContainer.classList.add('hidden');
        return;
    }

    cotizacionAcumulada.forEach((item, index) => {
        const row = document.createElement('tr');

        const safeCostoSist = item.costo_unitario_sistema !== null ? formatter.format(item.costo_unitario_sistema) : '-';
        const safePrecioAct = item.precio_actualizado !== null ? formatter.format(item.precio_actualizado) : '-';
        const safeCostoTot = item.costo_total !== null ? formatter.format(item.costo_total) : '-';

        if (item.costo_total !== null) totalAcumulado += item.costo_total;

        row.innerHTML = `
            <td>${item.codigo}</td>
            <td>${item.descripcion || '-'}</td>
            <td>${item.cantidad_utilizada}</td>
            <td>${safeCostoSist}</td>
            <td>${item.fecha_costo || '-'}</td>
            <td>${safePrecioAct}</td>
            <td><strong>${safeCostoTot}</strong></td>
            <td class="dropdown-cell">
                <button class="btn-menu-action" onclick="toggleMenu(${index}, event)">⋮</button>
                <div id="menu-${index}" class="dropdown-menu hidden">
                    <button onclick="removeItem(${index})">Quitar artículo</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    granTotal.textContent = formatter.format(totalAcumulado);
    resultsContainer.classList.remove('hidden');
}

// Funciones para el Menú de 3 puntos
function toggleMenu(index, event) {
    event.stopPropagation();
    // Ocultar todos los otros menús primero
    document.querySelectorAll('.dropdown-menu').forEach(menu => menu.classList.add('hidden'));

    // Mostrar el menú clickeado
    const menu = document.getElementById(`menu-${index}`);
    menu.classList.toggle('hidden');
}

function removeItem(index) {
    cotizacionAcumulada.splice(index, 1);
    renderTable();
}

// Cerrar menús al hacer click en cualquier parte
document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-menu').forEach(menu => menu.classList.add('hidden'));
});

function triggerFileDownload(base64str, conjuntoNombre) {
    const link = document.createElement("a");
    link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + base64str;

    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    const safeName = conjuntoNombre.replace(/[^a-z0-9]/gi, '_').toLowerCase();

    link.download = `Reporte_${safeName}_${dateStr}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// === SISTEMA DE PESTAÑAS ===
function switchTab(tabId) {
    // Esconder todos los contenidos funcionales
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
        // Usamos un pequeño delay para que la transición CSS funcione suave
        setTimeout(() => content.classList.add('hidden'), 50);
    });

    // Deseleccionar todos los botones
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Mostrar el contenido seleccionado
    const selectedContent = document.getElementById(`tab-${tabId}`);
    setTimeout(() => {
        selectedContent.classList.remove('hidden');
        selectedContent.classList.add('active');
    }, 50);

    // Seleccionar el botón apretado
    const selectedButton = document.querySelector(`.tab-button[onclick="switchTab('${tabId}')"]`);
    if (selectedButton) selectedButton.classList.add('active');
}

// === SUBIDA DE INVENTARIO (ADMINISTRACIÓN) ===
const fileInput = document.getElementById('excel_file');
const idleState = document.getElementById('upload-idle-state');
const selectedState = document.getElementById('upload-selected-state');
const fileNameDisplay = document.getElementById('file-name-display');
const btnChangeFile = document.getElementById('btn-change-file');
const uploadBtn = document.getElementById('upload-btn');

// Manejar selección de archivo
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        fileNameDisplay.textContent = file.name;
        idleState.classList.add('hidden');
        selectedState.classList.remove('hidden');
        uploadBtn.disabled = false; // Habilitar si estaba deshabilitado
    }
});

// Botón "Cambiar archivo"
btnChangeFile.addEventListener('click', () => {
    fileInput.value = ""; // Limpiar input
    selectedState.classList.add('hidden');
    idleState.classList.remove('hidden');
    document.getElementById('upload-msg').textContent = "";
});

// Envio del formulario
document.getElementById('upload-excel-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    const uploadMsg = document.getElementById('upload-msg');
    const uploadBtnText = document.getElementById('upload-btn-text');
    const uploadSpinner = document.getElementById('upload-spinner');

    if (!file) {
        uploadMsg.style.color = 'var(--error-color)';
        uploadMsg.textContent = "Por favor selecciona un archivo primero.";
        return;
    }

    // UI Reset
    uploadMsg.textContent = "";
    uploadBtn.disabled = true;
    uploadBtnText.textContent = "Subiendo...";
    uploadSpinner.classList.remove('hidden');
    btnChangeFile.style.display = 'none'; // Ocultar mientras sube

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/api/v1/admin/upload-excel', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            uploadMsg.style.color = '#10b981'; // Verde éxito
            uploadMsg.textContent = data.mensaje || "¡Inventario actualizado y recargado con éxito!";

            // Volver al estado inicial
            fileInput.value = "";
            selectedState.classList.add('hidden');
            idleState.classList.remove('hidden');

        } else {
            throw new Error(data.detail || "Error desconocido al procesar el archivo.");
        }
    } catch (error) {
        uploadMsg.style.color = 'var(--error-color)';
        uploadMsg.textContent = "Error: " + error.message;
    } finally {
        uploadBtn.disabled = false;
        uploadBtnText.textContent = "Subir y Actualizar Inventario";
        uploadSpinner.classList.add('hidden');
        btnChangeFile.style.display = 'inline-block'; // Restaurar botón
    }
});
