const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('app/static/js/main.js', 'utf8');
const code = source.slice(source.indexOf('function initializeProductForms('), source.indexOf('function getSelectedProductIds('));
function field(value = '') { return {value, checked: false, hidden: false, events: {}, addEventListener(k, fn) {this.events[k] = fn;}}; }
function row(quantity) {
    const fields = {'[data-variant-checkbox]': field(), '[data-variant-quantity-input]': field(quantity),
        '[data-variant-quantity-controls]': field(), '[data-variant-quantity-minus]': field(), '[data-variant-quantity-plus]': field()};
    fields['[data-variant-checkbox]'].checked = quantity > 0;
    return {fields, querySelector(s) {return fields[s];}};
}
const rows = [row(1), row(2)];
const purchase = field('100');
const total = field();
const none = field();
const stock = field('10');
const fields = {'input[name="purchase_price"]': purchase, '[data-purchase-total]': total,
    '[data-variant-none-checkbox]': none, '[name="stock_quantity"]': stock,
    '[data-global-stock-field]': field(), '[data-variant-quantity-total]': field()};
const form = {dataset: {}, events: {}, querySelector(s) {return fields[s] || null;},
    querySelectorAll() {return rows;}, addEventListener(k, fn) {this.events[k] = fn;}};
const root = {querySelectorAll(s) {return s === '[data-bulk-price-preview]' ? [] : [form];}};
const ctx = {parseLocaleNumber: Number, Intl};
vm.createContext(ctx);
vm.runInContext(code, ctx);
ctx.initializeProductForms(root);
assert.match(total.textContent, /3 adet/);
assert.match(total.textContent, /300,00/);
rows[1].fields['[data-variant-quantity-plus]'].events.click();
assert.match(total.textContent, /4 adet/);
assert.match(total.textContent, /400,00/);
none.checked = true;
none.events.change();
assert.match(total.textContent, /10 adet/);
assert.match(total.textContent, /1\.000,00/);
purchase.value = '200';
form.events.input();
assert.match(total.textContent, /2\.000,00/);
console.log('Beden adetleri, + butonu, varyantsız stok ve alış fiyatı değişimi: OK');
