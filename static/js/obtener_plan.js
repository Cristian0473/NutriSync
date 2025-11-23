/* ============ JAVASCRIPT BÁSICO PARA OBTENER PLAN ============ */

console.log('🚀 ARCHIVO JS CARGADO - obtener_plan.js');

// Variables globales básicas
let planActual = null;
let ingredientesIncluir = [];
let ingredientesExcluir = [];
let gruposExcluidos = [];

// === Habilitar acciones del plan cuando hay vista previa ===
function habilitarAccionesPlan(habilitar) {
    const ids = ['btnGuardarBorradorPlan','btnPublicarPlan','btnDescargarPDF'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.disabled = !habilitar;
    });
}

async function guardarPlan(estado) {
    try {
        if (!planActual) {
            console.log('Primero genera un plan.');
            return;
        }
        const pacienteId = document.getElementById('paciente_id')?.value || null;
        const body = {
            paciente_id: pacienteId ? parseInt(pacienteId) : null,
            estado: estado, // 'borrador' | 'publicado'
            plan: planActual,
            configuracion: recolectarConfiguracionActual(),
            ingredientes: recolectarFiltrosIngredientes()
        };
        const resp = await fetch('/api/planes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            credentials: 'same-origin'
        });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(text || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        // Guardado silencioso - no mostrar alert
        console.log(`Plan ${estado} guardado. ID: ${data.id}`);
        if (estado === 'publicado' && data.detalle_url) {
            window.open(data.detalle_url, '_blank');
        }
    } catch (e) {
        console.error('Error guardando plan:', e);
        console.error('No se pudo guardar el plan.');
    }
}

function descargarPDFDesdePreview() {
    try {
        const nodo = document.getElementById('seccion-preview');
        if (!nodo) {
            console.error('No hay vista previa para imprimir.');
            return;
        }
        
        // Guardar el estado actual
        const semanaActualGuardada = semanaActual;
        const contenidoOriginal = document.getElementById('plan-content').innerHTML;
        
        // Mostrar todas las semanas para impresión
        if (planActual && planActual.semanas) {
            mostrarPlanCompletoParaImpresion(planActual);
        }
        
        // Imprimir
        window.print();
        
        // Restaurar el estado original después de imprimir
        setTimeout(() => {
            document.getElementById('plan-content').innerHTML = contenidoOriginal;
            semanaActual = semanaActualGuardada;
            if (document.getElementById('currentWeek')) {
                document.getElementById('currentWeek').textContent = semanaActual;
            }
        }, 100);
    } catch (e) {
        console.error('Error al generar PDF:', e);
    }
}

function mostrarPlanCompletoParaImpresion(plan) {
    const container = document.getElementById('plan-content');
    if (!container) return;
    
    const totalSemanas = plan.semanas.length;
    let html = '';
    
    // Mostrar todas las semanas
    for (let semana = 0; semana < totalSemanas; semana++) {
        const semanaData = plan.semanas[semana];
        const inicioSemana = semana * 7 + 1;
        const finSemana = Math.min((semana + 1) * 7, plan.dias);
        
        html += `
            <div class="plan-schedule" style="page-break-after: ${semana < totalSemanas - 1 ? 'always' : 'auto'};">
                <h4 style="margin-bottom: 10px; font-size: 14pt; font-weight: 700;">Semana ${semana + 1} - Horarios de Comidas</h4>
                <div class="schedule-grid">
        `;
        
        // Crear encabezados de días
        html += '<div class="schedule-header"><div class="time-header">Hora</div>';
        for (let dia = inicioSemana; dia <= finSemana; dia++) {
            html += `<div class="day-header">Día ${dia}</div>`;
        }
        html += '</div>';
        
        // Obtener todos los horarios únicos
        const horarios = ['07:00', '10:00', '12:00', '15:00', '19:00'];
        
        horarios.forEach(hora => {
            html += `<div class="schedule-row"><div class="time-cell">${hora}</div>`;
            
            for (let dia = inicioSemana; dia <= finSemana; dia++) {
                const diaIndex = dia - inicioSemana;
                const diaPlan = semanaData.dias[diaIndex];
                const comida = diaPlan ? Object.values(diaPlan.comidas).find(c => c.horario === hora) : null;
                
                // Determinar el tipo de comida basado en el horario
                let tipoComida = 'meal';
                if (hora === '07:00') tipoComida = 'desayuno';
                else if (hora === '10:00') tipoComida = 'media_manana';
                else if (hora === '12:00') tipoComida = 'almuerzo';
                else if (hora === '15:00') tipoComida = 'media_tarde';
                else if (hora === '19:00') tipoComida = 'cena';
                
                html += `
                    <div class="meal-cell">
                        ${comida ? `
                            <div class="meal-info">
                                <strong class="${tipoComida}">${comida.nombre}</strong>
                                <div class="meal-foods">
                                    ${comida.alimentos.map(alimento => {
                                        const colorGrupo = obtenerColorGrupo(alimento.grupo);
                                        const colorFondo = obtenerColorFondoGrupo(alimento.grupo);
                                        return `<div style="background: ${colorFondo}; color: ${colorGrupo}; border: 1px solid ${colorGrupo}; padding: 2px 6px; border-radius: 4px; margin: 1px 0; font-size: 10px; font-weight: 500;">${alimento.nombre} - ${alimento.cantidad}</div>`;
                                    }).join('')}
                                </div>
                            </div>
                        ` : '<div class="no-meal">—</div>'}
                    </div>
                `;
            }
            
            html += '</div>';
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Aplicar estilos adicionales
    setTimeout(() => {
        aplicarEstilosDinamicos();
    }, 100);
}

function recolectarConfiguracionActual() {
    return {
        fecha_inicio: document.getElementById('fecha_inicio')?.value || null,
        fecha_fin: document.getElementById('fecha_fin')?.value || null,
        dias_plan: parseInt(document.getElementById('dias_plan')?.value || '7'),
        kcal_objetivo: parseFloat(document.getElementById('kcal_objetivo')?.value || '0') || null,
        cho_pct: parseFloat(document.getElementById('cho_pct')?.value || '0') || null,
        pro_pct: parseFloat(document.getElementById('pro_pct')?.value || '0') || null,
        fat_pct: parseFloat(document.getElementById('fat_pct')?.value || '0') || null,
        ig_max: parseFloat(document.getElementById('ig_max')?.value || '0') || null,
        max_repeticiones: parseInt(document.getElementById('max_repeticiones')?.value || '0') || null,
        patron_comidas: ['des','alm','cena'].filter(id => document.getElementById(`comida_${id}`)?.checked).join(',')
    };
}

function recolectarFiltrosIngredientes() {
    return {
        incluir: [...ingredientesIncluir],
        excluir: [...ingredientesExcluir],
        grupos_excluidos: [...gruposExcluidos]
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const btnBorrador = document.getElementById('btnGuardarBorradorPlan');
    if (btnBorrador) btnBorrador.addEventListener('click', () => guardarPlan('borrador'));
    const btnPublicar = document.getElementById('btnPublicarPlan');
    if (btnPublicar) btnPublicar.addEventListener('click', () => guardarPlan('publicado'));
    // El botón ya tiene onclick="descargarPDFDesdePreview()" en el HTML, no necesitamos otro listener
    // const btnPDF = document.getElementById('btnDescargarPDF');
    // if (btnPDF) btnPDF.addEventListener('click', descargarPDFDesdePreview);
});

// ============ FUNCIONES DE UTILIDAD PARA COLORES DE GRUPOS ============

function obtenerColorGrupo(grupo) {
    const colores = {
        'GRUPO1_CEREALES': '#8b5cf6',      // Púrpura
        'GRUPO2_VERDURAS': '#10b981',      // Verde
        'GRUPO3_FRUTAS': '#f59e0b',        // Amarillo/naranja
        'GRUPO4_LACTEOS': '#06b6d4',      // Cian
        'GRUPO5_CARNES': '#ef4444',        // Rojo
        'GRUPO6_AZUCARES': '#ec4899',      // Rosa
        'GRUPO7_GRASAS': '#f97316',        // Naranja
        'GRUPO9_OTROS': '#6b7280',         // Gris
        // Fallbacks para nombres antiguos
        'cereales': '#8b5cf6',
        'verduras': '#10b981',
        'frutas': '#f59e0b',
        'proteinas': '#ef4444',
        'lacteos': '#06b6d4',
        'grasas': '#f97316',
        'otros': '#6b7280'
    };
    return colores[grupo] || '#6b7280';
}

function obtenerColorFondoGrupo(grupo) {
    const colores = {
        'GRUPO1_CEREALES': '#f3f4f6',      // Gris claro
        'GRUPO2_VERDURAS': '#f0fdf4',      // Verde claro
        'GRUPO3_FRUTAS': '#fffbeb',        // Amarillo claro
        'GRUPO4_LACTEOS': '#f0f9ff',      // Azul claro
        'GRUPO5_CARNES': '#fef2f2',        // Rojo claro
        'GRUPO6_AZUCARES': '#fdf2f8',      // Rosa claro
        'GRUPO7_GRASAS': '#fff7ed',        // Naranja claro
        'GRUPO9_OTROS': '#f9fafb',         // Gris claro
        // Fallbacks para nombres antiguos
        'cereales': '#f3f4f6',
        'verduras': '#f0fdf4',
        'frutas': '#fffbeb',
        'proteinas': '#fef2f2',
        'lacteos': '#f0f9ff',
        'grasas': '#fff7ed',
        'otros': '#f9fafb'
    };
    return colores[grupo] || '#f9fafb';
}

// ============ FUNCIONES DE BÚSQUEDA DE PACIENTES ============

async function buscarPacientes(query) {
    if (query.length < 1) return [];
    
    try {
        console.log('🔍 Buscando pacientes con query:', query);
        const response = await fetch(`/api/pacientes/buscar?q=${encodeURIComponent(query)}`, {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        console.log('📡 Response status:', response.status);
        console.log('📡 Response headers:', response.headers);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        console.log('📄 Content-Type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('❌ Respuesta no es JSON:', text.substring(0, 200));
            throw new Error('La respuesta del servidor no es JSON válido');
        }
        
                const data = await response.json();
                console.log('✅ Datos recibidos:', data);
                return data.results || [];
    } catch (error) {
        console.error('❌ Error buscando pacientes:', error);
        return [];
    }
}

function mostrarSugerenciasPacientes(sugerencias) {
    console.log('📋 Mostrando sugerencias:', sugerencias);
    
    // Limpiar sugerencias anteriores (buscar ambos IDs por si acaso)
    const existente1 = document.getElementById('sugerencias-pacientes');
    const existente2 = document.getElementById('sugerenciasPacientes');
    if (existente1) existente1.remove();
    if (existente2) existente2.remove();
    
    if (sugerencias.length === 0) {
        console.log('📭 No hay sugerencias');
        // Ocultar el contenedor si existe
        const container = document.getElementById('sugerenciasPacientes');
        if (container) {
            container.style.display = 'none';
        }
        return;
    }
    
    // Usar el contenedor existente del HTML o crear uno nuevo
    let div = document.getElementById('sugerenciasPacientes');
    if (!div) {
        // Si no existe, buscar el searchbox que contiene el input qPac
        const qPac = document.getElementById('qPac');
        const searchbox = qPac ? qPac.closest('.searchbox') : document.querySelector('.searchbox');
        
        if (!searchbox) {
            console.error('❌ No se encontró el searchbox');
            return;
        }
        
        // Crear uno nuevo
        div = document.createElement('div');
        div.id = 'sugerenciasPacientes';
        div.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            max-height: 200px;
            overflow-y: auto;
        `;
        
        // Insertar el contenedor dentro del searchbox
        searchbox.appendChild(div);
    }
    
    // Limpiar contenido anterior
    div.innerHTML = '';
    div.style.display = 'block';
    
    console.log(`📝 Generando ${sugerencias.length} sugerencias`);
    sugerencias.forEach(paciente => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
        `;
        item.innerHTML = `
            <div style="font-weight: 500;">${paciente.nombres} ${paciente.apellidos}</div>
            <div style="font-size: 12px; color: #666;">DNI: ${paciente.dni}</div>
        `;
        
        item.addEventListener('click', function() {
            console.log('👤 Paciente seleccionado:', paciente);
            // Llenar el campo de búsqueda con la información del paciente
            const qPac = document.getElementById('qPac');
            if (qPac) {
                qPac.value = `${paciente.nombres} ${paciente.apellidos} (DNI: ${paciente.dni})`;
            }
            
            // Mostrar botón clear
            const btnClearPac = document.getElementById('btnClearPac');
            if (btnClearPac) {
                btnClearPac.style.visibility = 'visible';
            }
            
            // Ocultar sugerencias
            if (div) {
                div.style.display = 'none';
            }
            
            // Cargar datos del paciente
            cargarDatosPaciente(paciente.id);
        });
        
        // Efecto hover
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8fafc';
        });
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
        });
        
        div.appendChild(item);
    });
    
    console.log('✅ Sugerencias mostradas');
}

// ============ FUNCIONES DE BÚSQUEDA DE INGREDIENTES ============

