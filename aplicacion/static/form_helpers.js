// Este archivo contiene el código JavaScript para los formularios.

document.addEventListener('DOMContentLoaded', function() {
    // Lógica para el campo de fecha de nacimiento en el registro de lactantes
    const fechaNacimientoInput = document.getElementById('fecha_nacimiento_lactante');
    if (fechaNacimientoInput) {
        fechaNacimientoInput.addEventListener('focus', function() {
            this.type = 'date';
        });
        fechaNacimientoInput.addEventListener('blur', function() {
            if (!this.value) {
                this.type = 'text';
            }
        });
    }

    // Lógica para el campo de hora de llegada en el registro de citas
    const horaLlegadaInput = document.getElementById('hora_llegada');
    if (horaLlegadaInput) {
        horaLlegadaInput.addEventListener('focus', function() { this.type = 'time'; });
        horaLlegadaInput.addEventListener('blur', function() { if (!this.value) { this.type = 'text'; } });
    }

    // Lógica para el selector de tipo de cita (Primera Vez / Subsecuente)
    const btnPrimera = document.getElementById('btn-primera');
    const btnSubsecuente = document.getElementById('btn-subsecuente');
    const subsecuenteCheckbox = document.getElementById('subsecuente_checkbox');

    if (btnPrimera && btnSubsecuente && subsecuenteCheckbox) {
        // Estado inicial (Primera Vez seleccionado por defecto)
        subsecuenteCheckbox.checked = false;

        btnPrimera.addEventListener('click', function() {
            // Actualizar estado del checkbox oculto
            subsecuenteCheckbox.checked = false;
            
            // Actualizar estilos de los botones
            btnPrimera.classList.add('bg-white', 'text-[#6a003f]', 'shadow');
            btnPrimera.classList.remove('text-gray-500');
            btnSubsecuente.classList.remove('bg-white', 'text-[#6a003f]', 'shadow');
            btnSubsecuente.classList.add('text-gray-500');
        });

        btnSubsecuente.addEventListener('click', function() {
            // Actualizar estado del checkbox oculto
            subsecuenteCheckbox.checked = true;

            // Actualizar estilos de los botones
            btnSubsecuente.classList.add('bg-white', 'text-[#6a003f]', 'shadow');
            btnSubsecuente.classList.remove('text-gray-500');
            btnPrimera.classList.remove('bg-white', 'text-[#6a003f]', 'shadow');
            btnPrimera.classList.add('text-gray-500');
        });
    }
});
