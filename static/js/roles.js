// ====== Funciones para roles ======
let ALL_ROLES = [];

// ====== Funciones auxiliares ======
const openModal = sel => document.querySelector(sel).classList.add('open');
const closeModal = sel => document.querySelector(sel).classList.remove('open');

// ====== Función para bindear acciones de la tabla ======
function bindAccionesRoles() {
  // Editar
  document.querySelectorAll('.js-edit').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log('Botón editar clickeado!');
      
      const f = document.getElementById('formRol');
      const modal = document.getElementById('modalRol');
      const id = btn.dataset.id;
      
      if (f && modal) {
        f.action = `/admin/roles/${id}/editar`;

        document.getElementById('rol_titulo').innerText = "Editar rol";
        document.getElementById('r_nombre').value = btn.dataset.nombre || "";
        document.getElementById('r_desc').value = btn.dataset.descripcion || "";

        // Evita renombrar admin/paciente (sólo permite editar descripción)
        const esReservado = ['admin','paciente'].includes((btn.dataset.nombre || '').toLowerCase());
        document.getElementById('r_nombre').readOnly = esReservado;

        console.log('Abriendo modal para editar...');
        modal.classList.add('open');
        console.log('Modal classes:', modal.className);
      } else {
        console.error('No se encontró el formulario o modal para editar');
      }
    });
  });

  // Borrar con confirmación moderna
  document.querySelectorAll('.js-borrar').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      
      const rid = btn.dataset.id;
      const nombre = btn.dataset.nombre;
      const usuarios = parseInt(btn.dataset.usuarios);
      
      let mensaje = `¿Estás seguro de borrar el rol "${nombre}"?`;
      if (usuarios > 0) {
        mensaje += `\n\nEste rol tiene ${usuarios} usuario(s) asignado(s).`;
      }
      
      // Mostrar confirmación con Toastify
      Toastify({
        text: mensaje,
        duration: 0, // Sin duración automática
        gravity: "top",
        position: "center",
        backgroundColor: "#ef4444",
        stopOnFocus: true,
        onClick: async function() {
          // Confirmar borrado
          try {
            const response = await fetch(`/admin/roles/${rid}/borrar`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              }
            });
            
            if (response.ok) {
              Toastify({
                text: "✅ Rol borrado correctamente",
                duration: 3000,
                gravity: "top",
                position: "right",
                backgroundColor: "#10b981",
              }).showToast();
              
              // Recargar la página para actualizar datos
              window.location.reload();
            } else {
              Toastify({
                text: "❌ Error al borrar el rol",
                duration: 3000,
                gravity: "top",
                position: "right",
                backgroundColor: "#ef4444",
              }).showToast();
            }
          } catch (error) {
            Toastify({
              text: "❌ Error de conexión",
              duration: 3000,
              gravity: "top",
              position: "right",
              backgroundColor: "#ef4444",
            }).showToast();
          }
        }
      }).showToast();
    });
  });
}

// ====== Renderizado de tabla ======
function renderTablaRoles(filtro = '') {
  const cont = document.getElementById('tablaRoles');
  
  let rolesFiltrados = ALL_ROLES;
  if (filtro) {
    rolesFiltrados = ALL_ROLES.filter(r => 
      r.nombre.toLowerCase().includes(filtro.toLowerCase())
    );
  }
  
  if (!rolesFiltrados.length) {
    cont.innerHTML = "<p class='empty'>No hay roles que coincidan con la búsqueda.</p>";
    return;
  }

  let html = `
    <table class="tbl">
      <thead>
        <tr>
          <th>ID</th>
          <th>Nombre</th>
          <th>Descripción</th>
          <th>Usuarios</th>
          <th style="width:220px;">Acciones</th>
        </tr>
      </thead>
      <tbody>`;

  rolesFiltrados.forEach(r => {
    const badgeClass = r.esReservado ? 
      (r.nombre === 'admin' ? 'admin' : 'paciente') : 'custom';
    
    html += `
      <tr>
        <td>${r.id}</td>
        <td>
          <span class="rol-badge ${badgeClass}">${r.nombre}</span>
        </td>
        <td>${r.descripcion || ''}</td>
        <td>${r.usuarios}</td>
        <td class="actions">
          <button class="btn btn-sm btn-primary js-edit"
                  data-id="${r.id}"
                  data-nombre="${r.nombre}"
                  data-descripcion="${r.descripcion || ''}">
            <i class="fas fa-edit"></i> Editar
          </button>
          <button class="btn btn-sm btn-danger js-borrar"
                  data-id="${r.id}"
                  data-nombre="${r.nombre}"
                  data-usuarios="${r.usuarios}"
                  data-esreservado="${r.esReservado}"
                  ${r.esReservado || r.usuarios > 0 ? 'disabled' : ''}>
            <i class="fas fa-trash"></i> Borrar
          </button>
        </td>
      </tr>`;
  });

  html += `</tbody></table>`;
  cont.innerHTML = html;

  // Re-bind acciones
  bindAccionesRoles();
}