async function buscarIngredientes(query) {
    if (query.length < 1) return [];
    
    try {
        console.log('🔍 Buscando ingredientes con query:', query);
        
        // Mostrar indicador de carga
        mostrarIndicadorCarga(query.length >= 1);
        
        const response = await fetch(`/api/ingredientes/buscar?q=${encodeURIComponent(query)}`, {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('✅ Ingredientes encontrados:', data);
        
        // Ocultar indicador de carga
        mostrarIndicadorCarga(false);
        
        // Filtrar ingredientes de grupos excluidos
        const ingredientesFiltrados = (data.results || []).filter(ingrediente => {
            const grupo = ingrediente.grupo || '';
            return !gruposExcluidos.includes(grupo);
        });
        
        console.log(`🔍 Ingredientes filtrados (excluyendo ${gruposExcluidos.length} grupos):`, ingredientesFiltrados);
        
        return ingredientesFiltrados;
    } catch (error) {
        console.error('❌ Error buscando ingredientes:', error);
        // Ocultar indicador de carga en caso de error
        mostrarIndicadorCarga(false);
        return [];
    }
}

function mostrarIndicadorCarga(mostrar) {
    // Buscar contenedores de sugerencias existentes
    const contenedores = ['sugerencias-ingredientes-incluir', 'sugerencias-ingredientes-excluir'];
    
    contenedores.forEach(contenedorId => {
        const existente = document.getElementById(contenedorId);
        if (existente && mostrar) {
            // Agregar indicador de carga al contenedor existente
            const indicador = document.createElement('div');
            indicador.id = 'indicador-carga-' + contenedorId;
            indicador.style.cssText = `
                padding: 20px;
                text-align: center;
                color: #6b7280;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            `;
            indicador.innerHTML = `
                <div class="loading-spinner"></div>
                <span>Buscando ingredientes...</span>
            `;
            existente.appendChild(indicador);
        } else if (existente && !mostrar) {
            // Remover indicador de carga
            const indicador = document.getElementById('indicador-carga-' + contenedorId);
            if (indicador) {
                indicador.remove();
            }
        }
    });
}

function limpiarDropdownsIngredientes() {
    // Limpiar todos los dropdowns de ingredientes
    const dropdowns = ['sugerencias-ingredientes-incluir', 'sugerencias-ingredientes-excluir'];
    dropdowns.forEach(id => {
        const dropdown = document.getElementById(id);
        if (dropdown) {
            dropdown.remove();
        }
    });
}

// ============ FUNCIONES PARA GRUPOS EXCLUIDOS ============

function actualizarGruposExcluidos() {
    gruposExcluidos = [];
    const checkboxes = document.querySelectorAll('.grupos-exclusion-grid input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        gruposExcluidos.push(checkbox.value);
    });
    console.log('🚫 Grupos excluidos actualizados:', gruposExcluidos);
    
    // Remover ingredientes de grupos excluidos
    removerIngredientesDeGruposExcluidos();
}

function obtenerPatronComidas() {
    const comidas = [];
    const checkboxes = document.querySelectorAll('#comida_des, #comida_mm, #comida_alm, #comida_mt, #comida_cena');
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            comidas.push(checkbox.value);
        }
    });
    const patron = comidas.join(',');
    console.log('🍽️ Patrón de comidas:', patron);
    return patron;
}

function calcularDiasDelPlan() {
    const fechaInicio = document.getElementById('fecha_inicio').value;
    const fechaFin = document.getElementById('fecha_fin').value;
    const campoDias = document.getElementById('dias_plan');
    
    if (fechaInicio && fechaFin) {
        const inicio = new Date(fechaInicio);
        const fin = new Date(fechaFin);
        
        // Calcular diferencia en días
        const diferenciaTiempo = fin.getTime() - inicio.getTime();
        const dias = Math.ceil(diferenciaTiempo / (1000 * 3600 * 24)) + 1; // +1 para incluir ambos días
        
        if (dias > 0) {
            campoDias.value = dias;
            console.log(`📅 Plan calculado: ${dias} días (${fechaInicio} a ${fechaFin})`);
        } else {
            campoDias.value = '';
            console.log('⚠️ Fecha de fin debe ser posterior a fecha de inicio');
        }
    } else {
        campoDias.value = '';
    }
}

function obtenerRangoFechas() {
    const fechaInicio = document.getElementById('fecha_inicio').value;
    const fechaFin = document.getElementById('fecha_fin').value;
    const dias = document.getElementById('dias_plan').value;
    
    console.log('📅 Rango de fechas:', { fechaInicio, fechaFin, dias });
    
    return {
        fechaInicio,
        fechaFin,
        dias: parseInt(dias) || 0
    };
}

function removerIngredientesDeGruposExcluidos() {
    let ingredientesRemovidos = 0;
    
    // Remover de ingredientes a incluir
    const ingredientesIncluirOriginal = [...ingredientesIncluir];
    ingredientesIncluir = ingredientesIncluir.filter(ingrediente => {
        if (gruposExcluidos.includes(ingrediente.grupo)) {
            ingredientesRemovidos++;
            console.log(`🗑️ Removiendo ingrediente "${ingrediente.text}" del grupo excluido "${ingrediente.grupo}"`);
            return false;
        }
        return true;
    });
    
    // Remover de ingredientes a excluir
    const ingredientesExcluirOriginal = [...ingredientesExcluir];
    ingredientesExcluir = ingredientesExcluir.filter(ingrediente => {
        if (gruposExcluidos.includes(ingrediente.grupo)) {
            ingredientesRemovidos++;
            console.log(`🗑️ Removiendo ingrediente "${ingrediente.text}" del grupo excluido "${ingrediente.grupo}"`);
            return false;
        }
        return true;
    });
    
    // Actualizar la UI si se removieron ingredientes
    if (ingredientesRemovidos > 0) {
        actualizarListaIngredientes('incluir');
        actualizarListaIngredientes('excluir');
        
        Toastify({
            text: `🗑️ Se removieron ${ingredientesRemovidos} ingredientes de grupos excluidos`,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#f59e0b"
        }).showToast();
    }
}

