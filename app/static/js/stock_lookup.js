(() => {
    'use strict';
    const form = document.getElementById('stockLookupForm');
    if (!form) return;
    const input = document.getElementById('lookupBarcode');
    const video = document.getElementById('stockCamera');
    const start = document.getElementById('startStockCamera');
    const stop = document.getElementById('stopStockCamera');
    const status = document.getElementById('stockCameraStatus');
    let stream = null, timer = null, generation = 0;
    function closeCamera() {
        generation += 1;
        clearTimeout(timer);
        if (stream) stream.getTracks().forEach(track => track.stop());
        stream = null;
        video.srcObject = null;
        video.hidden = true;
        stop.hidden = true;
        start.disabled = false;
    }
    start.addEventListener('click', async () => {
        closeCamera();
        const token = generation;
        start.disabled = true;
        stop.hidden = false;
        try {
            if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.BarcodeDetector) {
                throw new Error('Bu tarayıcıda kamera ile barkod okuma desteklenmiyor. Barkodu elle yazabilir veya destekleyen bir tarayıcıda HTTPS adresini açabilirsiniz.');
            }
            const formats = await BarcodeDetector.getSupportedFormats();
            if (!formats.includes('code_128')) throw new Error('Bu tarayıcı etiket biçimini okuyamıyor. Barkodu elle yazın.');
            const detector = new BarcodeDetector({ formats: ['code_128', 'ean_13', 'ean_8'].filter(f => formats.includes(f)) });
            if (token !== generation) return;
            const acquired = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
            if (token !== generation) { acquired.getTracks().forEach(t => t.stop()); return; }
            stream = acquired;
            video.srcObject = stream;
            video.hidden = false;
            await video.play();
            status.textContent = 'Etiketi aydınlık bir yerde kameraya tutun. Barkod bulununca sorgulama açılır.';
            async function scan() {
                if (token !== generation) return;
                try {
                    const codes = await detector.detect(video);
                    if (token !== generation) return;
                    const code = codes.find(item => item.rawValue && item.rawValue.length <= 64);
                    if (code) {
                        input.value = code.rawValue;
                        closeCamera();
                        form.requestSubmit();
                        return;
                    }
                    timer = setTimeout(scan, 250);
                } catch (_) {
                    if (token !== generation) return;
                    closeCamera();
                    status.textContent = 'Görüntü okunamadı. Kamerayı tekrar açın veya barkodu elle yazın.';
                }
            }
            scan();
        } catch (error) {
            if (token !== generation) return;
            closeCamera();
            status.textContent = error.name === 'NotAllowedError' ? 'Kamera izni verilmedi. İzin verebilir veya barkodu elle yazabilirsiniz.' : (error.name === 'NotFoundError' ? 'Kamera bulunamadı. Barkodu elle yazın.' : error.message);
        }
    });
    stop.addEventListener('click', () => { closeCamera(); status.textContent = 'Kamera kapatıldı.'; });
    form.addEventListener('submit', closeCamera);
    window.addEventListener('pagehide', closeCamera);
    document.addEventListener('visibilitychange', () => { if (document.hidden) closeCamera(); });
})();
