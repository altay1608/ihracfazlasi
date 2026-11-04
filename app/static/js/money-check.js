(function () {
  const money = new Intl.NumberFormat('tr-TR', {style: 'currency', currency: 'TRY'});
  document.querySelectorAll('form').forEach(form => {
    const inputs = [...form.querySelectorAll('[data-money-check]')];
    const output = form.querySelector('[data-money-result]');
    if (!inputs.length || !output) return;
    function update() {
      let difference = false;
      const lines = inputs.map(input => {
        if (input.value === '') return 'Gerçek tutarı girin.';
        const value = Number(input.value), expected = Number(input.dataset.expected);
        if (!Number.isFinite(value)) return 'Geçerli bir tutar girin.';
        const diff = Math.round(value * 100) - Math.round(expected * 100);
        difference ||= diff !== 0;
        return `${input.name === 'counted_cash' ? 'Nakit' : input.name === 'counted_card' ? 'Kart' : input.name === 'counted_transfer' ? 'Banka' : 'Banka tutarı'}: ${diff === 0 ? 'Uyumlu' : (diff < 0 ? 'Eksik ' : 'Fazla ') + money.format(Math.abs(diff) / 100)}`;
      });
      output.textContent = lines.join(' · ');
      const note = form.querySelector('[name="note"]');
      if (note) { note.required = difference; note.minLength = difference ? 5 : 0; }
    }
    inputs.forEach(input => input.addEventListener('input', update));
    update();
  });
})();
