const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/js/stock_lookup.js', 'utf8');
function setup(supported) {
    const ids = ['stockLookupForm', 'lookupBarcode', 'stockCamera', 'startStockCamera', 'stopStockCamera', 'stockCameraStatus'];
    const nodes = Object.fromEntries(ids.map(id => [id, { events: {}, addEventListener(k, fn) { this.events[k] = fn; }, play: async () => {}, requestSubmit() { this.submitted = true; } }]));
    let stopped = 0;
    const track = { stop() { stopped++; } };
    const document = { getElementById: id => nodes[id], addEventListener() {} };
    const window = { isSecureContext: true, addEventListener() {} };
    class Detector {
        static async getSupportedFormats() { return ['code_128']; }
        async detect() { return [{ rawValue: '1000001-01' }]; }
    }
    if (supported) window.BarcodeDetector = Detector;
    vm.runInNewContext(source, { window, document, navigator: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [track] }) } }, BarcodeDetector: Detector, setTimeout, clearTimeout });
    return { nodes, stopped: () => stopped };
}
(async () => {
    const unsupported = setup(false);
    await unsupported.nodes.startStockCamera.events.click();
    assert.match(unsupported.nodes.stockCameraStatus.textContent, /desteklenmiyor/);
    assert.equal(unsupported.nodes.startStockCamera.disabled, false);
    const active = setup(true);
    await active.nodes.startStockCamera.events.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(active.nodes.lookupBarcode.value, '1000001-01');
    assert.equal(active.nodes.stockLookupForm.submitted, true);
    assert.equal(active.stopped(), 1);
    assert.equal(active.nodes.stockCamera.srcObject, null);
    console.log('Kamera desteği yok: elle giriş; başarılı okuma: tek sorgu ve kamera kapanışı OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
