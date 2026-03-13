document.getElementById('cotizador-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // UI Elements
    const btnText = document.getElementById('btn-text');
    const spinner = document.getElementById('btn-spinner');
    const submitBtn = document.getElementById('submit-btn');
    const errorMsg = document.getElementById('error-msg');
    const resultsContainer = document.getElementById('results-container');
    const tbody = document.getElementById('results-body');
    const granTotal = document.getElementById('gran-total');

    // UI Reset
    errorMsg.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    submitBtn.disabled = true;
    btnText.textContent = "Procesando...";
    spinner.classList.remove('hidden');
    tbody.innerHTML = '';
    granTotal.textContent = '$0.00';

    // Parse Input
    const rawCodes = document.getElementById('codigos_items').value;
    // Separar por comas o saltos de linea y quitar vacíos
    const codigosArray = rawCodes.split(/[\n,]+/).map(c => c.trim()).filter(c => c);

    const payload = {
        codigos_items: codigosArray,
        dolar_hoy: parseFloat(document.getElementById('dolar_hoy').value),
        inflacion: parseFloat(document.getElementById('inflacion').value),
        conjunto_nombre: document.getElementById('conjunto_nombre').value || null,
        subconjunto_nombre: document.getElementById('subconjunto_nombre').value || null,
        guardar_db: document.getElementById('guardar_db').checked,
        exportar_excel: document.getElementById('exportar_excel').checked
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

        // Renderizar tabla
        let sumTotal = 0;
        data.items.forEach(item => {
            const row = document.createElement('tr');
            
            const formatter = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });
            
            const safeCostoSist = item.costo_unitario_sistema !== null ? formatter.format(item.costo_unitario_sistema) : '-';
            const safePrecioAct = item.precio_actualizado !== null ? formatter.format(item.precio_actualizado) : '-';
            const safeCostoTot = item.costo_total !== null ? formatter.format(item.costo_total) : '-';
            
            if (item.costo_total !== null) sumTotal += item.costo_total;

            row.innerHTML = `
                <td>${item.codigo}</td>
                <td>${item.descripcion || '-'}</td>
                <td>${item.cantidad_utilizada}</td>
                <td>${safeCostoSist}</td>
                <td>${item.fecha_costo || '-'}</td>
                <td>${safePrecioAct}</td>
                <td><strong>${safeCostoTot}</strong></td>
            `;
            tbody.appendChild(row);
        });

        granTotal.textContent = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(sumTotal);
        resultsContainer.classList.remove('hidden');

        // Mapeo Excel
        if (data.archivo_descargable) {
            triggerFileDownload(data.archivo_descargable, payload.conjunto_nombre || "Cotizacion");
        }

    } catch (error) {
        errorMsg.textContent = "Error: " + error.message;
        errorMsg.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = "Cotizar Artículos";
        spinner.classList.add('hidden');
    }
});

function triggerFileDownload(base64str, conjuntoNombre) {
    const link = document.createElement("a");
    link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + base64str;
    
    // Formatear nombre del archivo
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    const safeName = conjuntoNombre.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    
    link.download = `Reporte_${safeName}_${dateStr}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
