// Escáner con la cámara del teléfono o del PC usando la librería html5-qrcode (QR y códigos de barras).
// Uso: EscanerCamara.conectar({ boton, panel, aviso, alLeer: function (codigo) {...}, continuo: true|false })
// La cámara solo funciona con HTTPS o en localhost (requisito del navegador).
window.EscanerCamara = (function () {
  function conectar(op) {
    var panel = op.panel;
    var estado = panel.querySelector('[data-estado]');
    var idLector = panel.querySelector('[data-lector]').id;
    var lector = null, ultimo = '', ultimoEn = 0;

    function avisar(msg) { if (op.aviso) op.aviso.textContent = msg; }

    function cerrar() {
      panel.classList.add('d-none');
      if (lector && lector.isScanning) { lector.stop().catch(function () {}); }
    }

    function leido(texto) {
      var ahora = Date.now();
      if (texto === ultimo && ahora - ultimoEn < 2000) return;  // evita leer el mismo código varias veces seguidas
      ultimo = texto; ultimoEn = ahora;
      if (navigator.vibrate) navigator.vibrate(80);
      estado.textContent = 'Leído: ' + texto;
      if (!op.continuo) cerrar();
      op.alLeer(texto.trim());
    }

    op.boton.addEventListener('click', function () {
      avisar('');
      if (!window.isSecureContext || !navigator.mediaDevices) {
        avisar('La cámara solo funciona con HTTPS o en localhost. Abre la página con https://');
        return;
      }
      if (typeof Html5Qrcode === 'undefined') {
        avisar('No se pudo cargar el lector de la cámara (revisa la conexión a internet).');
        return;
      }
      if (lector && lector.isScanning) return;
      panel.classList.remove('d-none');
      var F = Html5QrcodeSupportedFormats;
      lector = lector || new Html5Qrcode(idLector, {
        verbose: false,
        formatsToSupport: [F.QR_CODE, F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E, F.CODE_128, F.CODE_39],
        experimentalFeatures: { useBarCodeDetectorIfSupported: true },
      });
      estado.textContent = 'Apunta al código de barras o QR.';
      lector.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 260, height: 160 } }, leido, function () {})
        .catch(function (err) {
          panel.classList.add('d-none');
          avisar('No se pudo abrir la cámara: ' + (String(err).indexOf('NotAllowedError') !== -1
            ? 'el permiso fue denegado. Actívalo en los ajustes del navegador.' : err));
        });
    });
    panel.querySelector('[data-cerrar]').addEventListener('click', cerrar);
    return { cerrar: cerrar };
  }

  return { conectar: conectar };
})();
