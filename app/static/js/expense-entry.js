const shortcuts = document.querySelector("[data-expense-shortcuts]");
shortcuts.addEventListener("click", (event) => {
    const choice = event.target.closest("button[data-expense]");
    if (!choice) return;
    choice.form.elements.description.value = choice.dataset.expense;
    choice.form.elements.total_amount.focus();
});