function mostrarSugerenciasIngredientes(sugerencias, tipo) {
    console.log(`📋 Mostrando sugerencias de ingredientes (${tipo}):`, sugerencias);
    
    // Limpiar todos los dropdowns de ingredientes primero
    limpiarDropdownsIngredientes();
    
    if (sugerencias.length === 0) {
        console.log('📭 No hay sugerencias de ingredientes');
        return;
    }
    
    // Crear contenedor mejorado con mejor visibilidad
    const div = document.createElement('div');
    div.id = `sugerencias-ingredientes-${tipo}`;
    div.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #e5e7eb;
        border-top: none;
        border-radius: 0 0 8px 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 99999;
        max-height: 180px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: #cbd5e1 #f1f5f9;
    `;
    
    // Mejorar el scrollbar para webkit browsers
    div.style.setProperty('--scrollbar-thumb', '#cbd5e1');
    div.style.setProperty('--scrollbar-track', '#f1f5f9');
    
    console.log(`📝 Generando ${sugerencias.length} sugerencias de ingredientes`);
    sugerencias.forEach((ingrediente, index) => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 14px 16px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
            transition: all 0.2s ease;
            position: relative;
        `;
        
        // Mejorar el contenido del ingrediente
        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="
                    width: 8px; 
                    height: 8px; 
                    border-radius: 50%; 
                    background: ${tipo === 'incluir' ? '#10b981' : '#ef4444'};
                    flex-shrink: 0;
                "></div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #1f2937; font-size: 14px; margin-bottom: 2px;">
                        ${ingrediente.text}
                    </div>
                    <div style="font-size: 12px; color: #6b7280; display: flex; align-items: center; gap: 4px;">
                        <i class="fas fa-tag" style="font-size: 10px;"></i>
                        Grupo: ${ingrediente.grupo || 'N/A'}
                    </div>
                </div>
            </div>
        `;
        
        item.addEventListener('click', function() {
            console.log(`🍎 Ingrediente seleccionado para ${tipo}:`, ingrediente);
            agregarIngrediente(ingrediente, tipo);
            
            // Limpiar campo de búsqueda
            const campo = document.getElementById(`qIngrediente${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`);
            if (campo) {
                campo.value = '';
            }
            
            // Limpiar sugerencias después de un pequeño delay
            setTimeout(() => {
                if (div && div.parentNode) {
                    div.remove();
                }
            }, 100);
        });
        
        // Mejorar efectos hover
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = tipo === 'incluir' ? '#f0fdf4' : '#fef2f2';
            this.style.transform = 'translateX(4px)';
            this.style.borderLeft = `4px solid ${tipo === 'incluir' ? '#10b981' : '#ef4444'}`;
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.transform = 'translateX(0)';
            this.style.borderLeft = 'none';
        });
        
        div.appendChild(item);
    });
    
    // Insertar el contenedor después del searchbox correspondiente
    const inputField = document.getElementById(`qIngrediente${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`);
    const searchbox = inputField.parentElement;
    if (searchbox) {
        searchbox.appendChild(div);
        console.log(`✅ Sugerencias de ingredientes mostradas para ${tipo}`);
    } else {
        console.error(`❌ No se encontró el searchbox para ${tipo}`);
    }
}

function agregarIngrediente(ingrediente, tipo) {
    const lista = tipo === 'incluir' ? ingredientesIncluir : ingredientesExcluir;
    const listaId = `lista-ingredientes-${tipo}`;
    
    // Verificar si ya existe
    if (lista.some(item => item.id === ingrediente.id)) {
        Toastify({
            text: `⚠️ El ingrediente "${ingrediente.text}" ya está en la lista`,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#f59e0b"
        }).showToast();
        return;
    }
    
    // Agregar a la lista
    lista.push(ingrediente);
    
    // Actualizar la UI
    actualizarListaIngredientes(tipo);
    
    Toastify({
        text: `✅ Ingrediente "${ingrediente.text}" agregado para ${tipo === 'incluir' ? 'incluir' : 'excluir'}`,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#10b981"
    }).showToast();
}

function removerIngrediente(ingredienteId, tipo) {
    const lista = tipo === 'incluir' ? ingredientesIncluir : ingredientesExcluir;
    const ingrediente = lista.find(item => item.id === ingredienteId);
    
    if (ingrediente) {
        // Remover de la lista
        const index = lista.findIndex(item => item.id === ingredienteId);
        lista.splice(index, 1);
        
        // Actualizar la UI
        actualizarListaIngredientes(tipo);
        
        // Limpiar cualquier dropdown abierto
        const dropdown = document.getElementById(`sugerencias-ingredientes-${tipo}`);
        if (dropdown) {
            dropdown.remove();
        }
        
        // Limpiar el campo de búsqueda
        const campo = document.getElementById(`qIngrediente${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`);
        if (campo) {
            campo.value = '';
        }
        
        Toastify({
            text: `🗑️ Ingrediente "${ingrediente.text}" removido`,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#6b7280"
        }).showToast();
    }
}

function actualizarListaIngredientes(tipo) {
    const lista = tipo === 'incluir' ? ingredientesIncluir : ingredientesExcluir;
    const listaElement = document.getElementById(`lista-ingredientes-${tipo}`);
    
    if (!listaElement) return;
    
    if (lista.length === 0) {
        listaElement.innerHTML = `
            <div class="ingrediente-vacio">
                <i class="fas fa-search" style="font-size: 24px; color: #d1d5db; margin: 40px 0 20px 20px; display: block;"></i>
                <div style="color: #9ca3af; font-size: 14px; margin-left: 20px; margin-bottom: 12px;">No hay ingredientes seleccionados</div>
                <div style="color: #d1d5db; font-size: 12px; margin-left: 20px; margin-bottom: 40px;">Busca ingredientes para ${tipo === 'incluir' ? 'incluir' : 'excluir'}</div>
            </div>
        `;
        return;
    }
    
    listaElement.innerHTML = lista.map(ingrediente => `
        <div class="ingrediente-item ${tipo}" style="
            display: flex;
            align-items: center;
            padding: 12px 16px;
            margin: 8px 0;
            background: linear-gradient(135deg, ${tipo === 'incluir' ? '#f0fdf4' : '#fef2f2'} 0%, white 100%);
            border: 1px solid ${tipo === 'incluir' ? '#bbf7d0' : '#fecaca'};
            border-left: 4px solid ${tipo === 'incluir' ? '#10b981' : '#ef4444'};
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        ">
            <div style="
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: ${tipo === 'incluir' ? '#10b981' : '#ef4444'};
                margin-right: 12px;
                flex-shrink: 0;
                box-shadow: 0 0 0 2px ${tipo === 'incluir' ? '#dcfce7' : '#fee2e2'};
            "></div>
            
            <div style="flex: 1; min-width: 0;">
                <div style="
                    font-weight: 600;
                    color: #1f2937;
                    font-size: 14px;
                    margin-bottom: 4px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                ">${ingrediente.text}</div>
                <div style="
                    font-size: 12px;
                    color: #6b7280;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <i class="fas fa-tag" style="font-size: 10px;"></i>
                    <span>${ingrediente.grupo || 'N/A'}</span>
                    <span style="
                        background: ${tipo === 'incluir' ? '#dcfce7' : '#fee2e2'};
                        color: ${tipo === 'incluir' ? '#166534' : '#dc2626'};
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: 500;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    ">${tipo === 'incluir' ? 'incluir' : 'excluir'}</span>
                </div>
            </div>
            
            <button class="btn-remover-ingrediente" onclick="removerIngrediente(${ingrediente.id}, '${tipo}')" style="
                background: ${tipo === 'incluir' ? '#10b981' : '#ef4444'};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                margin-left: 12px;
                transition: all 0.2s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                width: 32px;
                height: 32px;
            ">
                <i class="fas fa-times" style="font-size: 12px;"></i>
            </button>
            
            <!-- Efecto de brillo sutil -->
            <div style="
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent 0%, ${tipo === 'incluir' ? '#10b981' : '#ef4444'} 50%, transparent 100%);
                opacity: 0.6;
            "></div>
        </div>
    `).join('');
    
    // Agregar efectos hover mejorados
    listaElement.querySelectorAll('.ingrediente-item').forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 16px rgba(0,0,0,0.12)';
            this.style.borderColor = tipo === 'incluir' ? '#10b981' : '#ef4444';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
            this.style.borderColor = tipo === 'incluir' ? '#bbf7d0' : '#fecaca';
        });
        
        // Mejorar el botón de remover
        const btnRemover = item.querySelector('.btn-remover-ingrediente');
        if (btnRemover) {
            btnRemover.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.1)';
                this.style.background = tipo === 'incluir' ? '#059669' : '#dc2626';
            });
            
            btnRemover.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
                this.style.background = tipo === 'incluir' ? '#10b981' : '#ef4444';
            });
        }
    });
}

function limpiarIngredientes(tipo) {
    const lista = tipo === 'incluir' ? ingredientesIncluir : ingredientesExcluir;
    lista.length = 0;
    actualizarListaIngredientes(tipo);
    
    Toastify({
        text: `🧹 Lista de ingredientes para ${tipo === 'incluir' ? 'incluir' : 'excluir'} limpiada`,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#10b981"
    }).showToast();
}

// Función para cargar datos del paciente
async function cargarDatosPaciente(pacienteId) {
    try {
        console.log('📥 Cargando datos del paciente:', pacienteId);
        const response = await fetch(`/api/pacientes/${pacienteId}/detalle`);
        const data = await response.json();
        
        if (data.ok) {
            const d = data.paciente;
            console.log('✅ Datos del paciente cargados:', d);
            
            // Guardar ID del paciente
            document.getElementById('paciente_id').value = pacienteId;
            
            // Datos personales
            document.getElementById('p_dni').value = d.dni || '';
            document.getElementById('p_nombres').value = d.nombres || '';
            document.getElementById('p_apellidos').value = d.apellidos || '';
            document.getElementById('p_sexo').value = d.sexo || '';
            document.getElementById('p_fnac').value = d.fecha_nac || '';
            document.getElementById('p_tel').value = d.telefono || '';
            document.getElementById('p_email').value = d.usuario_email || '';
            
            // Datos de antropometría
            if (d.antropometria) {
                document.getElementById('p_peso').value = (d.antropometria.peso != null && d.antropometria.peso !== '') ? d.antropometria.peso : '—';
                document.getElementById('p_talla').value = (d.antropometria.talla != null && d.antropometria.talla !== '') ? d.antropometria.talla : '—';
                document.getElementById('p_cintura').value = (d.antropometria.cc != null && d.antropometria.cc !== '') ? d.antropometria.cc : '—';
                const bfPct = d.antropometria.bf_pct;
                if (bfPct != null && bfPct !== '') {
                    const bfPctFormatted = parseFloat(bfPct).toFixed(1);
                    document.getElementById('p_grasa').value = `${bfPctFormatted}%`;
                } else {
                    document.getElementById('p_grasa').value = '—';
                }
                document.getElementById('p_actividad').value = (d.antropometria.actividad != null && d.antropometria.actividad !== '') ? d.antropometria.actividad : '—';
                document.getElementById('p_fecha_antropo').value = (d.antropometria.fecha_medicion != null && d.antropometria.fecha_medicion !== '') ? d.antropometria.fecha_medicion : '—';
            } else {
                // Limpiar campos si no hay datos
                ['p_peso', 'p_talla', 'p_cintura', 'p_grasa', 'p_actividad', 'p_fecha_antropo'].forEach(id => {
                    document.getElementById(id).value = '—';
                });
            }
            
            // Datos clínicos
            if (d.clinico) {
                document.getElementById('p_hba1c').value = (d.clinico.hba1c != null && d.clinico.hba1c !== '') ? d.clinico.hba1c : '—';
                document.getElementById('p_glucosa').value = (d.clinico.glucosa_ayunas != null && d.clinico.glucosa_ayunas !== '') ? d.clinico.glucosa_ayunas : '—';
                document.getElementById('p_ldl').value = (d.clinico.ldl != null && d.clinico.ldl !== '') ? d.clinico.ldl : '—';
                document.getElementById('p_trigliceridos').value = (d.clinico.trigliceridos != null && d.clinico.trigliceridos !== '') ? d.clinico.trigliceridos : '—';
                document.getElementById('p_pa_sis').value = (d.clinico.pa_sis != null && d.clinico.pa_sis !== '') ? d.clinico.pa_sis : '—';
                document.getElementById('p_pa_dia').value = (d.clinico.pa_dia != null && d.clinico.pa_dia !== '') ? d.clinico.pa_dia : '—';
                document.getElementById('p_fecha_clinico').value = (d.clinico.fecha_medicion != null && d.clinico.fecha_medicion !== '') ? d.clinico.fecha_medicion : '—';
            } else {
                // Limpiar campos si no hay datos
                ['p_hba1c', 'p_glucosa', 'p_ldl', 'p_trigliceridos', 'p_pa_sis', 'p_pa_dia', 'p_fecha_clinico'].forEach(id => {
                    document.getElementById(id).value = '—';
                });
            }
            
            // NO llenar configuración del plan aquí - se llena solo con motor IA
            // Solo limpiar la configuración para que esté vacía hasta usar Motor IA
            limpiarConfiguracionPlan();
            
            // Habilitar botones
            const btnGenerar = document.getElementById('btnGenerar');
            if (btnGenerar) btnGenerar.disabled = false;
            
            const btnMotorRecomendacion = document.getElementById('btnMotorRecomendacion');
            if (btnMotorRecomendacion) btnMotorRecomendacion.disabled = false;
            
            // Mostrar mensaje de éxito con Toastify
            Toastify({
                text: `✅ Datos de ${d.nombres} ${d.apellidos} cargados correctamente`,
                duration: 3000,
                gravity: "top",
                position: "right",
                backgroundColor: "#10b981"
            }).showToast();
            
        } else {
            console.error('❌ Error en respuesta:', data);
            Toastify({
                text: "❌ Error al cargar los datos del paciente",
                duration: 3000,
                gravity: "top",
                position: "right",
                backgroundColor: "#ef4444"
            }).showToast();
        }
    } catch (error) {
        console.error('❌ Error cargando datos:', error);
        Toastify({
            text: "❌ Error de conexión al cargar datos del paciente",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#ef4444"
        }).showToast();
    }
}

// Función para limpiar el formulario
function limpiarFormulario() {
    try {
        console.log('🧹 Limpiando todos los campos del formulario...');
        
        // Limpiar campo de búsqueda
        const qPac = document.getElementById('qPac');
        if (qPac) {
            qPac.value = '';
        }
        
        // Limpiar botón clear del campo de búsqueda
        const btnClearPac = document.getElementById('btnClearPac');
        if (btnClearPac) {
            btnClearPac.style.visibility = 'hidden';
        }
        
        // Limpiar sugerencias
        const existente = document.getElementById('sugerenciasPacientes');
        if (existente) {
            existente.style.display = 'none';
            existente.innerHTML = '';
        }
        
        // Limpiar ID del paciente
        const pacienteId = document.getElementById('paciente_id');
        if (pacienteId) {
            pacienteId.value = '';
        }
        
        // Limpiar datos personales
        const camposPersonales = ['p_dni', 'p_nombres', 'p_apellidos', 'p_sexo', 'p_fnac', 'p_tel', 'p_email'];
        camposPersonales.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) campo.value = '';
        });
        
        // Limpiar datos de antropometría
        const camposAntropometria = ['p_peso', 'p_talla', 'p_cintura', 'p_grasa', 'p_actividad', 'p_fecha_antropo'];
        camposAntropometria.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) campo.value = '';
        });
        
        // Limpiar datos clínicos
        const camposClinicos = ['p_hba1c', 'p_glucosa', 'p_ldl', 'p_pa_sis', 'p_pa_dia', 'p_fecha_clinico'];
        camposClinicos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) campo.value = '';
        });
        
        // Deshabilitar botones
        const btnGenerar = document.getElementById('btnGenerar');
        if (btnGenerar) btnGenerar.disabled = true;
        
        const btnMotorRecomendacion = document.getElementById('btnMotorRecomendacion');
        if (btnMotorRecomendacion) btnMotorRecomendacion.disabled = true;
        
        // Limpiar listas de ingredientes
        ingredientesIncluir.length = 0;
        ingredientesExcluir.length = 0;
        gruposExcluidos.length = 0;
        limpiarDropdownsIngredientes();
        actualizarListaIngredientes('incluir');
        actualizarListaIngredientes('excluir');
        
        // Limpiar checkboxes de grupos excluidos
        const checkboxesGrupos = document.querySelectorAll('.grupos-exclusion-grid input[type="checkbox"]');
        checkboxesGrupos.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Restablecer patrones de comidas por defecto (desayuno, almuerzo, cena)
        document.getElementById('comida_des').checked = true;
        document.getElementById('comida_mm').checked = false;
        document.getElementById('comida_alm').checked = true;
        document.getElementById('comida_mt').checked = false;
        document.getElementById('comida_cena').checked = true;
        
        // Limpiar configuración del plan
        limpiarConfiguracionPlan();
        
        // Restablecer fechas por defecto
        const hoy = new Date();
        const fechaHoy = hoy.toISOString().split('T')[0];
        document.getElementById('fecha_inicio').value = fechaHoy;
        document.getElementById('fecha_fin').value = '';
        document.getElementById('dias_plan').value = '';
        
        // Mostrar mensaje de éxito con Toastify
        Toastify({
            text: "🧹 Formulario limpiado correctamente",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#10b981"
        }).showToast();
        
        console.log('✅ Formulario limpiado correctamente');
        
    } catch (error) {
        console.error('❌ Error limpiando formulario:', error);
        Toastify({
            text: "❌ Error al limpiar el formulario",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#ef4444"
        }).showToast();
    }
}

async function seleccionarPaciente(pacienteId) {
    try {
        // Obtener detalles del paciente
        const response = await fetch(`/api/pacientes/${pacienteId}/detalle`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Llenar formulario con datos del paciente
        llenarFormularioPaciente(data);
        
        // Cargar datos completos del paciente (incluye antropometría y clínico)
        await cargarDatosPaciente(pacienteId);
        
        // Ocultar sugerencias
        const sugerencias = document.getElementById('sugerenciasPacientes');
        if (sugerencias) {
            sugerencias.style.display = 'none';
        }
        
        // Limpiar búsqueda y mostrar nombre del paciente
        const qPac = document.getElementById('qPac');
        if (qPac) {
            const nombres = data.paciente?.nombres || '';
            const apellidos = data.paciente?.apellidos || '';
            const dni = data.paciente?.dni || '';
            qPac.value = `${nombres} ${apellidos}`.trim() || `DNI: ${dni}`;
        }
        
        // Habilitar botones
        const btnGenerar = document.getElementById('btnGenerar');
        if (btnGenerar) btnGenerar.disabled = false;
        
        const btnMotorRecomendacion = document.getElementById('btnMotorRecomendacion');
        if (btnMotorRecomendacion) btnMotorRecomendacion.disabled = false;
        
        const btnEditarPac = document.getElementById('btnEditarPac');
        if (btnEditarPac) btnEditarPac.disabled = false;
        
        const btnGuardarBorrador = document.getElementById('btnGuardarBorrador');
        if (btnGuardarBorrador) btnGuardarBorrador.disabled = false;
        
        // Mostrar mensaje de éxito
        Toastify({
            text: "✅ Paciente seleccionado correctamente",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#10b981"
        }).showToast();
        
    } catch (error) {
        console.error('Error seleccionando paciente:', error);
        Toastify({
            text: `❌ Error: ${error.message}`,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#ef4444"
        }).showToast();
    }
}

function llenarFormularioPaciente(paciente) {
    // Datos básicos
    document.getElementById('paciente_id').value = paciente.id;
    document.getElementById('p_dni').value = paciente.dni || '';
    document.getElementById('p_nombres').value = paciente.nombres || '';
    document.getElementById('p_apellidos').value = paciente.apellidos || '';
    document.getElementById('p_sexo').value = paciente.sexo || '';
    document.getElementById('p_fnac').value = paciente.fecha_nac || '';
    document.getElementById('p_tel').value = paciente.telefono || '';
    document.getElementById('p_email').value = paciente.email || '';
    
    // Antropometría
    if (paciente.antropometria) {
        document.getElementById('p_peso').value = paciente.antropometria.peso || '';
        document.getElementById('p_talla').value = paciente.antropometria.talla || '';
        document.getElementById('p_cintura').value = paciente.antropometria.cc || '';
        const bfPct = paciente.antropometria.bf_pct;
        if (bfPct != null && bfPct !== '') {
            const bfPctFormatted = parseFloat(bfPct).toFixed(1);
            document.getElementById('p_grasa').value = `${bfPctFormatted}%`;
        } else {
            document.getElementById('p_grasa').value = '';
        }
        document.getElementById('p_actividad').value = paciente.antropometria.actividad || '';
        document.getElementById('p_fecha_antropo').value = paciente.antropometria.fecha_medicion || '';
    }
    
    // Datos clínicos
    if (paciente.clinico) {
        document.getElementById('p_hba1c').value = paciente.clinico.hba1c || '';
        document.getElementById('p_glucosa').value = paciente.clinico.glucosa_ayunas || '';
        document.getElementById('p_ldl').value = paciente.clinico.ldl || '';
        document.getElementById('p_trigliceridos').value = paciente.clinico.trigliceridos || '';
        document.getElementById('p_pa_sis').value = paciente.clinico.pa_sis || '';
        document.getElementById('p_pa_dia').value = paciente.clinico.pa_dia || '';
        document.getElementById('p_fecha_clinico').value = paciente.clinico.fecha_medicion || '';
    }
    
    // NO llenar configuración del plan aquí - se llena solo con motor IA
    // Solo limpiar la configuración para que esté vacía hasta usar Motor IA
    limpiarConfiguracionPlan();
}

// ============ FUNCIONES BÁSICAS ============

function limpiarFormulario() {
    // Usar la función completa de limpieza
    limpiarTodosLosCampos();
    
    // Limpiar preview
    const previewEmpty = document.getElementById('previewEmpty');
    const previewPlan = document.getElementById('previewPlan');
    const diaPanel = document.getElementById('diaPanel');
    
    if (previewEmpty) previewEmpty.style.display = 'block';
    if (previewPlan) previewPlan.style.display = 'none';
    if (diaPanel) diaPanel.innerHTML = '';
    
    // Limpiar variables globales
    planActual = null;
    
    // Mostrar mensaje de éxito con Toastify
    Toastify({
        text: "🧹 Formulario limpiado correctamente",
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#10b981"
    }).showToast();
}

async function generarPlan() {
    console.log('🚀 INICIANDO generarPlan()...');
    const pacienteId = document.getElementById('paciente_id').value;
    console.log('👤 Paciente ID:', pacienteId);
    
    if (!pacienteId) {
        console.log('❌ No hay paciente seleccionado');
        Toastify({
            text: "❌ Selecciona un paciente primero",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "#f59e0b"
        }).showToast();
        return;
    }
    
    // Validar que la configuración del plan esté completa
    console.log('✅ Validando configuración del plan...');
    const configuracionCompleta = validarConfiguracionPlan();
    if (!configuracionCompleta.valida) {
        Toastify({
            text: `❌ ${configuracionCompleta.mensaje}`,
            duration: 4000,
            gravity: "top",
            position: "right",
            backgroundColor: "#ef4444"
        }).showToast();
        return;
    }
    
    // Mostrar loading
    mostrarLoadingGeneracion();
    
    try {
        // Recopilar datos del plan
        console.log('📋 Recopilando datos del plan...');
        const datosPlan = recopilarDatosPlan(pacienteId);
        console.log('📋 Datos del plan recopilados:', datosPlan);
        
        // Generar el plan
        console.log('🌐 Enviando solicitud a /api/recomendacion/generar...');
        
        // Actualizar mensaje de loading para indicar optimización
        let loadingText = document.querySelector('#loading-overlay p');
        if (loadingText) {
            loadingText.textContent = 'Generando plan nutricional...';
        }
        
        const respuesta = await fetch('/api/recomendacion/generar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(datosPlan)
        });
        
        // Actualizar mensaje durante la generación
        if (loadingText) {
            loadingText.textContent = 'Optimizando plan para cumplir objetivos nutricionales...';
        }
        
        if (!respuesta.ok) {
            throw new Error(`Error del servidor: ${respuesta.status}`);
        }
        
        const planGenerado = await respuesta.json();
        console.log('📦 Plan generado desde API:', planGenerado);
        console.log('📦 Estructura del plan:', JSON.stringify(planGenerado, null, 2));
        
        // Verificar si la respuesta tiene error
        if (planGenerado.error) {
            throw new Error(`Error del servidor: ${planGenerado.error}`);
        }
        
        // Actualizar los campos de la UI con los valores ajustados del ML
        if (planGenerado.metas_nutricionales) {
            const metas = planGenerado.metas_nutricionales;
            console.log('📊 Actualizando campos con valores ajustados del ML:', metas);
            console.log('📊 Valores recibidos:', {
                cho: metas.carbohidratos_porcentaje,
                pro: metas.proteinas_porcentaje,
                fat: metas.grasas_porcentaje,
                kcal: metas.calorias_diarias
            });
            
            // Verificar valores de debug ML si están disponibles
            if (planGenerado.debug_ml) {
                console.log('🤖 Debug ML:', planGenerado.debug_ml);
            }
            
            // Obtener valores actuales ANTES de actualizar
            const choAntes = document.getElementById('cho_pct')?.value;
            const proAntes = document.getElementById('pro_pct')?.value;
            console.log('📊 Valores ANTES de actualizar:', { cho: choAntes, pro: proAntes });
            
            // Actualizar campos de configuración con los valores ajustados
            if (metas.calorias_diarias) {
                const campoKcal = document.getElementById('kcal_objetivo');
                if (campoKcal) {
                    campoKcal.value = metas.calorias_diarias;
                    console.log('✅ Actualizado kcal_objetivo:', metas.calorias_diarias);
                } else {
                    console.error('❌ No se encontró campo kcal_objetivo');
                }
            }
            
            if (metas.carbohidratos_porcentaje !== undefined) {
                const campoCho = document.getElementById('cho_pct');
                if (campoCho) {
                    campoCho.value = metas.carbohidratos_porcentaje;
                    console.log('✅ Actualizado cho_pct:', metas.carbohidratos_porcentaje, '(antes:', choAntes, ')');
                } else {
                    console.error('❌ No se encontró campo cho_pct');
                }
            } else {
                console.warn('⚠️ carbohidratos_porcentaje es undefined');
            }
            
            if (metas.proteinas_porcentaje !== undefined) {
                const campoPro = document.getElementById('pro_pct');
                if (campoPro) {
                    campoPro.value = metas.proteinas_porcentaje;
                    console.log('✅ Actualizado pro_pct:', metas.proteinas_porcentaje, '(antes:', proAntes, ')');
                } else {
                    console.error('❌ No se encontró campo pro_pct');
                }
            } else {
                console.warn('⚠️ proteinas_porcentaje es undefined');
            }
            
            if (metas.grasas_porcentaje !== undefined) {
                const campoFat = document.getElementById('fat_pct');
                if (campoFat) {
                    campoFat.value = metas.grasas_porcentaje;
                    console.log('✅ Actualizado fat_pct:', metas.grasas_porcentaje);
                } else {
                    console.error('❌ No se encontró campo fat_pct');
                }
            } else {
                console.warn('⚠️ grasas_porcentaje es undefined');
            }
            
            // Verificar valores DESPUÉS de actualizar
            const choDespues = document.getElementById('cho_pct')?.value;
            const proDespues = document.getElementById('pro_pct')?.value;
            console.log('📊 Valores DESPUÉS de actualizar:', { cho: choDespues, pro: proDespues });
            
            // Mostrar mensaje informativo si los valores fueron ajustados
            const campoCho = document.getElementById('cho_pct');
            const campoPro = document.getElementById('pro_pct');
            const choOriginal = campoCho?.dataset?.originalValue ? parseFloat(campoCho.dataset.originalValue) : null;
            const proOriginal = campoPro?.dataset?.originalValue ? parseFloat(campoPro.dataset.originalValue) : null;
            
            // Solo mostrar mensaje si hay valores originales guardados y fueron ajustados
            if (choOriginal !== null && proOriginal !== null) {
                const choAjustado = metas.carbohidratos_porcentaje;
                const proAjustado = metas.proteinas_porcentaje;
                
                // Mostrar notificación si los valores fueron ajustados
                if (Math.abs(choAjustado - choOriginal) > 0.1 || Math.abs(proAjustado - proOriginal) > 0.1) {
                    Toastify({
                        text: `🤖 ML ajustó los macronutrientes: CHO ${choOriginal}%→${choAjustado}%, PRO ${proOriginal}%→${proAjustado}%`,
                        duration: 5000,
                        gravity: "top",
                        position: "right",
                        backgroundColor: "#3b82f6"
                    }).showToast();
                }
            }
        }
        
        // Convertir el formato del motor al formato esperado por la UI
        const planConvertido = convertirPlanMotorAFormatoUI(planGenerado);
        console.log('🔄 Plan convertido:', planConvertido);
        
        // Almacenar el plan generado
        planActual = planConvertido;
        
        // Actualizar mensaje de loading
        loadingText = document.querySelector('#loading-overlay p');
        if (loadingText) {
            loadingText.textContent = 'Guardando plan...';
        }
        
        // Guardar automáticamente como borrador
        console.log('💾 Guardando plan como borrador...');
        
        // Incluir configuración ajustada del plan generado
        const planConConfiguracion = {
            ...planConvertido,
            configuracion_ajustada: planGenerado.configuracion_ajustada || {},
            metas_nutricionales: planGenerado.metas_nutricionales || {},
            debug_ml: planGenerado.debug_ml || {}
        };
        
        const body = {
            paciente_id: pacienteId ? parseInt(pacienteId) : null,
            estado: 'borrador',
            plan: planConConfiguracion,
            configuracion: recolectarConfiguracionActual(),
            ingredientes: recolectarFiltrosIngredientes()
        };
        
        const respGuardar = await fetch('/api/planes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            credentials: 'same-origin'
        });
        
        if (!respGuardar.ok) {
            const text = await respGuardar.text();
            throw new Error(`Error guardando plan: ${text || `HTTP ${respGuardar.status}`}`);
        }
        
        const dataGuardado = await respGuardar.json();
        console.log(`✅ Plan guardado. ID: ${dataGuardado.id}`);
        
        // Actualizar mensaje de loading
        if (loadingText) {
            loadingText.textContent = 'Redirigiendo a la edición del plan...';
        }
        
        // Redirigir a la pantalla de edición del plan
        const detalleUrl = `/admin/planes/${dataGuardado.id}`;
        console.log(`🔀 Redirigiendo a: ${detalleUrl}`);
        
        // Mostrar configuración recomendada del motor antes de redirigir
        mostrarConfiguracionRecomendada(planGenerado);
        
        // Ocultar loading
        ocultarLoadingGeneracion();
        
        // Pequeño delay para que se vea la configuración recomendada antes de redirigir
        setTimeout(() => {
            window.location.href = detalleUrl;
        }, 2000);  // Aumentado a 2 segundos para que se vea la configuración
        
    } catch (error) {
        console.error('Error generando plan:', error);
        
        // Ocultar loading
        ocultarLoadingGeneracion();
        
        // Mostrar error
        Toastify({
            text: `❌ Error generando plan: ${error.message}`,
            duration: 5000,
            gravity: "top",
            position: "right",
            backgroundColor: "#ef4444"
        }).showToast();
    }
}

// ============ FUNCIONES AUXILIARES PARA GENERACIÓN DE PLAN ============

function mostrarConfiguracionRecomendada(planGenerado) {
    const card = document.getElementById('configRecomendadaCard');
    const content = document.getElementById('configRecomendadaContent');
    
    if (!card || !content) return;
    
    if (!planGenerado.metas_nutricionales) {
        card.style.display = 'none';
        return;
    }
    
    const metas = planGenerado.metas_nutricionales;
    const debugML = planGenerado.debug_ml || {};
    
    // Calcular gramos de macronutrientes
    const kcal = metas.calorias_diarias || 0;
    const choG = metas.carbohidratos_g || Math.round((kcal * (metas.carbohidratos_porcentaje || 0) / 100) / 4);
    const proG = metas.proteinas_g || Math.round((kcal * (metas.proteinas_porcentaje || 0) / 100) / 4);
    const fatG = metas.grasas_g || Math.round((kcal * (metas.grasas_porcentaje || 0) / 100) / 9);
    const fibraG = metas.fibra_g || 0;
    
    content.innerHTML = `
        <div style="padding: 12px; background: #f0f9ff; border-left: 4px solid #3b82f6; border-radius: 6px;">
            <div style="font-weight: 600; color: #1e40af; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-fire"></i> Calorías Diarias
            </div>
            <div style="font-size: 18px; font-weight: 700; color: #1e3a8a;">
                ${kcal.toLocaleString()} kcal
            </div>
        </div>
        <div style="padding: 12px; background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 6px;">
            <div style="font-weight: 600; color: #065f46; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-bread-slice"></i> Carbohidratos
            </div>
            <div style="font-size: 18px; font-weight: 700; color: #047857;">
                ${metas.carbohidratos_porcentaje || 0}% (${choG}g)
            </div>
        </div>
        <div style="padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
            <div style="font-weight: 600; color: #92400e; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-drumstick-bite"></i> Proteínas
            </div>
            <div style="font-size: 18px; font-weight: 700; color: #78350f;">
                ${metas.proteinas_porcentaje || 0}% (${proG}g)
            </div>
        </div>
        <div style="padding: 12px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 6px;">
            <div style="font-weight: 600; color: #991b1b; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-oil-can"></i> Grasas
            </div>
            <div style="font-size: 18px; font-weight: 700; color: #7f1d1d;">
                ${metas.grasas_porcentaje || 0}% (${fatG}g)
            </div>
        </div>
        <div style="padding: 12px; background: #f3e8ff; border-left: 4px solid #8b5cf6; border-radius: 6px;">
            <div style="font-weight: 600; color: #6b21a8; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-leaf"></i> Fibra
            </div>
            <div style="font-size: 18px; font-weight: 700; color: #581c87;">
                ${fibraG}g
            </div>
        </div>
        ${debugML.probabilidad_mal_control !== undefined ? `
        <div style="padding: 12px; background: #fce7f3; border-left: 4px solid #ec4899; border-radius: 6px;">
            <div style="font-weight: 600; color: #9f1239; margin-bottom: 8px; font-size: 14px;">
                <i class="fas fa-brain"></i> Control Glucémico (ML)
            </div>
            <div style="font-size: 14px; color: #831843;">
                Probabilidad mal control: ${((debugML.probabilidad_ajustada || debugML.probabilidad_mal_control || 0) * 100).toFixed(1)}%
            </div>
            <div style="font-size: 12px; color: #9f1239; margin-top: 4px;">
                ${(debugML.probabilidad_ajustada || debugML.probabilidad_mal_control || 0) > 0.6 ? '⚠️ Control glucémico MALO' : 
                  (debugML.probabilidad_ajustada || debugML.probabilidad_mal_control || 0) > 0.4 ? '⚡ Control glucémico MODERADO' : 
                  '✅ Control glucémico BUENO'}
            </div>
        </div>
        ` : ''}
    `;
    
    card.style.display = 'block';
}

function convertirPlanMotorAFormatoUI(planMotor) {
    // Convertir el formato del motor al formato esperado por la UI
    console.log('🔄 Convirtiendo plan del motor...');
    console.log('🔍 Plan completo recibido:', planMotor);
    console.log('🔍 Estructura del plan:', Object.keys(planMotor));
    
    // Verificar si hay error en la respuesta
    if (planMotor.error) {
        console.error('❌ Error en la respuesta del motor:', planMotor.error);
        throw new Error(`Error del motor: ${planMotor.error}`);
    }
    
    // El motor puede devolver datos en diferentes formatos
    let planSemanal = planMotor.plan_semanal || planMotor.plan_completo;
    let comidas = planMotor.comidas;
    
    // Si el plan_semanal está dentro de otra estructura, extraerlo
    if (!planSemanal && planMotor.plan_semanal) {
        planSemanal = planMotor.plan_semanal;
    }
    
    console.log('🔍 planSemanal encontrado:', !!planSemanal);
    console.log('🔍 comidas encontradas:', !!comidas);
    
    if (planSemanal) {
        console.log('🔍 Claves de planSemanal:', Object.keys(planSemanal));
    }
    
    // Si no hay plan_semanal pero hay comidas, crear estructura
    if (!planSemanal && comidas) {
        console.log('📝 Creando estructura desde comidas...');
        console.log('📝 Comidas recibidas:', comidas);
        // Crear estructura básica para los días
        const diasPlan = Math.ceil(planMotor.dias_plan || 7);
        planSemanal = {};
        
        for (let i = 1; i <= diasPlan; i++) {
            planSemanal[`dia_${i}`] = {
                fecha: `2025-10-${19 + i}`,
                des: comidas.des || comidas.desayuno,
                mm: comidas.mm || comidas.media_manana,
                alm: comidas.alm || comidas.almuerzo,
                mt: comidas.mt || comidas.media_tarde,
                cena: comidas.cena
            };
        }
    }
    
    if (!planSemanal) {
        console.error('❌ No se encontró plan_semanal ni comidas en la respuesta del motor');
        console.error('❌ Estructura completa recibida:', JSON.stringify(planMotor, null, 2));
        throw new Error('No se encontró plan_semanal ni comidas en la respuesta del motor');
    }
    
    const dias = Object.keys(planSemanal).length;
    
    // Crear estructura de semanas
    const semanas = [];
    const diasPorSemana = 7;
    const totalSemanas = Math.ceil(dias / diasPorSemana);
    
    for (let semana = 0; semana < totalSemanas; semana++) {
        const diasSemana = [];
        const inicioSemana = semana * diasPorSemana;
        const finSemana = Math.min((semana + 1) * diasPorSemana, dias);
        
        for (let dia = inicioSemana; dia < finSemana; dia++) {
            const diaKey = `dia_${dia + 1}`;
            const diaPlan = planSemanal[diaKey];
            
            if (diaPlan) {
                console.log(`🔄 Procesando día ${dia + 1}:`, diaPlan);
                
                // Convertir estructura de comidas del motor a formato UI
                const comidas = {};
                
                // Mapear las comidas del motor al formato esperado
                if (diaPlan.des || diaPlan.desayuno) {
                    const desayuno = diaPlan.des || diaPlan.desayuno;
                    console.log(`🍳 Desayuno encontrado:`, desayuno);
                    comidas.desayuno = {
                        nombre: "Desayuno",
                        horario: "07:00",
                        alimentos: convertirAlimentosMotor(desayuno.alimentos_sugeridos || desayuno.alimentos || [])
                    };
                }
                
                if (diaPlan.mm || diaPlan.media_manana) {
                    const mediaManana = diaPlan.mm || diaPlan.media_manana;
                    console.log(`🥤 Media mañana encontrada:`, mediaManana);
                    comidas.media_manana = {
                        nombre: "Media Mañana",
                        horario: "10:00",
                        alimentos: convertirAlimentosMotor(mediaManana.alimentos_sugeridos || mediaManana.alimentos || [])
                    };
                }
                
                if (diaPlan.alm || diaPlan.almuerzo) {
                    const almuerzo = diaPlan.alm || diaPlan.almuerzo;
                    console.log(`🍽️ Almuerzo encontrado:`, almuerzo);
                    comidas.almuerzo = {
                        nombre: "Almuerzo",
                        horario: "12:00",
                        alimentos: convertirAlimentosMotor(almuerzo.alimentos_sugeridos || almuerzo.alimentos || [])
                    };
                }
                
                if (diaPlan.mt || diaPlan.media_tarde) {
                    const mediaTarde = diaPlan.mt || diaPlan.media_tarde;
                    console.log(`🍎 Media tarde encontrada:`, mediaTarde);
                    comidas.media_tarde = {
                        nombre: "Media Tarde",
                        horario: "15:00",
                        alimentos: convertirAlimentosMotor(mediaTarde.alimentos_sugeridos || mediaTarde.alimentos || [])
                    };
                }
                
                if (diaPlan.cena) {
                    console.log(`🌙 Cena encontrada:`, diaPlan.cena);
                    comidas.cena = {
                        nombre: "Cena",
                        horario: "19:00",
                        alimentos: convertirAlimentosMotor(diaPlan.cena.alimentos_sugeridos || diaPlan.cena.alimentos || [])
                    };
                }
                
                console.log(`✅ Comidas procesadas para día ${dia + 1}:`, comidas);
                
                diasSemana.push({
                    numero: dia + 1,
                    fecha: diaPlan.fecha || `2025-10-${20 + dia}`,
                    comidas: comidas
                });
            }
        }
        
        if (diasSemana.length > 0) {
            semanas.push({
                numero: semana + 1,
                dias: diasSemana
            });
        }
    }
    
    return {
        dias: dias,
        semanas: semanas
    };
}

function convertirAlimentosMotor(alimentosMotor) {
    // Convertir alimentos del formato del motor al formato de la UI
    if (!alimentosMotor || !Array.isArray(alimentosMotor)) {
        return [];
    }
    
    return alimentosMotor.map(alimento => {
        if (alimento.ingrediente && alimento.cantidad_sugerida) {
            // Formato del motor: {ingrediente: {...}, cantidad_sugerida: 120, unidad: "g"}
            const ing = alimento.ingrediente;
            const cantidad = alimento.cantidad_sugerida;
            const unidad = alimento.unidad || 'g';
            
            // Calcular valores nutricionales si están disponibles
            const factor = cantidad / 100.0;
            const kcal = ing.kcal ? (ing.kcal * factor) : null;
            const cho = ing.cho ? (ing.cho * factor) : null;
            const pro = ing.pro ? (ing.pro * factor) : null;
            const fat = ing.fat ? (ing.fat * factor) : null;
            const fibra = ing.fibra ? (ing.fibra * factor) : null;
            
            return {
                nombre: ing.nombre,
                ingrediente_id: ing.id, // Incluir ID para facilitar la búsqueda
                cantidad: `${cantidad}${unidad}`,
                cantidad_num: cantidad, // Guardar número para facilitar parsing
                unidad: unidad,
                grupo: ing.grupo,
                kcal: kcal ? Math.round(kcal * 100) / 100 : null,
                cho: cho ? Math.round(cho * 100) / 100 : null,
                pro: pro ? Math.round(pro * 100) / 100 : null,
                fat: fat ? Math.round(fat * 100) / 100 : null,
                fibra: fibra ? Math.round(fibra * 100) / 100 : null
            };
        } else if (alimento.nombre && alimento.cantidad) {
            // Formato ya convertido: {nombre: "...", cantidad: "120g"}
            return alimento;
        } else {
            // Formato simple: {nombre: "...", cantidad: "120g"}
            return {
                nombre: alimento.nombre || 'Alimento',
                cantidad: alimento.cantidad || '1 porción'
            };
        }
    });
}

function generarPlanPrueba() {
    // Datos de prueba para mostrar la funcionalidad
    return {
        dias: 2, // Solo 2 días para simplificar
        semanas: [
            {
                numero: 1,
                dias: [
                    {
                        numero: 1,
                        fecha: "2025-10-20",
                        comidas: {
                            desayuno: {
                                nombre: "Desayuno",
                                horario: "07:00",
                                alimentos: [
                                    { nombre: "Avena", cantidad: "1 taza", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Leche descremada", cantidad: "1 vaso", grupo: "GRUPO4_LACTEOS" },
                                    { nombre: "Plátano", cantidad: "1 unidad", grupo: "GRUPO3_FRUTAS" }
                                ]
                            },
                            media_manana: {
                                nombre: "Media Mañana",
                                horario: "10:00",
                                alimentos: [
                                    { nombre: "Yogurt griego", cantidad: "1 envase", grupo: "GRUPO4_LACTEOS" },
                                    { nombre: "Nueces", cantidad: "10 unidades", grupo: "GRUPO7_GRASAS" }
                                ]
                            },
                            almuerzo: {
                                nombre: "Almuerzo",
                                horario: "12:00",
                                alimentos: [
                                    { nombre: "Pollo a la plancha", cantidad: "150g", grupo: "GRUPO5_CARNES" },
                                    { nombre: "Arroz integral", cantidad: "1/2 taza", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Ensalada de lechuga", cantidad: "1 taza", grupo: "GRUPO2_VERDURAS" }
                                ]
                            },
                            media_tarde: {
                                nombre: "Media Tarde",
                                horario: "15:00",
                                alimentos: [
                                    { nombre: "Manzana", cantidad: "1 unidad", grupo: "GRUPO3_FRUTAS" },
                                    { nombre: "Almendras", cantidad: "15 unidades", grupo: "GRUPO7_GRASAS" }
                                ]
                            },
                            cena: {
                                nombre: "Cena",
                                horario: "19:00",
                                alimentos: [
                                    { nombre: "Salmón", cantidad: "120g", grupo: "GRUPO5_CARNES" },
                                    { nombre: "Quinoa", cantidad: "1/2 taza", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Brócoli al vapor", cantidad: "1 taza", grupo: "GRUPO2_VERDURAS" }
                                ]
                            }
                        }
                    },
                    {
                        numero: 2,
                        fecha: "2025-10-21",
                        comidas: {
                            desayuno: {
                                nombre: "Desayuno",
                                horario: "07:00",
                                alimentos: [
                                    { nombre: "Huevos revueltos", cantidad: "2 unidades", grupo: "GRUPO5_CARNES" },
                                    { nombre: "Pan integral", cantidad: "1 rebanada", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Aguacate", cantidad: "1/2 unidad", grupo: "GRUPO7_GRASAS" }
                                ]
                            },
                            media_manana: {
                                nombre: "Media Mañana",
                                horario: "10:00",
                                alimentos: [
                                    { nombre: "Fresas", cantidad: "1 taza", grupo: "GRUPO3_FRUTAS" },
                                    { nombre: "Yogurt natural", cantidad: "1 envase", grupo: "GRUPO4_LACTEOS" }
                                ]
                            },
                            almuerzo: {
                                nombre: "Almuerzo",
                                horario: "12:00",
                                alimentos: [
                                    { nombre: "Pescado blanco", cantidad: "150g", grupo: "GRUPO5_CARNES" },
                                    { nombre: "Batata asada", cantidad: "1 unidad mediana", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Espinacas", cantidad: "1 taza", grupo: "GRUPO2_VERDURAS" }
                                ]
                            },
                            media_tarde: {
                                nombre: "Media Tarde",
                                horario: "15:00",
                                alimentos: [
                                    { nombre: "Pera", cantidad: "1 unidad", grupo: "GRUPO3_FRUTAS" },
                                    { nombre: "Queso cottage", cantidad: "1/2 taza", grupo: "GRUPO4_LACTEOS" }
                                ]
                            },
                            cena: {
                                nombre: "Cena",
                                horario: "19:00",
                                alimentos: [
                                    { nombre: "Pechuga de pavo", cantidad: "120g", grupo: "GRUPO5_CARNES" },
                                    { nombre: "Lentejas", cantidad: "1/2 taza", grupo: "GRUPO1_CEREALES" },
                                    { nombre: "Zanahorias al vapor", cantidad: "1 taza", grupo: "GRUPO2_VERDURAS" }
                                ]
                            }
                        }
                    }
                ]
            }
        ]
    };
}

function validarConfiguracionPlan() {
    const camposRequeridos = [
        { id: 'kcal_objetivo', nombre: 'Calorías objetivo' },
        { id: 'cho_pct', nombre: 'Carbohidratos (%)' },
        { id: 'pro_pct', nombre: 'Proteínas (%)' },
        { id: 'fat_pct', nombre: 'Grasas (%)' },
        { id: 'ig_max', nombre: 'Índice Glucémico máximo' },
        { id: 'max_repeticiones', nombre: 'Repeticiones máximas' },
        { id: 'fecha_inicio', nombre: 'Fecha de inicio' },
        { id: 'fecha_fin', nombre: 'Fecha de fin' }
    ];
    
    for (const campo of camposRequeridos) {
        const elemento = document.getElementById(campo.id);
        if (!elemento || !elemento.value.trim()) {
            return {
                valida: false,
                mensaje: `El campo "${campo.nombre}" es requerido`
            };
        }
    }
    
    return { valida: true };
}

function recopilarDatosPlan(pacienteId) {
    const rangoFechas = obtenerRangoFechas();
    const patronComidas = obtenerPatronComidas();
    
    // Obtener configuración original guardada (propuesta por el sistema)
    let configuracionOriginal = null;
    const formConfig = document.getElementById('formConfiguracionPlan') || document.body;
    if (formConfig.dataset.configuracionOriginal) {
        try {
            configuracionOriginal = JSON.parse(formConfig.dataset.configuracionOriginal);
            console.log('📋 Enviando configuración original al backend:', configuracionOriginal);
        } catch (e) {
            console.warn('⚠️ No se pudo parsear configuración original:', e);
        }
    }
    
    return {
        paciente_id: parseInt(pacienteId),
        configuracion: {
            fecha_inicio: rangoFechas.fechaInicio,
            fecha_fin: rangoFechas.fechaFin,
            dias_plan: rangoFechas.dias,
            kcal_objetivo: parseInt(document.getElementById('kcal_objetivo').value),
            cho_pct: parseInt(document.getElementById('cho_pct').value),
            pro_pct: parseInt(document.getElementById('pro_pct').value),
            fat_pct: parseInt(document.getElementById('fat_pct').value),
            ig_max: parseInt(document.getElementById('ig_max').value),
            max_repeticiones: parseInt(document.getElementById('max_repeticiones').value),
            patron_comidas: patronComidas
        },
        configuracion_original: configuracionOriginal, // Configuración propuesta por el sistema (antes del ajuste ML)
        ingredientes: {
            incluir: ingredientesIncluir,
            excluir: ingredientesExcluir,
            grupos_excluidos: gruposExcluidos
        }
    };
}

function mostrarLoadingGeneracion() {
    const btnGenerar = document.getElementById('btnGenerar');
    if (btnGenerar) {
        btnGenerar.disabled = true;
        btnGenerar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    }
    
    // Mostrar overlay de loading con animación
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
        
        // Simular progreso de carga
        const progressBar = document.getElementById('loading-progress');
        if (progressBar) {
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90; // No llegar al 100% hasta que termine
                progressBar.style.width = progress + '%';
            }, 300);
            
            // Guardar el interval para limpiarlo después
            loadingOverlay.dataset.intervalId = interval;
        }
    }
}

function ocultarLoadingGeneracion() {
    const btnGenerar = document.getElementById('btnGenerar');
    if (btnGenerar) {
        btnGenerar.disabled = false;
        btnGenerar.innerHTML = '<i class="fas fa-magic"></i> Generar Plan Nutricional';
    }
    
    // Ocultar overlay de loading
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        // Completar la barra de progreso
        const progressBar = document.getElementById('loading-progress');
        if (progressBar) {
            progressBar.style.width = '100%';
        }
        
        // Limpiar interval si existe
        if (loadingOverlay.dataset.intervalId) {
            clearInterval(parseInt(loadingOverlay.dataset.intervalId));
        }
        
        // Ocultar después de un breve delay para mostrar el 100%
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
            if (progressBar) {
                progressBar.style.width = '0%';
            }
        }, 500);
    }
}

function mostrarPlanGenerado(plan) {
    console.log('📋 Plan generado recibido:', plan);
    
    // Mostrar la sección de preview del plan
    const seccionPreview = document.getElementById('seccion-preview');
    if (seccionPreview) {
        seccionPreview.style.display = 'block';
        console.log('✅ Sección de preview mostrada');
    } else {
        console.error('❌ No se encontró la sección de preview');
    }
    
    // Crear los controles de visualización
    crearControlesVisualizacion(plan);
    
    // Mostrar el plan en formato horario
    mostrarPlanFormatoHorario(plan, 1);
    // Habilitar acciones (guardar/publicar/pdf)
    habilitarAccionesPlan(true);
}

function crearControlesVisualizacion(plan) {
    const controlesContainer = document.getElementById('controles-visualizacion');
    if (!controlesContainer) return;
    
    const totalSemanas = Math.ceil(plan.dias / 7);
    
    controlesContainer.innerHTML = `
        <div class="plan-controls">
            ${totalSemanas > 1 ? `
            <div class="pagination-controls">
                <button class="pagination-btn" id="prevWeek" onclick="cambiarSemana(-1)">
                    <i class="fas fa-chevron-left"></i> Anterior
                </button>
                <span class="week-info">
                    Semana <span id="currentWeek">1</span> de ${totalSemanas}
                </span>
                <button class="pagination-btn" id="nextWeek" onclick="cambiarSemana(1)">
                    Siguiente <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            ` : ''}
        </div>
    `;
}

// Variables globales para control de visualización
let formatoActual = 'horario';
let semanaActual = 1;

function cambiarSemana(direccion) {
    const totalSemanas = Math.ceil(planActual.dias / 7);
    const nuevaSemana = semanaActual + direccion;
    
    if (nuevaSemana >= 1 && nuevaSemana <= totalSemanas) {
        semanaActual = nuevaSemana;
        
        // Actualizar indicador de semana
        document.getElementById('currentWeek').textContent = semanaActual;
        
        // Actualizar botones de paginación
        document.getElementById('prevWeek').disabled = semanaActual === 1;
        document.getElementById('nextWeek').disabled = semanaActual === totalSemanas;
        
        // Mostrar la semana correspondiente en formato horario
        mostrarPlanFormatoHorario(planActual, semanaActual);
    }
}

function mostrarPlanFormatoHorario(plan, semana) {
    const container = document.getElementById('plan-content');
    if (!container) return;
    
    const inicioSemana = (semana - 1) * 7 + 1;
    const finSemana = Math.min(semana * 7, plan.dias);
    
    let html = `
        <div class="plan-schedule">
            <div class="leyenda-grupos" style="margin: 0 0 10px 0; display:flex; gap:8px; flex-wrap:wrap;">
                <span style="background:#8b5cf6; color:white; padding:4px 8px; border-radius:6px">Cereales</span>
                <span style="background:#10b981; color:white; padding:4px 8px; border-radius:6px">Verduras</span>
                <span style="background:#f59e0b; color:white; padding:4px 8px; border-radius:6px">Frutas</span>
                <span style="background:#06b6d4; color:white; padding:4px 8px; border-radius:6px">Lácteos</span>
                <span style="background:#ef4444; color:white; padding:4px 8px; border-radius:6px">Carnes</span>
                <span style="background:#ec4899; color:white; padding:4px 8px; border-radius:6px">Azúcares</span>
                <span style="background:#f97316; color:white; padding:4px 8px; border-radius:6px">Grasas</span>
            </div>
            <h4>Semana ${semana} - Horarios de Comidas</h4>
            <div class="schedule-grid">
    `;
    
    // Crear encabezados de días
    html += '<div class="schedule-header"><div class="time-header">Hora</div>';
    for (let dia = inicioSemana; dia <= finSemana; dia++) {
        html += `<div class="day-header">Día ${dia}</div>`;
    }
    html += '</div>';
    
    // Obtener todos los horarios únicos
    const horarios = ['07:00', '10:00', '12:00', '15:00', '19:00'];
    
    horarios.forEach(hora => {
        html += `<div class="schedule-row"><div class="time-cell">${hora}</div>`;
        
        for (let dia = inicioSemana; dia <= finSemana; dia++) {
            const diaPlan = plan.semanas[semana - 1].dias[dia - inicioSemana];
            const comida = Object.values(diaPlan.comidas).find(c => c.horario === hora);
            
            // Determinar el tipo de comida basado en el horario
            let tipoComida = 'meal';
            if (hora === '07:00') tipoComida = 'desayuno';
            else if (hora === '10:00') tipoComida = 'media_manana';
            else if (hora === '12:00') tipoComida = 'almuerzo';
            else if (hora === '15:00') tipoComida = 'media_tarde';
            else if (hora === '19:00') tipoComida = 'cena';
            
            html += `
                <div class="meal-cell">
                    ${comida ? `
                        <div class="meal-info">
                            <strong class="${tipoComida}">${comida.nombre}</strong>
                            <div class="meal-foods">
                                ${comida.alimentos.map(alimento => {
                                    const colorGrupo = obtenerColorGrupo(alimento.grupo);
                                    const colorFondo = obtenerColorFondoGrupo(alimento.grupo);
                                    return `<div style="background: ${colorFondo}; color: ${colorGrupo}; border: 1px solid ${colorGrupo}; padding: 2px 6px; border-radius: 4px; margin: 1px 0; font-size: 10px; font-weight: 500;">${alimento.nombre} - ${alimento.cantidad}</div>`;
                                }).join('')}
                            </div>
                        </div>
                    ` : '<div class="no-meal">—</div>'}
                </div>
            `;
        }
        
        html += '</div>';
    });
    
    html += `
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Aplicar estilos adicionales después de insertar el HTML
    setTimeout(() => {
        aplicarEstilosDinamicos();
    }, 100);
}


// ============ FUNCIÓN PARA APLICAR ESTILOS DINÁMICOS ============

function aplicarEstilosDinamicos() {
    console.log('🎨 Aplicando estilos dinámicos al plan generado...');
    
    // Asegurar que el contenedor principal tenga los estilos correctos
    const planContent = document.getElementById('plan-content');
    if (planContent) {
        planContent.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            margin-top: 16px;
        `;
    }
    
    // Agregar estilos CSS para formato horario y tabla si no existen
    agregarEstilosHorarioTabla();
    
    // Aplicar estilos a elementos específicos si existen
    const planDays = document.querySelectorAll('.plan-day');
    planDays.forEach(day => {
        day.style.cssText = `
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 2px solid #e5e7eb !important;
            border-radius: 12px !important;
            padding: 20px !important;
            margin-bottom: 16px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        `;
    });
    
    const mealSections = document.querySelectorAll('.meal-section');
    mealSections.forEach(section => {
        // Determinar el color según el tipo de comida
        let borderColor = '#3b82f6'; // Color por defecto
        let backgroundColor = 'white';
        
        if (section.classList.contains('desayuno')) {
            borderColor = '#f59e0b';
            backgroundColor = 'linear-gradient(135deg, #fef3c7 0%, #ffffff 100%)';
        } else if (section.classList.contains('media_manana')) {
            borderColor = '#10b981';
            backgroundColor = 'linear-gradient(135deg, #d1fae5 0%, #ffffff 100%)';
        } else if (section.classList.contains('almuerzo')) {
            borderColor = '#ef4444';
            backgroundColor = 'linear-gradient(135deg, #fee2e2 0%, #ffffff 100%)';
        } else if (section.classList.contains('media_tarde')) {
            borderColor = '#8b5cf6';
            backgroundColor = 'linear-gradient(135deg, #ede9fe 0%, #ffffff 100%)';
        } else if (section.classList.contains('cena')) {
            borderColor = '#1f2937';
            backgroundColor = 'linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%)';
        }
        
        section.style.cssText = `
            background: ${backgroundColor} !important;
            border-radius: 8px !important;
            padding: 16px !important;
            border-left: 6px solid ${borderColor} !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
            margin-bottom: 12px !important;
            transition: all 0.2s ease !important;
        `;
    });
    
    const mealItems = document.querySelectorAll('.meal-item');
    mealItems.forEach(item => {
        item.style.cssText = `
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 8px 12px !important;
            background: rgba(255, 255, 255, 0.7) !important;
            border-radius: 6px !important;
            margin-bottom: 6px !important;
            transition: all 0.2s ease !important;
        `;
    });
    
    const foodNames = document.querySelectorAll('.food-name');
    foodNames.forEach(name => {
        name.style.cssText = `
            color: #374151;
            font-weight: 600;
            font-size: 14px;
        `;
    });
    
    const foodQuantities = document.querySelectorAll('.food-quantity');
    foodQuantities.forEach(quantity => {
        quantity.style.cssText = `
            background: #3b82f6 !important;
            color: white !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        `;
    });
    
    // Aplicar estilos específicos por tipo de comida
    const desayunos = document.querySelectorAll('.meal-section.desayuno');
    desayunos.forEach(section => {
        section.style.borderLeftColor = '#f59e0b !important';
        section.style.background = 'linear-gradient(135deg, #fef3c7 0%, #ffffff 100%) !important';
    });
    
    const mediaMananas = document.querySelectorAll('.meal-section.media_manana');
    mediaMananas.forEach(section => {
        section.style.borderLeftColor = '#10b981 !important';
        section.style.background = 'linear-gradient(135deg, #d1fae5 0%, #ffffff 100%) !important';
    });
    
    const almuerzos = document.querySelectorAll('.meal-section.almuerzo');
    almuerzos.forEach(section => {
        section.style.borderLeftColor = '#ef4444 !important';
        section.style.background = 'linear-gradient(135deg, #fee2e2 0%, #ffffff 100%) !important';
    });
    
    const mediaTardes = document.querySelectorAll('.meal-section.media_tarde');
    mediaTardes.forEach(section => {
        section.style.borderLeftColor = '#8b5cf6 !important';
        section.style.background = 'linear-gradient(135deg, #ede9fe 0%, #ffffff 100%) !important';
    });
    
    const cenas = document.querySelectorAll('.meal-section.cena');
    cenas.forEach(section => {
        section.style.borderLeftColor = '#1f2937 !important';
        section.style.background = 'linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%) !important';
    });
    
    console.log('✅ Estilos dinámicos aplicados correctamente');
}

// ============ FUNCIÓN PARA AGREGAR ESTILOS CSS DE HORARIO Y TABLA ============

function agregarEstilosHorarioTabla() {
    // Verificar si los estilos ya existen
    if (document.getElementById('plan-horario-tabla-styles')) {
        return;
    }
    
    console.log('🎨 Agregando estilos CSS para formato horario y tabla...');
    
    const style = document.createElement('style');
    style.id = 'plan-horario-tabla-styles';
    style.textContent = `
        /* ============ ESTILOS PARA FORMATO HORARIO ============ */
        .plan-schedule {
            margin-top: 16px !important;
        }

        .plan-schedule h4 {
            color: #1f2937 !important;
            margin-bottom: 20px !important;
            padding-bottom: 12px !important;
            border-bottom: 3px solid #1f2937 !important;
            font-size: 20px !important;
            font-weight: 700 !important;
        }

        .schedule-grid {
            border: 2px solid #e5e7eb !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            background: white !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        }

        .schedule-header {
            display: grid !important;
            grid-template-columns: 80px repeat(7, 1fr) !important;
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
            border-bottom: 2px solid #e5e7eb !important;
        }

        .time-header, .day-header {
            padding: 16px 8px !important;
            text-align: center !important;
            font-weight: 700 !important;
            color: white !important;
            border-right: 1px solid rgba(255, 255, 255, 0.2) !important;
            font-size: 14px !important;
        }

        .schedule-row {
            display: grid !important;
            grid-template-columns: 80px repeat(7, 1fr) !important;
            border-bottom: 1px solid #e5e7eb !important;
            transition: background-color 0.2s ease !important;
        }

        .schedule-row:hover {
            background: #f8fafc !important;
        }

        .schedule-row:nth-child(even) {
            background: #f9fafb !important;
        }

        .time-cell {
            padding: 16px 8px !important;
            text-align: center !important;
            font-weight: 600 !important;
            color: #374151 !important;
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%) !important;
            border-right: 1px solid #e5e7eb !important;
            font-size: 14px !important;
        }

        .meal-cell {
            padding: 12px 8px !important;
            border-right: 1px solid #e5e7eb !important;
            min-height: 80px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        .meal-info {
            font-size: 12px !important;
            text-align: center !important;
            width: 100% !important;
        }

        .meal-info strong {
            color: #1f2937 !important;
            display: block !important;
            margin-bottom: 6px !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            padding: 4px 8px !important;
            background: #3b82f6 !important;
            color: white !important;
            border-radius: 4px !important;
        }

        .meal-foods {
            color: #374151 !important;
            font-size: 11px !important;
            line-height: 1.4 !important;
        }

        .meal-foods div {
            margin: 2px 0 !important;
            padding: 2px 6px !important;
            background: rgba(59, 130, 246, 0.1) !important;
            border-radius: 3px !important;
            font-weight: 500 !important;
        }

        .no-meal {
            text-align: center !important;
            color: #9ca3af !important;
            font-style: italic !important;
            font-size: 12px !important;
        }

        /* Colores específicos por tipo de comida en horario */
        .meal-cell .meal-info strong.desayuno {
            background: #f59e0b !important;
            color: white !important;
        }

        .meal-cell .meal-info strong.media_manana {
            background: #10b981 !important;
            color: white !important;
        }

        .meal-cell .meal-info strong.almuerzo {
            background: #ef4444 !important;
            color: white !important;
        }

        .meal-cell .meal-info strong.media_tarde {
            background: #8b5cf6 !important;
            color: white !important;
        }

        .meal-cell .meal-info strong.cena {
            background: #1f2937 !important;
            color: white !important;
        }

        .meal-cell .meal-info strong.meal {
            background: #6b7280 !important;
            color: white !important;
        }

        /* ============ ESTILOS PARA FORMATO TABLA ============ */
        .plan-table {
            margin-top: 16px !important;
        }

        .plan-table h4 {
            color: #1f2937 !important;
            margin-bottom: 20px !important;
            padding-bottom: 12px !important;
            border-bottom: 3px solid #1f2937 !important;
            font-size: 20px !important;
            font-weight: 700 !important;
        }

        .weekly-table {
            width: 100% !important;
            border-collapse: collapse !important;
            background: white !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            border: 2px solid #e5e7eb !important;
        }

        .weekly-table th {
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
            color: white !important;
            padding: 16px 8px !important;
            text-align: center !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            border-right: 1px solid rgba(255, 255, 255, 0.2) !important;
        }

        .weekly-table th:first-child {
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
        }

        .weekly-table td {
            padding: 16px 8px !important;
            border: 1px solid #e5e7eb !important;
            text-align: center !important;
            font-size: 13px !important;
            vertical-align: top !important;
            transition: background-color 0.2s ease !important;
        }

        .weekly-table tr:hover td {
            background: #f8fafc !important;
        }

        .weekly-table tr:nth-child(even) td {
            background: #f9fafb !important;
        }

        .day-cell {
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%) !important;
            font-weight: 700 !important;
            color: #374151 !important;
            font-size: 14px !important;
            border-right: 2px solid #d1d5db !important;
        }

        .meal-cell {
            color: #374151 !important;
            line-height: 1.6 !important;
            font-weight: 500 !important;
        }

        .meal-cell span {
            display: inline-block !important;
            margin: 2px !important;
            padding: 4px 8px !important;
            background: rgba(59, 130, 246, 0.1) !important;
            border-radius: 4px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            border-left: 3px solid #3b82f6 !important;
        }

        /* ============ ESTILOS RESPONSIVOS ============ */
        @media (max-width: 768px) {
            .schedule-header,
            .schedule-row {
                grid-template-columns: 60px repeat(3, 1fr) !important;
            }

            .time-header,
            .day-header,
            .time-cell,
            .meal-cell {
                padding: 8px 4px !important;
                font-size: 12px !important;
            }

            .weekly-table {
                font-size: 12px !important;
            }

            .weekly-table th,
            .weekly-table td {
                padding: 8px 4px !important;
            }
        }
    `;
    
    document.head.appendChild(style);
    console.log('✅ Estilos CSS para horario y tabla agregados correctamente');
}

// ============ INICIALIZACIÓN ============

function inicializarListasIngredientes() {
    // Inicializar las listas de ingredientes con el mensaje de estado vacío
    actualizarListaIngredientes('incluir');
    actualizarListaIngredientes('excluir');
}

function inicializarFechas() {
    // Establecer fecha actual como fecha de inicio por defecto
    const hoy = new Date();
    const fechaHoy = hoy.toISOString().split('T')[0];
    
    const campoFechaInicio = document.getElementById('fecha_inicio');
    if (campoFechaInicio) {
        campoFechaInicio.value = fechaHoy;
        console.log('📅 Fecha de inicio establecida:', fechaHoy);
    }
}

function limpiarConfiguracionPlan() {
    // Limpiar campos de configuración del plan
    const camposConfiguracion = [
        'kcal_objetivo', 'cho_pct', 'pro_pct', 'fat_pct', 
        'ig_max', 'max_repeticiones'
    ];
    
    camposConfiguracion.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.value = '';
            campo.placeholder = 'Generar recomendación';
            console.log(`🧹 Campo ${id} limpiado`);
        } else {
            console.error(`❌ Elemento ${id} no encontrado para limpiar`);
        }
    });
}

function limpiarTodosLosCampos() {
    console.log('🧹 Limpiando todos los campos del formulario...');
    
    // Limpiar datos del paciente
    const camposPersonales = ['paciente_id', 'p_dni', 'p_nombres', 'p_apellidos', 'p_sexo', 'p_fnac', 'p_tel', 'p_email'];
    camposPersonales.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.value = '';
            console.log(`🧹 Campo ${id} limpiado`);
        }
    });
    
    // Limpiar datos de antropometría
    const camposAntropometria = ['p_peso', 'p_talla', 'p_cintura', 'p_grasa', 'p_actividad', 'p_fecha_antropo'];
    camposAntropometria.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.value = '';
            console.log(`🧹 Campo ${id} limpiado`);
        }
    });
    
    // Limpiar datos clínicos
    const camposClinicos = ['p_hba1c', 'p_glucosa', 'p_ldl', 'p_pa_sis', 'p_pa_dia', 'p_fecha_clinico'];
    camposClinicos.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.value = '';
            console.log(`🧹 Campo ${id} limpiado`);
        }
    });
    
    // Limpiar configuración del plan
    limpiarConfiguracionPlan();
    
    // Limpiar fechas
    const hoy = new Date();
    const fechaHoy = hoy.toISOString().split('T')[0];
    document.getElementById('fecha_inicio').value = fechaHoy;
    document.getElementById('fecha_fin').value = '';
    document.getElementById('dias_plan').value = '';
    
    // Limpiar grupos excluidos
    const checkboxesGrupos = document.querySelectorAll('.grupos-exclusion input[type="checkbox"]');
    checkboxesGrupos.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Restablecer patrones de comidas por defecto
    document.getElementById('comida_des').checked = true;
    document.getElementById('comida_mm').checked = false;
    document.getElementById('comida_alm').checked = true;
    document.getElementById('comida_mt').checked = false;
    document.getElementById('comida_cena').checked = true;
    
    // Limpiar listas de ingredientes
    ingredientesIncluir.length = 0;
    ingredientesExcluir.length = 0;
    gruposExcluidos.length = 0;
    limpiarDropdownsIngredientes();
    actualizarListaIngredientes('incluir');
    actualizarListaIngredientes('excluir');
    
    // Deshabilitar botones
    const btnGenerar = document.getElementById('btnGenerar');
    if (btnGenerar) btnGenerar.disabled = true;
    
    const btnMotorRecomendacion = document.getElementById('btnMotorRecomendacion');
    if (btnMotorRecomendacion) btnMotorRecomendacion.disabled = true;
    
    console.log('✅ Todos los campos limpiados correctamente');
}

function llenarConfiguracionPlanPorDefecto() {
    // Obtener datos del paciente para calcular valores personalizados
    const peso = parseFloat(document.getElementById('p_peso').value) || 0;
    const talla = parseFloat(document.getElementById('p_talla').value) || 0;
    const edad = calcularEdad(document.getElementById('p_fnac').value);
    const sexo = document.getElementById('p_sexo').value;
    const actividad = document.getElementById('p_actividad').value;
    const hba1c = parseFloat(document.getElementById('p_hba1c').value) || 0;
    
    console.log('🤖 Calculando configuración personalizada para:', {
        peso, talla, edad, sexo, actividad, hba1c
    });
    
    // Calcular IMC
    const imc = talla > 0 ? peso / (talla * talla) : 0;
    
    // Calcular calorías basadas en TMB y actividad
    const calorias = calcularCaloriasBasales(peso, talla, edad, sexo, actividad);
    
    // Calcular macronutrientes basados en perfil del paciente
    const glucosa = parseFloat(document.getElementById('p_glucosa').value) || 0;
    const macronutrientes = calcularMacronutrientes(imc, hba1c, edad, sexo, glucosa);
    
    // Calcular índice glucémico máximo
    const igMax = calcularIGMaximo(hba1c, imc);
    
    // Calcular repeticiones máximas
    const maxRepeticiones = calcularMaxRepeticiones(edad, actividad);
    
    // Guardar configuración original propuesta por el sistema (ANTES de cualquier ajuste ML)
    const configuracionOriginal = {
        kcal_objetivo: calorias,
        cho_pct: macronutrientes.cho,
        pro_pct: macronutrientes.pro,
        fat_pct: macronutrientes.fat
    };
    
    // Guardar en un atributo data del formulario para usarlo después
    const formConfig = document.getElementById('formConfiguracionPlan') || document.body;
    formConfig.dataset.configuracionOriginal = JSON.stringify(configuracionOriginal);
    console.log('💾 Configuración original guardada:', configuracionOriginal);
    
    // Llenar campos con valores calculados
    const campos = {
        'kcal_objetivo': { value: calorias, placeholder: 'Auto' },
        'cho_pct': { value: macronutrientes.cho, placeholder: '' },
        'pro_pct': { value: macronutrientes.pro, placeholder: '' },
        'fat_pct': { value: macronutrientes.fat, placeholder: '' },
        'ig_max': { value: igMax, placeholder: '' },
        'max_repeticiones': { value: maxRepeticiones, placeholder: '' }
    };
    
    for (const [id, config] of Object.entries(campos)) {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.value = config.value;
            if (config.placeholder) {
                elemento.placeholder = config.placeholder;
            }
            console.log(`✅ Campo ${id} configurado: ${config.value}`);
        } else {
            console.error(`❌ Elemento ${id} no encontrado en el DOM`);
        }
    }
    
    console.log('⚙️ Configuración del plan personalizada establecida');
}

function calcularEdad(fechaNacimiento) {
    if (!fechaNacimiento) return 30; // Edad por defecto
    
    const hoy = new Date();
    const nacimiento = new Date(fechaNacimiento);
    let edad = hoy.getFullYear() - nacimiento.getFullYear();
    const mes = hoy.getMonth() - nacimiento.getMonth();
    
    if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
        edad--;
    }
    
    return edad;
}

function calcularCaloriasBasales(peso, talla, edad, sexo, actividad) {
    if (peso <= 0 || talla <= 0) return 2000; // Valor por defecto
    
    // Fórmula de Harris-Benedict
    let tmb;
    if (sexo === 'M') {
        tmb = 88.362 + (13.397 * peso) + (4.799 * talla * 100) - (5.677 * edad);
    } else {
        tmb = 447.593 + (9.247 * peso) + (3.098 * talla * 100) - (4.330 * edad);
    }
    
    // Factor de actividad
    const factoresActividad = {
        'baja': 1.2,
        'moderada': 1.375,
        'alta': 1.55
    };
    
    const factor = factoresActividad[actividad] || 1.2;
    const caloriasMantenimiento = Math.round(tmb * factor);
    
    // Calcular IMC
    const imc = talla > 0 ? peso / (talla * talla) : 0;
    
    // Aplicar déficit calórico para pérdida de peso si hay obesidad
    let calorias = caloriasMantenimiento;
    if (imc >= 35) {
        // Obesidad grado II/III: déficit del 25%
        calorias = Math.round(caloriasMantenimiento * 0.75);
        console.log(`📉 Obesidad severa (IMC ${imc.toFixed(2)}): aplicando déficit del 25% para pérdida de peso`);
    } else if (imc >= 30) {
        // Obesidad grado I: déficit del 20%
        calorias = Math.round(caloriasMantenimiento * 0.80);
        console.log(`📉 Obesidad (IMC ${imc.toFixed(2)}): aplicando déficit del 20% para pérdida de peso`);
    }
    
    console.log(`🔥 Calorías calculadas: TMB=${Math.round(tmb)}, Factor=${factor}, Mantenimiento=${caloriasMantenimiento}, Final=${calorias}`);
    return calorias;
}

function calcularMacronutrientes(imc, hba1c, edad, sexo, glucosa = 0) {
    let cho = 50; // Porcentaje por defecto
    let pro = 18; // Porcentaje por defecto
    let fat = 32; // Porcentaje por defecto
    
    // Determinar si hay obesidad y diabetes mal controlada
    const tieneObesidadSevera = imc >= 35;
    const tieneObesidad = imc >= 30;
    const diabetesMalControlada = hba1c >= 6.9 || glucosa >= 140;
    
    // Ajustar según obesidad + control glucémico (PRIORITARIO)
    if (tieneObesidadSevera && diabetesMalControlada) {
        // Obesidad severa + diabetes mal controlada: CHO 25-30%
        cho = 30;
        pro = 20;
        fat = 50;
        console.log(`🔴 Obesidad severa + diabetes mal controlada: CHO muy restrictivo (30%)`);
    } else if (tieneObesidad && diabetesMalControlada) {
        // Obesidad + diabetes mal controlada: CHO 30-35%
        cho = 35;
        pro = 20;
        fat = 45;
        console.log(`🟠 Obesidad + diabetes mal controlada: CHO restrictivo (35%)`);
    } else if (hba1c > 7.0) {
        // Diabetes mal controlada sin obesidad severa
        cho = 40;
        pro = 22;
        fat = 38;
    } else if (hba1c < 5.5) {
        cho = 55;
        pro = 16;
        fat = 29;
    }
    
    // Ajustar proteínas basado en edad
    if (edad > 65) {
        pro = Math.min(pro + 3, 25);
    } else if (edad < 18) {
        pro = Math.min(pro + 2, 20);
    }
    
    // Ajuste adicional por IMC (solo si no se aplicó ajuste por obesidad + diabetes)
    if (!tieneObesidad && imc > 30) {
        cho = Math.max(cho - 5, 35);
        pro = Math.min(pro + 2, 22);
        fat = Math.min(fat + 3, 40);
    }
    
    console.log(`🍎 Macronutrientes calculados: CHO=${cho}%, PRO=${pro}%, FAT=${fat}%`);
    return { cho, pro, fat };
}

function calcularIGMaximo(hba1c, imc) {
    let igMax = 70; // Valor por defecto
    
    if (hba1c > 8.0) {
        igMax = 50; // Índice glucémico muy bajo para diabetes mal controlada
    } else if (hba1c > 6.5) {
        igMax = 60; // Índice glucémico bajo para diabetes
    } else if (hba1c > 5.7) {
        igMax = 65; // Índice glucémico moderado para prediabetes
    }
    
    // Ajustar basado en IMC
    if (imc > 30) {
        igMax = Math.max(igMax - 10, 40); // Índice glucémico más bajo para obesidad
    }
    
    console.log(`📊 IG máximo calculado: ${igMax}`);
    return igMax;
}

function calcularMaxRepeticiones(edad, actividad) {
    let maxRep = 2; // Valor por defecto
    
    if (edad > 65) {
        maxRep = 3; // Más repeticiones para adultos mayores (menos variedad)
    } else if (edad < 18) {
        maxRep = 1; // Menos repeticiones para adolescentes (más variedad)
    }
    
    if (actividad === 'baja') {
        maxRep = Math.min(maxRep + 1, 4); // Más repeticiones para actividad baja
    } else if (actividad === 'alta') {
        maxRep = Math.max(maxRep - 1, 1); // Menos repeticiones para actividad alta
    }
    
    console.log(`🔄 Máx. repeticiones calculadas: ${maxRep}`);
    return maxRep;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando obtener_plan.js (versión completa con ML)');
    
    // Inicializar las listas de ingredientes
    inicializarListasIngredientes();
    
    // Inicializar fechas
    inicializarFechas();
    
    // Limpiar configuración del plan
    limpiarConfiguracionPlan();
    
    // Auto-cargar paciente si viene en la URL
    const urlParams = new URLSearchParams(window.location.search);
    const pacienteIdInicial = urlParams.get('paciente_id');
    
    if (pacienteIdInicial) {
        console.log('📋 Paciente ID encontrado en URL:', pacienteIdInicial);
        // Esperar un momento para que todo esté inicializado
        setTimeout(async () => {
            try {
                await seleccionarPaciente(pacienteIdInicial);
                console.log('✅ Paciente cargado automáticamente desde URL');
            } catch (error) {
                console.error('❌ Error al cargar paciente desde URL:', error);
            }
        }, 500);
    }
    
    // Configurar event listeners para fechas
    const campoFechaInicio = document.getElementById('fecha_inicio');
    const campoFechaFin = document.getElementById('fecha_fin');
    
    if (campoFechaInicio) {
        campoFechaInicio.addEventListener('change', calcularDiasDelPlan);
    }
    if (campoFechaFin) {
        campoFechaFin.addEventListener('change', calcularDiasDelPlan);
    }
    
    // Configurar event listeners para grupos excluidos
    const checkboxesGrupos = document.querySelectorAll('.grupos-exclusion-grid input[type="checkbox"]');
    checkboxesGrupos.forEach(checkbox => {
        checkbox.addEventListener('change', actualizarGruposExcluidos);
    });
    
    // Configurar event listeners para patrones de comidas
    const checkboxesComidas = document.querySelectorAll('#comida_des, #comida_mm, #comida_alm, #comida_mt, #comida_cena');
    checkboxesComidas.forEach(checkbox => {
        checkbox.addEventListener('change', obtenerPatronComidas);
    });
    
    // Configurar búsqueda de pacientes
    const qPac = document.getElementById('qPac');
    if (qPac) {
        console.log('✅ Campo de búsqueda encontrado');
        let timeoutId;
        qPac.addEventListener('input', function() {
            console.log('⌨️ Input detectado:', this.value);
            clearTimeout(timeoutId);
            timeoutId = setTimeout(async () => {
                const query = this.value.trim();
                console.log('🔍 Query procesado:', query);
                        if (query.length >= 1) {
                    console.log('🚀 Iniciando búsqueda...');
                    const sugerencias = await buscarPacientes(query);
                    mostrarSugerenciasPacientes(sugerencias);
                } else {
                    console.log('📭 Query vacío, limpiando sugerencias');
                    const existente = document.getElementById('sugerenciasPacientes');
                    if (existente) {
                        existente.style.display = 'none';
                        existente.innerHTML = '';
                    }
                    
                    // Limpiar todos los campos cuando el campo de búsqueda esté vacío
                    limpiarTodosLosCampos();
                }
            }, 300);
        });
    } else {
        console.error('❌ No se encontró el campo de búsqueda qPac');
    }
    
    // Configurar búsqueda de ingredientes para incluir
    const qIngredienteIncluir = document.getElementById('qIngredienteIncluir');
    if (qIngredienteIncluir) {
        console.log('✅ Campo de búsqueda de ingredientes para incluir encontrado');
        let timeoutId;
        qIngredienteIncluir.addEventListener('input', function() {
            console.log('⌨️ Input detectado en ingredientes incluir:', this.value);
            clearTimeout(timeoutId);
            timeoutId = setTimeout(async () => {
                const query = this.value.trim();
                console.log('🔍 Query procesado para ingredientes incluir:', query);
                if (query.length >= 1) {
                    console.log('🚀 Iniciando búsqueda de ingredientes para incluir...');
                    const sugerencias = await buscarIngredientes(query);
                    mostrarSugerenciasIngredientes(sugerencias, 'incluir');
                } else {
                    console.log('📭 Query vacío, limpiando sugerencias de ingredientes incluir');
                    limpiarDropdownsIngredientes();
                }
            }, 300);
        });
    } else {
        console.error('❌ No se encontró el campo de búsqueda qIngredienteIncluir');
    }
    
    // Configurar búsqueda de ingredientes para excluir
    const qIngredienteExcluir = document.getElementById('qIngredienteExcluir');
    if (qIngredienteExcluir) {
        console.log('✅ Campo de búsqueda de ingredientes para excluir encontrado');
        let timeoutId;
        qIngredienteExcluir.addEventListener('input', function() {
            console.log('⌨️ Input detectado en ingredientes excluir:', this.value);
            clearTimeout(timeoutId);
            timeoutId = setTimeout(async () => {
                const query = this.value.trim();
                console.log('🔍 Query procesado para ingredientes excluir:', query);
                if (query.length >= 1) {
                    console.log('🚀 Iniciando búsqueda de ingredientes para excluir...');
                    const sugerencias = await buscarIngredientes(query);
                    mostrarSugerenciasIngredientes(sugerencias, 'excluir');
                } else {
                    console.log('📭 Query vacío, limpiando sugerencias de ingredientes excluir');
                    limpiarDropdownsIngredientes();
                }
            }, 300);
        });
    } else {
        console.error('❌ No se encontró el campo de búsqueda qIngredienteExcluir');
    }
    
    // Configurar botones clear de ingredientes
    const btnClearIngredienteIncluir = document.getElementById('btnClearIngredienteIncluir');
    if (btnClearIngredienteIncluir) {
        btnClearIngredienteIncluir.onclick = function() {
            document.getElementById('qIngredienteIncluir').value = '';
            limpiarDropdownsIngredientes();
        };
    }
    
    const btnClearIngredienteExcluir = document.getElementById('btnClearIngredienteExcluir');
    if (btnClearIngredienteExcluir) {
        btnClearIngredienteExcluir.onclick = function() {
            document.getElementById('qIngredienteExcluir').value = '';
            limpiarDropdownsIngredientes();
        };
    }
    
    // Configurar botón generar
    const btnGenerar = document.getElementById('btnGenerar');
    if (btnGenerar) {
        console.log('✅ Botón "Generar Plan Nutricional" encontrado y configurado');
        btnGenerar.onclick = function() {
            console.log('🖱️ Click en botón "Generar Plan Nutricional"');
            generarPlan();
        };
    } else {
        console.error('❌ No se encontró el botón "Generar Plan Nutricional" (id: btnGenerar)');
    }
    
    // Configurar botón limpiar búsqueda
    const btnClearPac = document.getElementById('btnClearPac');
    if (btnClearPac) {
        btnClearPac.onclick = function() {
            document.getElementById('qPac').value = '';
            const container = document.getElementById('sugerenciasPacientes');
            if (container) container.style.display = 'none';
            
            // Limpiar todos los campos cuando se quita el paciente
            limpiarTodosLosCampos();
            
            console.log('🧹 Paciente deseleccionado - todos los campos limpiados');
        };
    }
    
    // Event listener para el botón limpiar
    const btnLimpiar = document.getElementById('btnLimpiar');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function() {
            console.log('🧹 Limpiando formulario...');
            limpiarFormulario();
        });
    } else {
        console.error('❌ No se encontró el botón limpiar');
    }
    
    // Event listener para el botón Motor IA
    const btnMotorRecomendacion = document.getElementById('btnMotorRecomendacion');
    if (btnMotorRecomendacion) {
        btnMotorRecomendacion.addEventListener('click', async function() {
            const pacienteId = document.getElementById('paciente_id').value;
            if (!pacienteId) {
                Toastify({
                    text: "⚠️ Selecciona un paciente primero",
                    duration: 3000,
                    gravity: "top",
                    position: "right",
                    backgroundColor: "#f59e0b"
                }).showToast();
                return;
            }
            
            // Deshabilitar botón mientras se calcula
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculando...';
            
            try {
                console.log('🤖 Obteniendo configuración recomendada con ajuste ML...');
                
                // Llamar al endpoint que calcula la configuración CON ajuste ML
                const response = await fetch(`/api/recomendacion/configuracion/${pacienteId}`, {
                    credentials: 'same-origin'
                });
                
                if (!response.ok) {
                    throw new Error(`Error HTTP: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (!data.ok) {
                    throw new Error(data.error || 'Error al calcular configuración');
                }
                
                // Llenar campos con la configuración FINAL (ya ajustada por ML)
                const config = data.configuracion_final;
                const metas = data.metas_nutricionales;
                
                document.getElementById('kcal_objetivo').value = config.kcal_objetivo || '';
                document.getElementById('cho_pct').value = config.cho_pct || '';
                document.getElementById('pro_pct').value = config.pro_pct || '';
                document.getElementById('fat_pct').value = config.fat_pct || '';
                document.getElementById('ig_max').value = config.ig_max || '';
                document.getElementById('max_repeticiones').value = config.max_repeticiones || '';
                
                // Guardar configuración base (antes del ajuste ML) para referencia
                const formConfig = document.getElementById('formConfiguracionPlan') || document.body;
                formConfig.dataset.configuracionOriginal = JSON.stringify(data.configuracion_base);
                formConfig.dataset.configuracionFinal = JSON.stringify(data.configuracion_final);
                formConfig.dataset.mlInfo = JSON.stringify(data.ml);
                
                console.log('✅ Configuración recomendada cargada:', {
                    base: data.configuracion_base,
                    final: data.configuracion_final,
                    ml: data.ml
                });
                
                // Mostrar mensaje de éxito con información del ML
                const controlMsg = data.ml.control_glucemico === 'MALO' ? '⚠️' : 
                                  data.ml.control_glucemico === 'MODERADO' ? '⚡' : '✅';
                Toastify({
                    text: `🤖 ${controlMsg} Configuración recomendada aplicada (${data.ml.control_glucemico})`,
                    duration: 4000,
                    gravity: "top",
                    position: "right",
                    backgroundColor: data.ml.control_glucemico === 'MALO' ? "#ef4444" : 
                                   data.ml.control_glucemico === 'MODERADO' ? "#f59e0b" : "#10b981"
                }).showToast();
                
            } catch (error) {
                console.error('❌ Error al obtener configuración recomendada:', error);
                Toastify({
                    text: `❌ Error: ${error.message}`,
                    duration: 4000,
                    gravity: "top",
                    position: "right",
                    backgroundColor: "#ef4444"
                }).showToast();
            } finally {
                // Rehabilitar botón
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-robot"></i> Recomendación inteligente';
            }
        });
    } else {
        console.error('❌ No se encontró el botón Generar recomendación');
    }
    
    console.log('✅ obtener_plan.js inicializado correctamente (versión completa con ML)');
});

console.log('🏁 FIN DEL ARCHIVO JS - obtener_plan.js');
