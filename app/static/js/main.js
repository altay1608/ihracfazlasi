const toastContainer = document.getElementById("toastContainer");
const busyOverlay = document.getElementById("busyOverlay");
const busyOverlayText = document.getElementById("busyOverlayText");
const globalModal = document.getElementById("globalModal");
const globalModalTitle = document.getElementById("globalModalTitle");
const globalModalBody = document.getElementById("globalModalBody");
const confirmModal = document.getElementById("confirmModal");
const confirmModalTitle = document.getElementById("confirmModalTitle");
const confirmModalMessage = document.getElementById("confirmModalMessage");
const confirmModalDetails = document.getElementById("confirmModalDetails");
const confirmModalSubmit = document.getElementById("confirmModalSubmit");

const TABLE_STATE_PREFIX = "lafemme_table_state:";
const PENDING_TOAST_KEY = "lafemme_pending_toast";
let confirmAction = null;
let busyCounter = 0;

function showToast(message, type = "success") {
    if (!toastContainer || !message) {
        return;
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    window.setTimeout(() => {
        toast.remove();
    }, 3500);
}

function storePendingToast(message, type = "success") {
    if (!message) {
        return;
    }
    sessionStorage.setItem(PENDING_TOAST_KEY, JSON.stringify({ message, type }));
}

function flushPendingToast() {
    try {
        const raw = sessionStorage.getItem(PENDING_TOAST_KEY);
        if (!raw) {
            return;
        }
        sessionStorage.removeItem(PENDING_TOAST_KEY);
        const payload = JSON.parse(raw);
        if (payload?.message) {
            showToast(payload.message, payload.type || "success");
        }
    } catch {
        sessionStorage.removeItem(PENDING_TOAST_KEY);
    }
}

function showBusy(message = "İşlem sürüyor...") {
    if (!busyOverlay) {
        return;
    }
    busyCounter += 1;
    busyOverlay.classList.add("is-visible");
    busyOverlay.setAttribute("aria-hidden", "false");
    if (busyOverlayText) {
        busyOverlayText.textContent = message;
    }
}

function hideBusy() {
    if (!busyOverlay) {
        return;
    }
    busyCounter = Math.max(0, busyCounter - 1);
    if (busyCounter > 0) {
        return;
    }
    busyOverlay.classList.remove("is-visible");
    busyOverlay.setAttribute("aria-hidden", "true");
    if (busyOverlayText) {
        busyOverlayText.textContent = "İşlem sürüyor...";
    }
}

function openModal(title, content) {
    if (!globalModal || !globalModalBody || !globalModalTitle) {
        return;
    }
    globalModalTitle.textContent = title || "Detay";
    globalModalBody.innerHTML = content;
    globalModal.classList.add("is-open");
    globalModal.setAttribute("aria-hidden", "false");
    initializeUi(globalModalBody);
}

function closeModal() {
    if (!globalModal) {
        return;
    }
    globalModal.classList.remove("is-open");
    globalModal.setAttribute("aria-hidden", "true");
    globalModalBody.innerHTML = "";
}

function openConfirmModal(messageOrOptions, onConfirm) {
    const options = typeof messageOrOptions === "object" && messageOrOptions !== null
        ? messageOrOptions
        : { message: messageOrOptions };
    confirmAction = onConfirm;
    if (confirmModalTitle) {
        confirmModalTitle.textContent = options.title || "Kaydı sil";
    }
    confirmModalMessage.textContent = options.message || "Bu kaydı silmek istediğinize emin misiniz?";
    if (confirmModalDetails) {
        if (options.detailsHtml) {
            confirmModalDetails.innerHTML = options.detailsHtml;
            confirmModalDetails.hidden = false;
        } else {
            confirmModalDetails.innerHTML = "";
            confirmModalDetails.hidden = true;
        }
    }
    if (confirmModalSubmit) {
        confirmModalSubmit.textContent = options.submitLabel || "Sil";
        confirmModalSubmit.classList.remove("danger-button");
        if ((options.submitVariant || "danger") === "danger") {
            confirmModalSubmit.classList.add("danger-button");
        }
    }
    confirmModal.classList.add("is-open");
    confirmModal.setAttribute("aria-hidden", "false");
}

function closeConfirmModal() {
    confirmAction = null;
    if (!confirmModal) {
        return;
    }
    confirmModal.classList.remove("is-open");
    confirmModal.setAttribute("aria-hidden", "true");
    if (confirmModalTitle) {
        confirmModalTitle.textContent = "Kaydı sil";
    }
    if (confirmModalMessage) {
        confirmModalMessage.textContent = "Bu kaydı silmek istediğinize emin misiniz?";
    }
    if (confirmModalDetails) {
        confirmModalDetails.innerHTML = "";
        confirmModalDetails.hidden = true;
    }
    if (confirmModalSubmit) {
        confirmModalSubmit.textContent = "Sil";
        confirmModalSubmit.classList.add("danger-button");
    }
}

function handleCloseConfirmClick(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    closeConfirmModal();
    return false;
}

function markRequiredFields(root = document) {
    root.querySelectorAll("input[required], select[required], textarea[required]").forEach((field) => {
        const label = root.querySelector(`label[for="${field.id}"]`) || document.querySelector(`label[for="${field.id}"]`);
        if (label) {
            label.classList.add("required-label");
        }
    });
}

function parseLocaleNumber(value) {
    if (value == null) {
        return 0;
    }
    const rawValue = String(value).trim().replace(/\s+/g, "");
    if (!rawValue) {
        return 0;
    }

    const hasComma = rawValue.includes(",");
    const hasDot = rawValue.includes(".");
    let normalized = rawValue;

    if (hasComma && hasDot) {
        normalized = rawValue.lastIndexOf(",") > rawValue.lastIndexOf(".")
            ? rawValue.replace(/\./g, "").replace(",", ".")
            : rawValue.replace(/,/g, "");
    } else if (hasComma) {
        normalized = rawValue.replace(/\./g, "").replace(",", ".");
    } else {
        normalized = rawValue.replace(/,/g, "");
    }

    return Number(normalized) || 0;
}

function roundAmount(value) {
    return Math.round((Number(value) || 0) * 100) / 100;
}

function roundCustomerPrice(value) {
    const amount = roundAmount(value);
    const wholeLira = Math.floor(amount);
    const cents = roundAmount(amount - wholeLira);
    const lowerTen = Math.floor(wholeLira / 10) * 10;
    const midpoint = lowerTen + 5;

    if (cents === 0 && wholeLira === midpoint) {
        return roundAmount(midpoint);
    }
    if (amount <= midpoint) {
        return roundAmount(lowerTen);
    }
    return roundAmount(lowerTen + 10);
}

function enhanceFilterForms(root = document) {
    root.querySelectorAll('form.filter-bar').forEach((form) => {
        if (form.dataset.enhancedFilter === "1") {
            return;
        }
        form.dataset.enhancedFilter = "1";
        const method = (form.getAttribute("method") || "get").toLowerCase();
        if (method !== "get") {
            return;
        }
        const clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className = "ghost-button";
        clearButton.textContent = "Filtreleri Temizle";
        clearButton.addEventListener("click", () => {
            const action = form.getAttribute("action") || window.location.pathname;
            const url = new URL(action, window.location.origin);
            window.location.href = `${url.pathname}${url.hash}`;
        });
        form.appendChild(clearButton);
    });
}

function sanitizeSheetValue(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function getExportableCells(row) {
    return Array.from(row.cells).filter((cell) => {
        if (cell.classList.contains("is-hidden-column")) {
            return false;
        }
        const key = (cell.dataset.columnKey || "").trim();
        return key !== "selection" && key !== "actions";
    });
}

function getExportHeaderValue(cell) {
    const explicitLabel = (cell.dataset.columnLabel || "").trim();
    if (explicitLabel && explicitLabel !== "Seçim" && explicitLabel !== "İşlemler") {
        return explicitLabel;
    }
    const labelNode = cell.querySelector(".table-header-label");
    if (labelNode) {
        return labelNode.textContent.trim();
    }
    return cell.textContent.trim();
}

function exportTableToExcel(table) {
    const headerRow = getHeaderRow(table);
    const visibleHeaders = getExportableCells(headerRow).map((cell) => sanitizeSheetValue(getExportHeaderValue(cell)));
    const rows = getBodyRows(table)
        .filter((row) => !row.classList.contains("is-filtered-out"))
        .map((row) => getExportableCells(row).map((cell) => sanitizeSheetValue(getCellDisplayValue(cell))));

    const sheetRows = [
        `<tr>${visibleHeaders.map((value) => `<th>${value}</th>`).join("")}</tr>`,
        ...rows.map((cells) => `<tr>${cells.map((value) => `<td>${value}</td>`).join("")}</tr>`)
    ].join("");

    const workbook = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office"
              xmlns:x="urn:schemas-microsoft-com:office:excel"
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta charset="UTF-8">
            <!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>Veriler</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]-->
        </head>
        <body>
            <table>${sheetRows}</table>
        </body>
        </html>
    `;

    const blob = new Blob([workbook], { type: "application/vnd.ms-excel;charset=utf-8;" });
    const tableName = table.dataset.exportName || table.dataset.tableKey || "liste";
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${tableName}.xls`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
}

function ensureTableExportButtons(root = document) {
    root.querySelectorAll("table[data-enhanced-table]").forEach((table) => {
        if (table.dataset.exportReady === "1" || table.closest(".modal-body")) {
            return;
        }
        table.dataset.exportReady = "1";
        if (table.dataset.manualExport === "true") {
            return;
        }

        const sectionHeading = table.closest(".panel")?.querySelector(".section-heading");
        const tableWrap = table.closest(".table-wrap");
        const host = sectionHeading || tableWrap;
        if (!host) {
            return;
        }

        let actions = host.querySelector(".table-export-actions");
        if (!actions) {
            actions = document.createElement("div");
            actions.className = "table-export-actions";
            if (sectionHeading) {
                host.appendChild(actions);
            } else {
                host.parentElement?.insertBefore(actions, tableWrap);
            }
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "ghost-button";
        button.textContent = "Excel'e Aktar";
        button.addEventListener("click", () => exportTableToExcel(table));
        actions.appendChild(button);
    });
}

function initializeReturnForms(root = document) {
    root.querySelectorAll('form[action*="/returns/create"]').forEach((form) => {
        if (form.dataset.returnFormBound === "1") {
            return;
        }
        form.dataset.returnFormBound = "1";

        const typeSelect = form.querySelector('select[name="type"]');
        const exchangeOnlyFields = Array.from(form.querySelectorAll("[data-exchange-only]"));
        if (!typeSelect || !exchangeOnlyFields.length) {
            return;
        }

        const syncExchangeFields = () => {
            const isExchange = typeSelect.value === "degisim";
            exchangeOnlyFields.forEach((field) => {
                field.disabled = !isExchange;
                if (!isExchange) {
                    field.value = "";
                }
                field.classList.toggle("is-disabled-field", !isExchange);
            });
        };

        typeSelect.addEventListener("change", syncExchangeFields);
        syncExchangeFields();

        form.querySelectorAll("[data-return-barcode-scan]").forEach((input) => {
            input.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return;
                }
                event.preventDefault();
                const value = input.value.trim();
                if (!value) {
                    return;
                }
                const match = Array.from(form.querySelectorAll("[data-return-unit-checkbox]")).find(
                    (checkbox) => checkbox.value === value
                );
                if (!match) {
                    showToast("Okutulan birim barkodu bu satışta bulunamadı.", "error");
                    input.select();
                    return;
                }
                if (match.checked) {
                    showToast("Bu birim barkodu işleme daha önce eklendi.", "error");
                    input.select();
                    return;
                }
                match.checked = true;
                input.value = "";
                showToast("Barkod işleme eklendi.", "success");
            });
        });
    });
}

function initializeProductForms(root = document) {
    root.querySelectorAll('form[action*="/products/"]').forEach((form) => {
        if (form.dataset.productFormBound === "1") {
            return;
        }
        form.dataset.productFormBound = "1";

        const purchaseInput = form.querySelector('input[name="purchase_price"]');
        const multiplierSelect = form.querySelector('select[name="retail_multiplier_id"]');
        const salePriceInput = form.querySelector('input[name="sale_price"]');

        if (!purchaseInput || !multiplierSelect || !salePriceInput) {
            return;
        }

        const resolveMultiplier = () => {
            const option = multiplierSelect.options[multiplierSelect.selectedIndex];
            const match = option?.textContent?.match(/([0-9]+(?:[.,][0-9]+)?)x/i);
            if (!match) {
                return 1;
            }
            return parseFloat(match[1].replace(",", ".")) || 1;
        };

        const syncSalePrice = () => {
            const purchase = parseLocaleNumber(purchaseInput.value);
            const multiplier = resolveMultiplier();
            const salePrice = roundCustomerPrice(purchase * 1.10 * multiplier);
            salePriceInput.value = salePrice.toFixed(2);
        };

        purchaseInput.addEventListener("input", syncSalePrice);
        multiplierSelect.addEventListener("change", syncSalePrice);
        syncSalePrice();
    });
}

function getSelectedProductIds(section) {
    if (!section) {
        return [];
    }
    return Array.from(section.querySelectorAll('[data-product-row-select]:checked')).map((input) => input.value);
}

function getSelectedProducts(section) {
    if (!section) {
        return [];
    }
    return Array.from(section.querySelectorAll('[data-product-row-select]:checked')).map((input) => ({
        id: input.value,
        code: (input.dataset.productCode || "").trim(),
        name: (input.dataset.productName || "").trim()
    }));
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function buildConfirmRecordsHtml(records = []) {
    if (!records.length) {
        return "";
    }
    const listClass = records.length > 5 ? "confirm-record-list is-compact" : "confirm-record-list";
    const items = records.map((record) => `
        <div class="confirm-record-item">
            <strong class="confirm-record-code">${escapeHtml(record.code || "-")}</strong>
            <span class="confirm-record-name">${escapeHtml(record.name || "Kayıt adı bulunamadı.")}</span>
        </div>
    `).join("");
    return `<div class="${listClass}">${items}</div>`;
}

function syncProductSelectionState(section) {
    const rowCheckboxes = Array.from(section.querySelectorAll('[data-product-row-select]'));
    const visibleCheckboxes = rowCheckboxes.filter((input) => {
        const row = input.closest("tr");
        return row && !row.classList.contains("is-filtered-out") && !row.classList.contains("is-paged-out");
    });
    const selectAll = section.querySelector("[data-select-all-products]");
    const checked = visibleCheckboxes.filter((input) => input.checked);

    if (selectAll) {
        selectAll.checked = visibleCheckboxes.length > 0 && checked.length === visibleCheckboxes.length;
        selectAll.indeterminate = checked.length > 0 && checked.length < visibleCheckboxes.length;
    }
}

function initializeBulkProductActions(root = document) {
    root.querySelectorAll("#products-table-section").forEach((section) => {
        if (section.dataset.bulkReady === "1") {
            syncProductSelectionState(section);
            return;
        }
        section.dataset.bulkReady = "1";

        const selectAll = section.querySelector("[data-select-all-products]");
        const rowCheckboxes = Array.from(section.querySelectorAll('[data-product-row-select]'));

        selectAll?.addEventListener("change", () => {
            if (selectAll.checked) {
                rowCheckboxes
                    .filter((input) => !input.closest("tr")?.classList.contains("is-filtered-out") && !input.closest("tr")?.classList.contains("is-paged-out"))
                    .forEach((input) => {
                        input.checked = true;
                    });
            } else {
                rowCheckboxes.forEach((input) => {
                    input.checked = false;
                });
            }
            syncProductSelectionState(section);
        });

        rowCheckboxes.forEach((input) => {
            input.addEventListener("change", () => syncProductSelectionState(section));
        });

        syncProductSelectionState(section);
    });
}

async function executeBulkProductAction(trigger, forcedAction = "") {
    const section = trigger.closest("#products-table-section");
    const selectedIds = getSelectedProductIds(section);
    const selectedProducts = getSelectedProducts(section);
    if (!selectedIds.length) {
        showToast("Önce en az bir ürün seçin.", "error");
        return;
    }

    const action = forcedAction || trigger.dataset.bulkAction || "";
    if (!action) {
        showToast("Önce uygulanacak işlemi seçin.", "error");
        return;
    }

    if (action === "labels") {
        const url = new URL(section?.dataset.bulkLabelsUrl || trigger.dataset.bulkLabelsUrl || trigger.dataset.bulkUrl, window.location.origin);
        selectedIds.forEach((id) => url.searchParams.append("product_ids", id));
        window.open(url.toString(), "_blank", "noopener");
        return;
    }

    if (action === "multiplier") {
        const url = new URL(section?.dataset.bulkMultiplierUrl || trigger.dataset.bulkMultiplierUrl || trigger.dataset.bulkUrl, window.location.origin);
        selectedIds.forEach((id) => url.searchParams.append("product_ids", id));
        await loadModalContent(url.toString(), trigger.dataset.modalTitle || "Çarpan Güncelle");
        return;
    }

    if (action === "delete") {
        openConfirmModal(
            {
                title: "Seçili ürünleri sil",
                message: `${selectedIds.length} ürünü silmek üzeresiniz. Bu işlem geri alınamaz.`,
                detailsHtml: buildConfirmRecordsHtml(selectedProducts)
            },
            async () => {
            showBusy("Seçili ürünler siliniyor...");
            try {
                const formData = new FormData();
                selectedIds.forEach((id) => formData.append("product_ids", id));
                const response = await fetch(section?.dataset.bulkDeleteUrl || trigger.dataset.bulkDeleteUrl || trigger.dataset.bulkUrl, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: formData
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.message || "Toplu silme işlemi başarısız.");
                }
                closeConfirmModal();
                showToast(data.message || "Seçili ürünler silindi.", "success");
                await window.refreshTarget(data.refresh_target || "#products-table-section", data.refresh_url || null);
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                hideBusy();
            }
        });
    }
}

function getTableStateKey(table) {
    return `${TABLE_STATE_PREFIX}${table.dataset.tableKey}`;
}

function getTableState(table) {
    try {
        return sanitizeTableState(table, JSON.parse(sessionStorage.getItem(getTableStateKey(table)) || "{}"));
    } catch {
        return {};
    }
}

function setTableState(table, nextState) {
    sessionStorage.setItem(getTableStateKey(table), JSON.stringify(nextState));
}

function getHeaderRow(table) {
    return table.tHead?.rows?.[0] || null;
}

function getHeaderCells(table) {
    return Array.from(getHeaderRow(table)?.cells || []);
}

function getColumnKeys(table) {
    return getHeaderCells(table).map((cell) => cell.dataset.columnKey);
}

function sanitizeTableState(table, state) {
    if (!state || typeof state !== "object") {
        return {};
    }

    const columnKeys = new Set(getHeaderCells(table).map((cell) => cell.dataset.columnKey).filter(Boolean));
    const nextState = { ...state };

    if (nextState.filters && typeof nextState.filters === "object") {
        nextState.filters = Object.fromEntries(
            Object.entries(nextState.filters).filter(([key]) => columnKeys.has(key))
        );
    }

    if (Array.isArray(nextState.hidden)) {
        nextState.hidden = nextState.hidden.filter((key) => columnKeys.has(key));
    }

    if (Array.isArray(nextState.order)) {
        const filteredOrder = nextState.order.filter((key) => columnKeys.has(key));
        const missingKeys = Array.from(columnKeys).filter((key) => !filteredOrder.includes(key));
        nextState.order = [...filteredOrder, ...missingKeys];
    }

    if (nextState.sort?.key && !columnKeys.has(nextState.sort.key)) {
        delete nextState.sort;
    }

    if (nextState.groupBy && !columnKeys.has(nextState.groupBy)) {
        delete nextState.groupBy;
    }

    if (nextState.widths && typeof nextState.widths === "object") {
        nextState.widths = Object.fromEntries(
            Object.entries(nextState.widths).filter(([key, width]) => {
                const normalizedWidth = Number(width);
                return columnKeys.has(key) && Number.isFinite(normalizedWidth) && normalizedWidth >= 40;
            }).map(([key, width]) => [key, Number(width)])
        );
    }

    return nextState;
}

function getBodyRows(table) {
    const headerRow = getHeaderRow(table);
    return Array.from(table.tBodies[0]?.rows || []).filter((row) => row.cells.length === headerRow.cells.length);
}

function getCellDisplayValue(cell) {
    if (!cell) {
        return "";
    }
    const input = cell.querySelector("input, select, textarea");
    if (input) {
        return String(input.value || "").trim();
    }
    return cell.textContent.replace(/\s+/g, " ").trim();
}

function setupColumnMetadata(table) {
    const headerCells = getHeaderCells(table);
    headerCells.forEach((cell, index) => {
        if (!cell.dataset.columnKey) {
            cell.dataset.columnKey = `col-${index}`;
        }
        if (!cell.dataset.columnLabel) {
            cell.dataset.columnLabel = cell.textContent.trim() || `Kolon ${index + 1}`;
        }
        if (!cell.querySelector(".table-header-label") && !cell.querySelector(".table-checkbox-label")) {
            const shell = document.createElement("span");
            shell.className = "table-header-shell";
            const label = document.createElement("span");
            label.className = "table-header-label";
            label.textContent = cell.dataset.columnLabel;
            cell.textContent = "";
            shell.appendChild(label);
            cell.appendChild(shell);
        }
        if (!cell.hasAttribute("data-no-sort")) {
            cell.classList.add("sortable-column");
        }
        cell.draggable = true;
    });

    getBodyRows(table).forEach((row) => {
        Array.from(row.cells).forEach((cell, index) => {
            cell.dataset.columnKey = headerCells[index].dataset.columnKey;
        });
    });
}

function ensureFilterRow(table) {
    if (table.tHead.rows.length > 1 && table.tHead.rows[1].dataset.filterRow === "1") {
        return table.tHead.rows[1];
    }

    const filterRow = document.createElement("tr");
    filterRow.dataset.filterRow = "1";
    filterRow.className = "table-filter-row";

    getHeaderCells(table).forEach((headerCell) => {
        const filterCell = document.createElement("th");
        filterCell.dataset.columnKey = headerCell.dataset.columnKey;
        if (headerCell.hasAttribute("data-no-filter")) {
            filterCell.className = "table-filter-cell table-filter-disabled";
            filterRow.appendChild(filterCell);
            return;
        }

        const select = document.createElement("select");
        select.className = "table-filter-select";
        select.dataset.filterKey = headerCell.dataset.columnKey;
        filterCell.className = "table-filter-cell";
        filterCell.appendChild(select);
        filterRow.appendChild(filterCell);
    });

    table.tHead.appendChild(filterRow);
    return filterRow;
}

function rowMatchesFilterMap(row, filterMap, excludeColumnKey = null) {
    return Object.entries(filterMap).every(([columnKey, filterSetting]) => {
        const normalizedFilter = normalizeColumnFilter(filterSetting);
        if (columnKey === excludeColumnKey || !hasActiveColumnFilter(normalizedFilter)) {
            return true;
        }
        const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
        const cellValue = getCellDisplayValue(cell);
        const matchesValues = !normalizedFilter.values.length || normalizedFilter.values.includes(cellValue);
        const matchesText = matchesTextFilter(cellValue, normalizedFilter);
        return matchesValues && matchesText;
    });
}

function collectColumnValues(table, columnKey, options = {}) {
    const {
        scopedFilterMap = getResolvedFilterMap(table),
        preserveValues = []
    } = options;
    const values = new Set();
    getBodyRows(table).forEach((row) => {
        if (!rowMatchesFilterMap(row, scopedFilterMap, columnKey)) {
            return;
        }
        const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
        const value = getCellDisplayValue(cell);
        if (value) {
            values.add(value);
        }
    });
    normalizeColumnFilter(preserveValues).values.forEach((value) => values.add(value));
    return Array.from(values).sort((a, b) => a.localeCompare(b, "tr", { numeric: true, sensitivity: "base" }));
}

function renderColumnFilters(table) {
    const state = getTableState(table);
    const filterRow = ensureFilterRow(table);

    Array.from(filterRow.cells).forEach((filterCell) => {
        const select = filterCell.querySelector("select");
        const columnKey = filterCell.dataset.columnKey;
        if (!select) {
            return;
        }

        const values = collectColumnValues(table, columnKey);
        const currentValue = state.filters?.[columnKey] || "";
        select.innerHTML = "";

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Tümü";
        select.appendChild(defaultOption);

        values.forEach((value) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            option.selected = value === currentValue;
            select.appendChild(option);
        });

        if (select.dataset.bound === "1") {
            return;
        }
        select.dataset.bound = "1";
        select.addEventListener("change", () => {
            const nextState = getTableState(table);
            nextState.filters = nextState.filters || {};
            if (select.value) {
                nextState.filters[columnKey] = select.value;
            } else {
                delete nextState.filters[columnKey];
            }
            setTableState(table, nextState);
            applyTableFilters(table);
        });
    });
}

function applyColumnOrder(table, orderKeys) {
    if (!orderKeys || !orderKeys.length) {
        return;
    }

    const headRows = Array.from(table.tHead.rows);
    const bodyRows = getBodyRows(table);
    const allRows = [...headRows, ...bodyRows];

    allRows.forEach((row) => {
        const cellMap = {};
        Array.from(row.cells).forEach((cell) => {
            cellMap[cell.dataset.columnKey] = cell;
        });
        orderKeys.forEach((key) => {
            if (cellMap[key]) {
                row.appendChild(cellMap[key]);
            }
        });
    });
}

function applyHiddenColumns(table, hiddenKeys) {
    const hidden = new Set(hiddenKeys || []);
    table.querySelectorAll("th, td").forEach((cell) => {
        const shouldHide = hidden.has(cell.dataset.columnKey);
        cell.classList.toggle("is-hidden-column", shouldHide);
    });
}

function applyColumnWidth(table, columnKey, width) {
    if (!columnKey || !Number.isFinite(Number(width))) {
        return;
    }
    const nextWidth = `${Math.max(60, Number(width))}px`;
    table.querySelectorAll(`[data-column-key="${columnKey}"]`).forEach((cell) => {
        cell.style.width = nextWidth;
        cell.style.minWidth = nextWidth;
    });
}

function applyColumnWidths(table, widths = {}) {
    getHeaderCells(table).forEach((headerCell) => {
        const key = headerCell.dataset.columnKey;
        if (!key) {
            return;
        }
        if (widths[key]) {
            applyColumnWidth(table, key, widths[key]);
            return;
        }
        table.querySelectorAll(`[data-column-key="${key}"]`).forEach((cell) => {
            cell.style.width = "";
            cell.style.minWidth = "";
        });
    });
}

function applyTableFilters(table) {
    const state = getTableState(table);
    const filters = state.filters || {};
    getBodyRows(table).forEach((row) => {
        const visible = Object.entries(filters).every(([columnKey, filterValue]) => {
            if (!filterValue) {
                return true;
            }
            const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
            return getCellDisplayValue(cell) === filterValue;
        });
        row.classList.toggle("is-filtered-out", !visible);
    });
    applyTableGrouping(table);
    paginateTable(table);
}

function normalizeFilterValues(value) {
    if (Array.isArray(value)) {
        return [...new Set(value.map((item) => String(item || "").trim()).filter(Boolean))];
    }
    if (value == null) {
        return [];
    }
    const normalized = String(value).trim();
    return normalized ? [normalized] : [];
}

function normalizeColumnFilter(value) {
    if (Array.isArray(value) || value == null || typeof value !== "object") {
        return {
            values: normalizeFilterValues(value),
            text: "",
            mode: "contains"
        };
    }

    const mode = String(value.mode || "contains").trim() || "contains";
    const text = String(value.text || "").trim();
    return {
        values: normalizeFilterValues(value.values || []),
        text,
        mode
    };
}

function hasActiveColumnFilter(filterSetting) {
    const normalized = normalizeColumnFilter(filterSetting);
    return normalized.values.length > 0 || Boolean(normalized.text);
}

function getFilterModeLabel(mode) {
    const labels = {
        equals: "Eşit",
        not_equals: "Eşit değil",
        starts_with: "İle başlar",
        ends_with: "Şununla biter",
        contains: "İçeren",
        not_contains: "İçermiyor",
        custom: "Özel Filtre"
    };
    return labels[mode] || "İçeren";
}

function normalizeFilterComparable(value) {
    return String(value || "").trim().toLocaleLowerCase("tr");
}

function splitTextFilterTerms(value) {
    return String(value || "")
        .split(";")
        .map((term) => normalizeFilterComparable(term))
        .filter(Boolean);
}

function matchesTextFilter(cellValue, filterSetting) {
    const normalized = normalizeColumnFilter(filterSetting);
    if (!normalized.text) {
        return true;
    }

    const haystack = normalizeFilterComparable(cellValue);
    const terms = splitTextFilterTerms(normalized.text);
    if (!terms.length) {
        return true;
    }

    switch (normalized.mode) {
        case "equals":
            return terms.some((term) => haystack === term);
        case "not_equals":
            return terms.every((term) => haystack !== term);
        case "starts_with":
            return terms.some((term) => haystack.startsWith(term));
        case "ends_with":
            return terms.some((term) => haystack.endsWith(term));
        case "not_contains":
            return terms.every((term) => !haystack.includes(term));
        case "custom":
        case "contains":
        default:
            return terms.some((term) => haystack.includes(term));
    }
}

function getResolvedFilterMap(table, state = getTableState(table)) {
    const filters = state.filters || {};
    const headerCells = getHeaderCells(table);
    const keyByIndex = headerCells.reduce((acc, cell, index) => {
        acc[String(index)] = cell.dataset.columnKey;
        return acc;
    }, {});

    return Object.entries(filters).reduce((acc, [rawKey, rawValue]) => {
        const columnKey = keyByIndex[rawKey] || rawKey;
        if (!columnKey) {
            return acc;
        }
        const filterSetting = normalizeColumnFilter(rawValue);
        if (hasActiveColumnFilter(filterSetting)) {
            acc[columnKey] = filterSetting;
        }
        return acc;
    }, {});
}

function closeAllTableFilterMenus(exceptMenu = null) {
    document.querySelectorAll(".table-column-filter-menu.is-open").forEach((menu) => {
        if (exceptMenu && menu === exceptMenu) {
            return;
        }
        menu.classList.remove("is-open");
        menu.setAttribute("aria-hidden", "true");
        menu.querySelector(".table-column-filter-mode-menu")?.classList.remove("is-open");
        menu.closest(".table-column-filter")?.querySelector(".table-column-filter-trigger")?.setAttribute("aria-expanded", "false");
    });
}

function updateHeaderFilterTriggerState(headerCell, selectedValues) {
    const trigger = headerCell.querySelector(".table-column-filter-trigger");
    const normalizedFilter = normalizeColumnFilter(selectedValues);
    if (!trigger) {
        return;
    }

    trigger.classList.toggle("is-active", hasActiveColumnFilter(normalizedFilter));
    trigger.setAttribute(
        "aria-label",
        hasActiveColumnFilter(normalizedFilter)
            ? `${headerCell.dataset.columnLabel || "Kolon"} filtresi aktif`
            : `${headerCell.dataset.columnLabel || "Kolon"} filtresi`
    );
}

function positionFilterMenu(menu, trigger) {
    if (!menu || !trigger) {
        return;
    }
    const headerCell = trigger.closest("th");
    const filterWrap = trigger.closest(".table-column-filter");
    if (!headerCell || !filterWrap) {
        menu.style.left = "";
        menu.style.top = "";
        return;
    }

    const headerRect = headerCell.getBoundingClientRect();
    const wrapRect = filterWrap.getBoundingClientRect();
    const criteriaInput = menu.querySelector(".table-column-filter-criteria");
    const criteriaValue = String(criteriaInput?.value || "").trim();
    const baseWidth = Math.max(280, Math.min(420, Math.round(headerRect.width + 36)));
    const canvasContext = document.createElement("canvas").getContext("2d");
    let contentWidth = 0;

    if (canvasContext && criteriaInput) {
        const inputStyle = window.getComputedStyle(criteriaInput);
        canvasContext.font = `${inputStyle.fontWeight} ${inputStyle.fontSize} ${inputStyle.fontFamily}`;
        contentWidth = Math.ceil(canvasContext.measureText(criteriaValue).width + 72);

        menu.querySelectorAll(".table-column-filter-option-text").forEach((optionText) => {
            const optionWidth = Math.ceil(canvasContext.measureText(optionText.textContent || "").width + 76);
            contentWidth = Math.max(contentWidth, optionWidth);
        });
    }

    const viewportMargin = 12;
    const viewportWidth = Math.max(260, window.innerWidth - (viewportMargin * 2));
    const desiredWidth = Math.min(Math.max(baseWidth, contentWidth), Math.min(680, viewportWidth));
    let viewportLeft = headerRect.left;
    if (viewportLeft + desiredWidth > window.innerWidth - viewportMargin) {
        viewportLeft = Math.max(viewportMargin, window.innerWidth - viewportMargin - desiredWidth);
    }

    menu.style.left = `${Math.round(viewportLeft - wrapRect.left)}px`;
    menu.style.right = "auto";
    menu.style.top = "calc(100% + 10px)";
    menu.style.width = `${desiredWidth}px`;
    menu.style.maxWidth = `${viewportWidth}px`;
}

function createFilterOptionItem(value, selectedValues) {
    const item = document.createElement("label");
    item.className = "table-column-filter-option";
    item.title = value;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = value;
    checkbox.checked = selectedValues.includes(value);

    const text = document.createElement("span");
    text.className = "table-column-filter-option-text";
    text.textContent = value;

    item.appendChild(checkbox);
    item.appendChild(text);
    return item;
}

function syncFilterMenuOptions(headerCell, values, selectedValues) {
    const menu = headerCell.querySelector(".table-column-filter-menu");
    const optionsHost = menu?.querySelector(".table-column-filter-options");
    const emptyState = menu?.querySelector(".table-column-filter-empty");
    const status = menu?.querySelector(".table-column-filter-status");
    if (!menu || !optionsHost || !emptyState || !status) {
        return;
    }

    const query = (menu.querySelector(".table-column-filter-search")?.value || "").trim().toLocaleLowerCase("tr");
    const filteredValues = values.filter((value) => value.toLocaleLowerCase("tr").includes(query));
    optionsHost.innerHTML = "";
    filteredValues.forEach((value) => {
        optionsHost.appendChild(createFilterOptionItem(value, selectedValues));
    });

    emptyState.hidden = filteredValues.length > 0;
    status.textContent = selectedValues.length
        ? `${selectedValues.length} seçim aktif`
        : "Filtre uygulanmıyor";
}

function ensureHeaderFilterControl(table, headerCell) {
    if (headerCell.hasAttribute("data-no-filter")) {
        headerCell.querySelector(".table-column-filter")?.remove();
        return null;
    }

    let wrap = headerCell.querySelector(".table-column-filter");
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "table-column-filter";
        wrap.innerHTML = `
            <button type="button" class="table-column-filter-trigger" aria-haspopup="dialog" aria-expanded="false">
                <span class="table-column-filter-icon" aria-hidden="true">
                    <svg viewBox="0 0 16 16" focusable="false" aria-hidden="true">
                        <path d="M2.25 3.25h11.5L9.5 8.34v3.54l-3 1.62V8.34L2.25 3.25Z" />
                    </svg>
                </span>
            </button>
            <div class="table-column-filter-menu" aria-hidden="true">
                <div class="table-column-filter-menu-head">
                    <strong class="table-column-filter-menu-title"></strong>
                    <button type="button" class="table-column-filter-clear">Temizle</button>
                </div>
                <label class="table-column-filter-search-wrap">
                    <input type="search" class="table-column-filter-search" placeholder="Ara">
                </label>
                <div class="table-column-filter-actions">
                    <button type="button" class="table-column-filter-select-all">Hepsini seç</button>
                    <button type="button" class="table-column-filter-deselect-all">Seçimi kaldır</button>
                </div>
                <div class="table-column-filter-options"></div>
                <div class="table-column-filter-empty" hidden>Sonuç bulunamadı.</div>
                <div class="table-column-filter-status">Filtre uygulanmıyor</div>
            </div>
        `;
        headerCell.appendChild(wrap);
    }

    const trigger = wrap.querySelector(".table-column-filter-trigger");
    const menu = wrap.querySelector(".table-column-filter-menu");
    const title = wrap.querySelector(".table-column-filter-menu-title");
    const search = wrap.querySelector(".table-column-filter-search");
    const clearButton = wrap.querySelector(".table-column-filter-clear");
    const selectAllButton = wrap.querySelector(".table-column-filter-select-all");
    const deselectAllButton = wrap.querySelector(".table-column-filter-deselect-all");
    const columnKey = headerCell.dataset.columnKey;

    title.textContent = headerCell.dataset.columnLabel || "Filtre";

    if (wrap.dataset.bound !== "1") {
        wrap.dataset.bound = "1";

        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

        trigger.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const willOpen = !menu.classList.contains("is-open");
            closeAllTableFilterMenus(willOpen ? menu : null);
            menu.classList.toggle("is-open", willOpen);
            menu.setAttribute("aria-hidden", willOpen ? "false" : "true");
            trigger.setAttribute("aria-expanded", willOpen ? "true" : "false");
            if (willOpen) {
                search.focus();
            }
        });

        search.addEventListener("input", () => {
            const state = getTableState(table);
            const selectedValues = getResolvedFilterMap(table, state)[columnKey] || [];
            syncFilterMenuOptions(
                headerCell,
                collectColumnValues(table, columnKey, { preserveValues: selectedValues }),
                selectedValues
            );
        });

        clearButton.addEventListener("click", () => {
            const state = getTableState(table);
            const nextFilters = getResolvedFilterMap(table, state);
            delete nextFilters[columnKey];
            state.filters = nextFilters;
            setTableState(table, state);
            updateHeaderFilterTriggerState(headerCell, []);
            search.value = "";
            syncFilterMenuOptions(headerCell, collectColumnValues(table, columnKey), []);
            applyTableFilters(table);
        });

        selectAllButton.addEventListener("click", () => {
            const state = getTableState(table);
            const nextFilters = getResolvedFilterMap(table, state);
            const values = collectColumnValues(table, columnKey, {
                scopedFilterMap: nextFilters
            });
            nextFilters[columnKey] = values;
            state.filters = nextFilters;
            setTableState(table, state);
            updateHeaderFilterTriggerState(headerCell, values);
            syncFilterMenuOptions(headerCell, values, values);
            applyTableFilters(table);
        });

        deselectAllButton.addEventListener("click", () => {
            const state = getTableState(table);
            const nextFilters = getResolvedFilterMap(table, state);
            delete nextFilters[columnKey];
            state.filters = nextFilters;
            setTableState(table, state);
            updateHeaderFilterTriggerState(headerCell, []);
            syncFilterMenuOptions(headerCell, collectColumnValues(table, columnKey), []);
            applyTableFilters(table);
        });

        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

        menu.addEventListener("change", (event) => {
            const checkbox = event.target.closest('input[type="checkbox"]');
            if (!checkbox) {
                return;
            }

            const state = getTableState(table);
            const nextFilters = getResolvedFilterMap(table, state);
            const nextSelectedValues = Array.from(menu.querySelectorAll('.table-column-filter-options input[type="checkbox"]:checked'))
                .map((input) => input.value);
            if (nextSelectedValues.length) {
                nextFilters[columnKey] = nextSelectedValues;
            } else {
                delete nextFilters[columnKey];
            }
            state.filters = nextFilters;
            setTableState(table, state);
            updateHeaderFilterTriggerState(headerCell, nextSelectedValues);
            syncFilterMenuOptions(
                headerCell,
                collectColumnValues(table, columnKey, { preserveValues: nextSelectedValues }),
                nextSelectedValues
            );
            applyTableFilters(table);
        });
    }

    return wrap;
}

function renderColumnFilters(table) {
    const state = getTableState(table);
    table.tHead.querySelector('[data-filter-row="1"]')?.remove();
    getHeaderCells(table).forEach((headerCell) => {
        const columnKey = headerCell.dataset.columnKey;
        const filterControl = ensureHeaderFilterControl(table, headerCell);
        if (!filterControl) {
            return;
        }

        const currentValues = getResolvedFilterMap(table, state)[columnKey] || [];
        const values = collectColumnValues(table, columnKey, { preserveValues: currentValues });
        updateHeaderFilterTriggerState(headerCell, currentValues);
        syncFilterMenuOptions(headerCell, values, currentValues);
    });
}

function closeAllTableFilterMenus(exceptMenu = null) {
    document.querySelectorAll(".table-column-filter-menu.is-open").forEach((menu) => {
        if (exceptMenu && menu === exceptMenu) {
            return;
        }
        menu.classList.remove("is-open");
        menu.setAttribute("aria-hidden", "true");
        menu.querySelector(".table-column-filter-mode-menu")?.classList.remove("is-open");
        menu.closest(".table-column-filter")?.querySelector(".table-column-filter-trigger")?.setAttribute("aria-expanded", "false");
    });
}

function updateHeaderFilterTriggerState(headerCell, filterSetting) {
    const trigger = headerCell.querySelector(".table-column-filter-trigger");
    const normalizedFilter = normalizeColumnFilter(filterSetting);
    if (!trigger) {
        return;
    }

    trigger.classList.toggle("is-active", hasActiveColumnFilter(normalizedFilter));
    trigger.setAttribute(
        "aria-label",
        hasActiveColumnFilter(normalizedFilter)
            ? `${headerCell.dataset.columnLabel || "Kolon"} filtresi aktif`
            : `${headerCell.dataset.columnLabel || "Kolon"} filtresi`
    );
}

function updateFilterMenuStatus(menu, filterSetting) {
    const status = menu?.querySelector(".table-column-filter-status");
    if (!status) {
        return;
    }
    const normalizedFilter = normalizeColumnFilter(filterSetting);
    const parts = [];
    if (normalizedFilter.values.length) {
        parts.push(`${normalizedFilter.values.length} seçim hazır`);
    }
    if (normalizedFilter.text) {
        const criteriaCount = splitTextFilterTerms(normalizedFilter.text).length || 1;
        const criteriaLabel = criteriaCount === 1 ? "metin kriteri" : "kriter";
        parts.push(`${getFilterModeLabel(normalizedFilter.mode)}: ${criteriaCount} ${criteriaLabel}`);
    }
    status.textContent = parts.length ? parts.join(" | ") : "Filtre uygulanmıyor";
}

function rowMatchesFilterMap(row, filterMap, excludeColumnKey = null) {
    return Object.entries(filterMap).every(([columnKey, filterSetting]) => {
        const normalizedFilter = normalizeColumnFilter(filterSetting);
        if (columnKey === excludeColumnKey || !hasActiveColumnFilter(normalizedFilter)) {
            return true;
        }
        const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
        const cellValue = getCellDisplayValue(cell);
        const matchesValues = !normalizedFilter.values.length || normalizedFilter.values.includes(cellValue);
        const matchesText = matchesTextFilter(cellValue, normalizedFilter);
        return matchesValues && matchesText;
    });
}

function collectColumnValues(table, columnKey, options = {}) {
    const {
        scopedFilterMap = getResolvedFilterMap(table),
        preserveValues = []
    } = options;
    const values = new Set();
    getBodyRows(table).forEach((row) => {
        if (!rowMatchesFilterMap(row, scopedFilterMap, columnKey)) {
            return;
        }
        const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
        const value = getCellDisplayValue(cell);
        if (value) {
            values.add(value);
        }
    });
    normalizeColumnFilter(preserveValues).values.forEach((value) => values.add(value));
    return Array.from(values).sort((a, b) => a.localeCompare(b, "tr", { numeric: true, sensitivity: "base" }));
}

function getMenuSelectedValues(menu) {
    if (!menu) {
        return [];
    }
    return Array.from(menu.querySelectorAll('.table-column-filter-options input[type="checkbox"]:checked'))
        .map((input) => input.value);
}

function getMenuFilterSetting(menu) {
    return {
        values: getMenuSelectedValues(menu),
        text: String(menu?.querySelector(".table-column-filter-criteria")?.value || "").trim(),
        mode: menu?.dataset.filterMode || "contains"
    };
}

function syncFilterMenuOptions(headerCell, values, filterSetting) {
    const menu = headerCell.querySelector(".table-column-filter-menu");
    const optionsHost = menu?.querySelector(".table-column-filter-options");
    const emptyState = menu?.querySelector(".table-column-filter-empty");
    if (!menu || !optionsHost || !emptyState) {
        return;
    }

    const normalizedFilter = normalizeColumnFilter(filterSetting);
    const criteriaInput = menu.querySelector(".table-column-filter-criteria");
    const modeLabel = menu.querySelector(".table-column-filter-mode-current");
    const modeButtons = menu.querySelectorAll(".table-column-filter-mode-option");
    const query = (menu.querySelector(".table-column-filter-search")?.value || "").trim().toLocaleLowerCase("tr");
    const filteredValues = values.filter((value) => value.toLocaleLowerCase("tr").includes(query));

    optionsHost.innerHTML = "";
    filteredValues.forEach((value) => {
        optionsHost.appendChild(createFilterOptionItem(value, normalizedFilter.values));
    });

    if (criteriaInput && criteriaInput !== document.activeElement) {
        criteriaInput.value = normalizedFilter.text;
    }
    menu.dataset.filterMode = normalizedFilter.mode;
    if (modeLabel) {
        modeLabel.textContent = getFilterModeLabel(normalizedFilter.mode);
    }
    modeButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.filterMode === normalizedFilter.mode);
    });

    emptyState.hidden = filteredValues.length > 0;
    updateFilterMenuStatus(menu, normalizedFilter);
    positionFilterMenu(menu, headerCell.querySelector(".table-column-filter-trigger"));
}

function ensureHeaderFilterControl(table, headerCell) {
    if (headerCell.hasAttribute("data-no-filter")) {
        headerCell.querySelector(".table-column-filter")?.remove();
        return null;
    }

    let wrap = headerCell.querySelector(".table-column-filter");
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "table-column-filter";
        wrap.innerHTML = `
            <button type="button" class="table-column-filter-trigger" aria-haspopup="dialog" aria-expanded="false">
                <span class="table-column-filter-icon" aria-hidden="true">
                    <svg viewBox="0 0 16 16" focusable="false" aria-hidden="true">
                        <path d="M2.25 3.25h11.5L9.5 8.34v3.54l-3 1.62V8.34L2.25 3.25Z" />
                    </svg>
                </span>
            </button>
            <div class="table-column-filter-menu" aria-hidden="true">
                <div class="table-column-filter-menu-head">
                    <strong class="table-column-filter-menu-title"></strong>
                    <button type="button" class="table-column-filter-clear">Temizle</button>
                </div>
                <div class="table-column-filter-mode-row">
                    <button type="button" class="table-column-filter-mode-toggle">Metin Filtreleri</button>
                    <span class="table-column-filter-mode-current">İçeren</span>
                    <div class="table-column-filter-mode-menu">
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="equals">Eşit</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="not_equals">Eşit değil</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="starts_with">İle başlar</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="ends_with">Şununla biter</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="contains">İçeren</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="not_contains">İçermiyor</button>
                        <button type="button" class="table-column-filter-mode-option" data-filter-mode="custom">Özel Filtre</button>
                    </div>
                </div>
                <label class="table-column-filter-criteria-wrap">
                    <input type="text" class="table-column-filter-criteria" placeholder="Metin kriteri (A; B; C)">
                </label>
                <label class="table-column-filter-search-wrap">
                    <input type="search" class="table-column-filter-search" placeholder="Seçenek ara">
                </label>
                <div class="table-column-filter-actions">
                    <button type="button" class="table-column-filter-select-all">Hepsini seç</button>
                    <button type="button" class="table-column-filter-deselect-all">Seçimi kaldır</button>
                </div>
                <div class="table-column-filter-options"></div>
                <div class="table-column-filter-empty" hidden>Sonuç bulunamadı.</div>
                <div class="table-column-filter-status">Filtre uygulanmıyor</div>
                <div class="table-column-filter-footer">
                    <button type="button" class="table-column-filter-apply">Tamam</button>
                    <button type="button" class="table-column-filter-cancel">İptal</button>
                </div>
            </div>
        `;
        headerCell.appendChild(wrap);
    }

    const trigger = wrap.querySelector(".table-column-filter-trigger");
    const menu = wrap.querySelector(".table-column-filter-menu");
    const title = wrap.querySelector(".table-column-filter-menu-title");
    const search = wrap.querySelector(".table-column-filter-search");
    const criteriaInput = wrap.querySelector(".table-column-filter-criteria");
    const clearButton = wrap.querySelector(".table-column-filter-clear");
    const selectAllButton = wrap.querySelector(".table-column-filter-select-all");
    const deselectAllButton = wrap.querySelector(".table-column-filter-deselect-all");
    const applyButton = wrap.querySelector(".table-column-filter-apply");
    const cancelButton = wrap.querySelector(".table-column-filter-cancel");
    const modeToggle = wrap.querySelector(".table-column-filter-mode-toggle");
    const modeMenu = wrap.querySelector(".table-column-filter-mode-menu");
    const columnKey = headerCell.dataset.columnKey;

    title.textContent = headerCell.dataset.columnLabel || "Filtre";

    if (wrap.dataset.bound !== "1") {
        wrap.dataset.bound = "1";

        trigger.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const willOpen = !menu.classList.contains("is-open");
            closeAllTableFilterMenus(willOpen ? menu : null);
            menu.classList.toggle("is-open", willOpen);
            menu.setAttribute("aria-hidden", willOpen ? "false" : "true");
            trigger.setAttribute("aria-expanded", willOpen ? "true" : "false");
            if (willOpen) {
                search.value = "";
                const state = getTableState(table);
                const currentFilter = normalizeColumnFilter(getResolvedFilterMap(table, state)[columnKey] || []);
                syncFilterMenuOptions(
                    headerCell,
                    collectColumnValues(table, columnKey, { preserveValues: currentFilter }),
                    currentFilter
                );
                positionFilterMenu(menu, trigger);
                criteriaInput?.focus();
            }
        });

        modeToggle?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            modeMenu?.classList.toggle("is-open");
        });

        modeMenu?.querySelectorAll(".table-column-filter-mode-option").forEach((button) => {
            button.addEventListener("click", () => {
                menu.dataset.filterMode = button.dataset.filterMode || "contains";
                syncFilterMenuOptions(
                    headerCell,
                    collectColumnValues(table, columnKey, { preserveValues: getMenuFilterSetting(menu) }),
                    getMenuFilterSetting(menu)
                );
                modeMenu.classList.remove("is-open");
            });
        });

        search.addEventListener("input", () => {
            syncFilterMenuOptions(
                headerCell,
                collectColumnValues(table, columnKey, { preserveValues: getMenuFilterSetting(menu) }),
                getMenuFilterSetting(menu)
            );
        });

        criteriaInput?.addEventListener("input", () => {
            updateFilterMenuStatus(menu, getMenuFilterSetting(menu));
            positionFilterMenu(menu, trigger);
        });

        clearButton.addEventListener("click", () => {
            search.value = "";
            if (criteriaInput) {
                criteriaInput.value = "";
            }
            menu.dataset.filterMode = "contains";
            syncFilterMenuOptions(headerCell, collectColumnValues(table, columnKey), []);
        });

        selectAllButton.addEventListener("click", () => {
            const currentFilter = getMenuFilterSetting(menu);
            const values = collectColumnValues(table, columnKey, {
                scopedFilterMap: getResolvedFilterMap(table),
                preserveValues: currentFilter
            });
            syncFilterMenuOptions(headerCell, values, { ...currentFilter, values });
        });

        deselectAllButton.addEventListener("click", () => {
            const currentFilter = getMenuFilterSetting(menu);
            syncFilterMenuOptions(headerCell, collectColumnValues(table, columnKey), { ...currentFilter, values: [] });
        });

        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

        menu.addEventListener("change", (event) => {
            const checkbox = event.target.closest('input[type="checkbox"]');
            if (!checkbox) {
                return;
            }
            updateFilterMenuStatus(menu, getMenuFilterSetting(menu));
        });

        applyButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const state = getTableState(table);
            const nextFilters = getResolvedFilterMap(table, state);
            const nextFilterSetting = normalizeColumnFilter(getMenuFilterSetting(menu));
            if (hasActiveColumnFilter(nextFilterSetting)) {
                nextFilters[columnKey] = nextFilterSetting;
            } else {
                delete nextFilters[columnKey];
            }
            state.filters = nextFilters;
            state.page = 1;
            setTableState(table, state);
            updateHeaderFilterTriggerState(headerCell, nextFilterSetting);
            applyTableFilters(table);
            menu.classList.remove("is-open");
            menu.setAttribute("aria-hidden", "true");
            modeMenu?.classList.remove("is-open");
            trigger.setAttribute("aria-expanded", "false");
        });

        cancelButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const state = getTableState(table);
            const currentFilter = normalizeColumnFilter(getResolvedFilterMap(table, state)[columnKey] || []);
            search.value = "";
            syncFilterMenuOptions(
                headerCell,
                collectColumnValues(table, columnKey, { preserveValues: currentFilter }),
                currentFilter
            );
            menu.classList.remove("is-open");
            menu.setAttribute("aria-hidden", "true");
            modeMenu?.classList.remove("is-open");
            trigger.setAttribute("aria-expanded", "false");
        });
    }

    return wrap;
}

function renderColumnFilters(table) {
    const state = getTableState(table);
    table.tHead.querySelector('[data-filter-row="1"]')?.remove();
    getHeaderCells(table).forEach((headerCell) => {
        const columnKey = headerCell.dataset.columnKey;
        const filterControl = ensureHeaderFilterControl(table, headerCell);
        if (!filterControl) {
            return;
        }

        const currentFilter = normalizeColumnFilter(getResolvedFilterMap(table, state)[columnKey] || []);
        const values = collectColumnValues(table, columnKey, { preserveValues: currentFilter });
        updateHeaderFilterTriggerState(headerCell, currentFilter);
        syncFilterMenuOptions(headerCell, values, currentFilter);
    });
}

function applyTableFilters(table) {
    const filterMap = getResolvedFilterMap(table);
    getBodyRows(table).forEach((row) => {
        const visible = rowMatchesFilterMap(row, filterMap);
        row.classList.toggle("is-filtered-out", !visible);
    });
    applyTableGrouping(table);
    paginateTable(table);
}

function getVisibleTableRows(table) {
    return getBodyRows(table).filter((row) => !row.classList.contains("is-filtered-out"));
}

function getCurrentPageRows(table) {
    return getVisibleTableRows(table).filter((row) => !row.classList.contains("is-paged-out"));
}

function getPageSize(state) {
    const size = Number(state.pageSize || 50);
    return Math.min(Math.max(size || 50, 1), 500);
}

function formatTryCurrency(value) {
    return new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number(value) || 0);
}

function formatSummaryNumber(value, digits = 0) {
    return Number(value || 0).toLocaleString("tr-TR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
    });
}

function isProductsListTable(table) {
    return table?.dataset.tableKey?.startsWith("products-list");
}

function getProductSummaryValue(row, columnKey) {
    const cell = row.querySelector(`[data-column-key="${columnKey}"]`);
    if (!cell) {
        return 0;
    }
    if (["purchase_price", "purchase_price_gross", "sale_price", "sale_price_gross"].includes(columnKey)) {
        return parseCurrencyText(getCellDisplayValue(cell));
    }
    return parseLocaleNumber(getCellDisplayValue(cell));
}

function calculateProductTableSummary(rows) {
    return rows.reduce((summary, row) => {
        summary.count += 1;
        summary.stock += getProductSummaryValue(row, "stock");
        summary.purchase += getProductSummaryValue(row, "purchase_price");
        summary.purchaseGross += getProductSummaryValue(row, "purchase_price_gross");
        summary.sale += getProductSummaryValue(row, "sale_price");
        summary.saleGross += getProductSummaryValue(row, "sale_price_gross");
        return summary;
    }, {
        count: 0,
        stock: 0,
        purchase: 0,
        purchaseGross: 0,
        sale: 0,
        saleGross: 0
    });
}

function buildProductSummarySection(title, summary) {
    return `
        <div class="products-summary-section">
            <div class="products-summary-section-title">${title}</div>
            <div class="products-summary-metrics">
                <div class="products-summary-chip">
                    <span class="products-summary-chip-label">Kayıt</span>
                    <strong>${formatSummaryNumber(summary.count)}</strong>
                </div>
                <div class="products-summary-chip">
                    <span class="products-summary-chip-label">Stok</span>
                    <strong>${formatSummaryNumber(summary.stock)}</strong>
                </div>
                <div class="products-summary-chip">
                    <span class="products-summary-chip-label">Alış</span>
                    <strong>${formatTryCurrency(summary.purchase)}</strong>
                </div>
                <div class="products-summary-chip">
                    <span class="products-summary-chip-label">Satış</span>
                    <strong>${formatTryCurrency(summary.sale)}</strong>
                </div>
            </div>
        </div>
    `;
}

function updateProductsTableSummary(table) {
    if (!isProductsListTable(table)) {
        return;
    }

    const panel = table.closest(".panel");
    const footer = panel?.querySelector(".table-footer-bar");
    if (!footer) {
        return;
    }

    let summaryHost = footer.querySelector("[data-products-summary]");
    if (!summaryHost) {
        summaryHost = document.createElement("div");
        summaryHost.className = "products-summary-bar";
        summaryHost.dataset.productsSummary = "1";
        footer.prepend(summaryHost);
    }

    const filteredRows = getVisibleTableRows(table);
    const pageRows = getCurrentPageRows(table);
    const pageSummary = calculateProductTableSummary(pageRows);
    const filteredSummary = calculateProductTableSummary(filteredRows);
    const showFilteredSummary = filteredRows.length !== pageRows.length;

    summaryHost.innerHTML = `
        <div class="products-summary-title">
            <span class="products-summary-eyebrow">Dip Toplam</span>
            <strong>Ürün Tablosu Özeti</strong>
        </div>
        <div class="products-summary-content">
            ${buildProductSummarySection("Bu Sayfa", pageSummary)}
            ${showFilteredSummary ? buildProductSummarySection("Filtre Sonucu", filteredSummary) : ""}
        </div>
    `;
}

function buildProductSummaryItems(title, summary) {
    return `
        <div class="products-summary-inline-group">
            <span class="products-summary-inline-title">${title}</span>
            <span class="products-summary-inline-item"><strong>Kayıt:</strong> ${formatSummaryNumber(summary.count)}</span>
            <span class="products-summary-inline-item"><strong>Stok:</strong> ${formatSummaryNumber(summary.stock)}</span>
            <span class="products-summary-inline-item"><strong>Alış:</strong> ${formatTryCurrency(summary.purchase)}</span>
            <span class="products-summary-inline-item"><strong>Satış:</strong> ${formatTryCurrency(summary.sale)}</span>
        </div>
    `;
}

function updateProductsTableSummary(table) {
    if (!isProductsListTable(table)) {
        return;
    }

    const panel = table.closest(".panel");
    const footer = panel?.querySelector(".table-footer-bar");
    if (!footer) {
        return;
    }

    let summaryHost = footer.querySelector("[data-products-summary]");
    if (!summaryHost) {
        summaryHost = document.createElement("div");
        summaryHost.className = "products-summary-bar";
        summaryHost.dataset.productsSummary = "1";
        footer.prepend(summaryHost);
    }

    const filteredRows = getVisibleTableRows(table);
    const pageRows = getCurrentPageRows(table);
    const pageSummary = calculateProductTableSummary(pageRows);
    const filteredSummary = calculateProductTableSummary(filteredRows);
    const showFilteredSummary = filteredRows.length !== pageRows.length;

    summaryHost.innerHTML = `
        <div class="products-summary-inline">
            ${buildProductSummaryItems("Bu Sayfa", pageSummary)}
            ${showFilteredSummary ? buildProductSummaryItems("Filtre Sonucu", filteredSummary) : ""}
        </div>
    `;
}

function updatePaginationUi(table, state, totalRows, pageRows) {
    const panel = table.closest(".panel");
    if (!panel) {
        return;
    }
    const pageInfo = panel.querySelector(".table-page-info");
    const pageSizeSelect = panel.querySelector(".table-page-size-select");
    const prevButton = panel.querySelector('[data-page-action="prev"]');
    const nextButton = panel.querySelector('[data-page-action="next"]');
    const totalPages = Math.max(1, Math.ceil(totalRows / getPageSize(state)));
    const currentPage = Math.min(state.page || 1, totalPages);
    const start = totalRows ? ((currentPage - 1) * getPageSize(state)) + 1 : 0;
    const end = totalRows ? start + pageRows - 1 : 0;

    if (pageInfo) {
        pageInfo.textContent = totalRows
            ? `${start}-${end} / ${totalRows} kayıt • Sayfa ${currentPage}/${totalPages}`
            : "0 kayıt";
    }
    if (pageSizeSelect) {
        pageSizeSelect.value = String(getPageSize(state));
    }
    if (prevButton) {
        prevButton.disabled = currentPage <= 1;
    }
    if (nextButton) {
        nextButton.disabled = currentPage >= totalPages;
    }
}

function updateProductsTableSummary(table) {
    if (!isProductsListTable(table)) {
        return;
    }

    const summaryRow = table.querySelector(".products-table-footer");
    if (!summaryRow) {
        return;
    }

    const summary = calculateProductTableSummary(getVisibleTableRows(table));
    const labelCell = summaryRow.querySelector(".products-table-footer-label");
    const purchaseCell = summaryRow.querySelector('[data-summary-key="purchase_price"]');
    const purchaseGrossCell = summaryRow.querySelector('[data-summary-key="purchase_price_gross"]');
    const saleCell = summaryRow.querySelector('[data-summary-key="sale_price"]');
    const saleGrossCell = summaryRow.querySelector('[data-summary-key="sale_price_gross"]');
    const stockCell = summaryRow.querySelector('[data-summary-key="stock"]');

    if (labelCell) {
        labelCell.textContent = summary.count ? `Dip Toplam (${formatSummaryNumber(summary.count)} kayıt)` : "Dip Toplam";
    }
    if (purchaseCell) {
        purchaseCell.textContent = formatTryCurrency(summary.purchase);
    }
    if (purchaseGrossCell) {
        purchaseGrossCell.textContent = formatTryCurrency(summary.purchaseGross);
    }
    if (saleCell) {
        saleCell.textContent = formatTryCurrency(summary.sale);
    }
    if (saleGrossCell) {
        saleGrossCell.textContent = formatTryCurrency(summary.saleGross);
    }
    if (stockCell) {
        stockCell.textContent = formatSummaryNumber(summary.stock);
    }

    summaryRow.classList.toggle("is-empty", summary.count === 0);
}

function paginateTable(table) {
    const state = getTableState(table);
    const visibleRows = getVisibleTableRows(table);
    const pageSize = getPageSize(state);
    const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
    const currentPage = Math.min(Math.max(Number(state.page || 1), 1), totalPages);
    state.page = currentPage;
    state.pageSize = pageSize;
    setTableState(table, state);

    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;

    visibleRows.forEach((row, index) => {
        row.classList.toggle("is-paged-out", index < start || index >= end);
    });

    getBodyRows(table)
        .filter((row) => row.classList.contains("is-filtered-out"))
        .forEach((row) => row.classList.remove("is-paged-out"));

    syncGroupRowVisibility(table);
    updatePaginationUi(table, state, visibleRows.length, visibleRows.slice(start, end).length);
    updateProductsTableSummary(table);
    syncProductSelectionState(table.closest("#products-table-section"));
}

function parseCurrencyText(value) {
    return Number(String(value).replace(/[^\d,-]/g, "").replace(/\./g, "").replace(",", ".")) || 0;
}

function getCellSortValue(cell) {
    if (!cell) {
        return "";
    }
    const rawText = getCellDisplayValue(cell);
    if (/^\d{2}\.\d{2}\.\d{4}$/.test(rawText)) {
        const [day, month, year] = rawText.split(".");
        return new Date(`${year}-${month}-${day}`).getTime();
    }
    if (/^#?\d+$/.test(rawText)) {
        return Number(rawText.replace("#", ""));
    }
    if (/[₺,.]/.test(rawText) && /\d/.test(rawText)) {
        return parseCurrencyText(rawText);
    }
    const numericValue = Number(rawText);
    if (!Number.isNaN(numericValue) && rawText !== "") {
        return numericValue;
    }
    return rawText.toLocaleLowerCase("tr");
}

function compareCellValues(valueA, valueB, direction = "asc") {
    if (typeof valueA === "number" && typeof valueB === "number") {
        return direction === "desc" ? valueB - valueA : valueA - valueB;
    }
    const comparison = String(valueA).localeCompare(String(valueB), "tr", { numeric: true, sensitivity: "base" });
    return direction === "desc" ? comparison * -1 : comparison;
}

function updateSortIndicators(table, sortState) {
    getHeaderCells(table).forEach((cell) => {
        cell.classList.remove("sort-asc", "sort-desc");
        if (!sortState || cell.dataset.columnKey !== sortState.key) {
            return;
        }
        cell.classList.add(sortState.direction === "desc" ? "sort-desc" : "sort-asc");
    });
}

function sortTable(table, columnKey, direction) {
    const body = table.tBodies[0];
    const sortableRows = getBodyRows(table);
    const lockedRows = Array.from(body.rows).filter((row) => !sortableRows.includes(row));

    sortableRows.sort((rowA, rowB) => {
        const cellA = rowA.querySelector(`[data-column-key="${columnKey}"]`);
        const cellB = rowB.querySelector(`[data-column-key="${columnKey}"]`);
        const valueA = getCellSortValue(cellA);
        const valueB = getCellSortValue(cellB);
        return compareCellValues(valueA, valueB, direction);
    });

    [...sortableRows, ...lockedRows].forEach((row) => body.appendChild(row));
}

function removeGroupRows(table) {
    table.querySelectorAll(".table-group-row").forEach((row) => row.remove());
}

function updateGroupZone(table, groupZone) {
    if (!groupZone) {
        return;
    }
    const state = getTableState(table);
    const groupKey = state.groupBy || "";
    const groupedHeader = getHeaderCells(table).find((cell) => cell.dataset.columnKey === groupKey);
    const text = groupZone.querySelector(".table-group-zone-text");
    const clearButton = groupZone.querySelector(".table-group-clear");

    if (groupedHeader) {
        text.textContent = `Gruplama: ${groupedHeader.dataset.columnLabel}`;
        clearButton?.classList.remove("is-hidden");
    } else {
        text.textContent = "Gruplamak için bir sütunu buraya sürükleyin";
        clearButton?.classList.add("is-hidden");
    }
}

function applyTableGrouping(table) {
    removeGroupRows(table);
    const state = getTableState(table);
    const groupKey = state.groupBy || "";
    if (!groupKey) {
        return;
    }

    const body = table.tBodies[0];
    const visibleRows = getBodyRows(table).filter((row) => !row.classList.contains("is-filtered-out"));
    const hiddenRows = getBodyRows(table).filter((row) => row.classList.contains("is-filtered-out"));
    if (!visibleRows.length) {
        return;
    }

    const indexedRows = visibleRows.map((row, index) => ({ row, index }));
    indexedRows.sort((itemA, itemB) => {
        const groupValueA = getCellSortValue(itemA.row.querySelector(`[data-column-key="${groupKey}"]`));
        const groupValueB = getCellSortValue(itemB.row.querySelector(`[data-column-key="${groupKey}"]`));
        const groupCompare = compareCellValues(groupValueA, groupValueB, "asc");
        if (groupCompare !== 0) {
            return groupCompare;
        }

        const sortState = state.sort;
        if (sortState?.key && sortState.key !== groupKey) {
            const sortValueA = getCellSortValue(itemA.row.querySelector(`[data-column-key="${sortState.key}"]`));
            const sortValueB = getCellSortValue(itemB.row.querySelector(`[data-column-key="${sortState.key}"]`));
            const sortCompare = compareCellValues(sortValueA, sortValueB, sortState.direction || "asc");
            if (sortCompare !== 0) {
                return sortCompare;
            }
        }

        return itemA.index - itemB.index;
    });

    const orderedRows = indexedRows.map((item) => item.row);
    const visibleColumnCount = getHeaderCells(table).filter((cell) => !cell.classList.contains("is-hidden-column")).length || getHeaderCells(table).length;
    let lastGroupValue = null;

    orderedRows.forEach((row) => {
        const rawValue = getCellDisplayValue(row.querySelector(`[data-column-key="${groupKey}"]`)) || "Boş";
        if (rawValue !== lastGroupValue) {
            const groupRow = document.createElement("tr");
            groupRow.className = "table-group-row";
            groupRow.dataset.groupValue = rawValue;
            groupRow.innerHTML = `<td colspan="${visibleColumnCount}"><span class="table-group-pill">${rawValue}</span></td>`;
            body.appendChild(groupRow);
            lastGroupValue = rawValue;
        }
        body.appendChild(row);
    });

    hiddenRows.forEach((row) => body.appendChild(row));
}

function syncGroupRowVisibility(table) {
    table.querySelectorAll(".table-group-row").forEach((groupRow) => {
        let nextRow = groupRow.nextElementSibling;
        let hasVisibleRows = false;
        while (nextRow && !nextRow.classList.contains("table-group-row")) {
            if (!nextRow.classList.contains("is-filtered-out") && !nextRow.classList.contains("is-paged-out")) {
                hasVisibleRows = true;
                break;
            }
            nextRow = nextRow.nextElementSibling;
        }
        groupRow.classList.toggle("is-paged-out", !hasVisibleRows);
    });
}

function buildColumnChooser(table) {
    const wrapper = table.closest(".table-wrap");
    if (!wrapper || wrapper.previousElementSibling?.classList.contains("table-toolbar")) {
        return;
    }

    const toolbar = document.createElement("div");
    toolbar.className = "table-toolbar";

    const buttonGroup = document.createElement("div");
    buttonGroup.className = "table-toolbar-group";

    const chooserContainer = document.createElement("div");
    chooserContainer.className = "table-toolbar-chooser";

    const chooserToggle = document.createElement("button");
    chooserToggle.type = "button";
    chooserToggle.className = "ghost-button table-toolbar-toggle";
    chooserToggle.textContent = "Sütunlar";

    const chooserMenu = document.createElement("div");
    chooserMenu.className = "column-chooser-menu";

    const clearFiltersButton = document.createElement("button");
    clearFiltersButton.type = "button";
    clearFiltersButton.className = "ghost-button";
    clearFiltersButton.textContent = "Filtreleri Temizle";

    const resetButton = document.createElement("button");
    resetButton.type = "button";
    resetButton.className = "ghost-button";
    resetButton.textContent = "Görünümü Sıfırla";

    chooserContainer.appendChild(chooserToggle);
    chooserContainer.appendChild(chooserMenu);
    buttonGroup.appendChild(chooserContainer);
    buttonGroup.appendChild(clearFiltersButton);
    buttonGroup.appendChild(resetButton);
    toolbar.appendChild(buttonGroup);

    const groupZone = document.createElement("div");
    groupZone.className = "table-group-zone";
    groupZone.innerHTML = `
        <span class="table-group-zone-text">Gruplamak için bir sütunu buraya sürükleyin</span>
        <button type="button" class="ghost-button table-group-clear is-hidden">Gruplamayı Kaldır</button>
    `;
    toolbar.appendChild(groupZone);
    wrapper.before(toolbar);

    const footer = document.createElement("div");
    footer.className = "table-footer-bar";

    const paginationGroup = document.createElement("div");
    paginationGroup.className = "table-pagination-group";
    paginationGroup.innerHTML = `
        <label class="table-page-size-label">
            <span>Kayıt</span>
            <select class="table-page-size-select">
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
                <option value="500">500</option>
            </select>
        </label>
        <button type="button" class="ghost-button table-page-button" data-page-action="prev" aria-label="Önceki sayfa">&#8249;</button>
        <span class="table-page-info">0 kayıt</span>
        <button type="button" class="ghost-button table-page-button" data-page-action="next" aria-label="Sonraki sayfa">&#8250;</button>
    `;
    footer.appendChild(paginationGroup);
    wrapper.after(footer);

    chooserToggle.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        chooserMenu.classList.toggle("is-open");
    });

    document.addEventListener("click", (event) => {
        if (!chooserContainer.contains(event.target)) {
            chooserMenu.classList.remove("is-open");
        }
        if (!event.target.closest(".table-column-filter")) {
            closeAllTableFilterMenus();
        }
    });

    clearFiltersButton.addEventListener("click", () => {
        const state = getTableState(table);
        delete state.filters;
        state.page = 1;
        setTableState(table, state);
        renderColumnFilters(table);
        applyTableFilters(table);
    });

    resetButton.addEventListener("click", () => {
        sessionStorage.removeItem(getTableStateKey(table));
        window.location.reload();
    });

    groupZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        groupZone.classList.add("is-drag-over");
    });

    groupZone.addEventListener("dragleave", () => {
        groupZone.classList.remove("is-drag-over");
    });

    groupZone.addEventListener("drop", (event) => {
        event.preventDefault();
        groupZone.classList.remove("is-drag-over");
        const sourceKey = event.dataTransfer.getData("text/plain");
        const sourceHeader = getHeaderCells(table).find((cell) => cell.dataset.columnKey === sourceKey);
        if (!sourceHeader || sourceHeader.hasAttribute("data-no-filter")) {
            return;
        }
        const state = getTableState(table);
        state.groupBy = sourceKey;
        state.page = 1;
        setTableState(table, state);
        updateGroupZone(table, groupZone);
        applyTableFilters(table);
    });

    groupZone.querySelector(".table-group-clear")?.addEventListener("click", () => {
        const state = getTableState(table);
        delete state.groupBy;
        state.page = 1;
        setTableState(table, state);
        updateGroupZone(table, groupZone);
        applyTableFilters(table);
    });

    const pageSizeSelect = paginationGroup.querySelector(".table-page-size-select");
    const prevButton = paginationGroup.querySelector('[data-page-action="prev"]');
    const nextButton = paginationGroup.querySelector('[data-page-action="next"]');

    pageSizeSelect?.addEventListener("change", () => {
        const state = getTableState(table);
        state.pageSize = Number(pageSizeSelect.value || 50);
        state.page = 1;
        setTableState(table, state);
        paginateTable(table);
    });

    prevButton?.addEventListener("click", () => {
        const state = getTableState(table);
        state.page = Math.max(1, Number(state.page || 1) - 1);
        setTableState(table, state);
        paginateTable(table);
    });

    nextButton?.addEventListener("click", () => {
        const state = getTableState(table);
        state.page = Number(state.page || 1) + 1;
        setTableState(table, state);
        paginateTable(table);
    });

    table.dataset.chooserMenuId = `chooser:${table.dataset.tableKey}`;
    renderColumnChooser(table, chooserMenu);
    updateGroupZone(table, groupZone);
}

function renderColumnChooser(table, chooserMenu) {
    chooserMenu.innerHTML = "";
    const state = getTableState(table);
    const hidden = new Set(state.hidden || []);
    getHeaderCells(table).forEach((headerCell) => {
        const item = document.createElement("label");
        item.className = "column-chooser-item";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = !hidden.has(headerCell.dataset.columnKey);
        checkbox.addEventListener("change", () => {
            const nextState = getTableState(table);
            const nextHidden = new Set(nextState.hidden || []);
            if (checkbox.checked) {
                nextHidden.delete(headerCell.dataset.columnKey);
            } else {
                nextHidden.add(headerCell.dataset.columnKey);
            }
            nextState.hidden = Array.from(nextHidden);
            setTableState(table, nextState);
            applyHiddenColumns(table, nextState.hidden);
            applyTableGrouping(table);
            paginateTable(table);
        });

        const text = document.createElement("span");
        text.textContent = headerCell.dataset.columnLabel;
        item.appendChild(checkbox);
        item.appendChild(text);
        chooserMenu.appendChild(item);
    });
}

function enableColumnSorting(table) {
    getHeaderCells(table).forEach((headerCell) => {
        if (headerCell.dataset.sortBound === "1" || headerCell.hasAttribute("data-no-sort")) {
            return;
        }
        headerCell.dataset.sortBound = "1";
        headerCell.addEventListener("click", (event) => {
            if (event.target.closest(".table-column-filter")) {
                return;
            }
            const state = getTableState(table);
            const nextDirection = state.sort?.key === headerCell.dataset.columnKey && state.sort.direction === "asc" ? "desc" : "asc";
            state.sort = { key: headerCell.dataset.columnKey, direction: nextDirection };
            setTableState(table, state);
            sortTable(table, state.sort.key, state.sort.direction);
            applyTableGrouping(table);
            updateSortIndicators(table, state.sort);
            paginateTable(table);
        });
    });
}

function enableColumnReorder(table) {
    getHeaderCells(table).forEach((headerCell) => {
        if (headerCell.dataset.dragBound === "1") {
            return;
        }
        headerCell.dataset.dragBound = "1";

        headerCell.addEventListener("dragstart", (event) => {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", headerCell.dataset.columnKey);
            headerCell.classList.add("is-dragging-column");
        });

        headerCell.addEventListener("dragend", () => {
            headerCell.classList.remove("is-dragging-column");
            getHeaderCells(table).forEach((cell) => cell.classList.remove("drag-over-column"));
        });

        headerCell.addEventListener("dragover", (event) => {
            event.preventDefault();
            headerCell.classList.add("drag-over-column");
        });

        headerCell.addEventListener("dragleave", () => {
            headerCell.classList.remove("drag-over-column");
        });

        headerCell.addEventListener("drop", (event) => {
            event.preventDefault();
            const sourceKey = event.dataTransfer.getData("text/plain");
            const targetKey = headerCell.dataset.columnKey;
            if (!sourceKey || sourceKey === targetKey) {
                return;
            }

            const state = getTableState(table);
            const currentOrder = state.order && state.order.length ? state.order : getColumnKeys(table);
            const nextOrder = currentOrder.filter((key) => key !== sourceKey);
            const targetIndex = nextOrder.indexOf(targetKey);
            nextOrder.splice(targetIndex, 0, sourceKey);
            state.order = nextOrder;
            setTableState(table, state);
            applyColumnOrder(table, state.order);
            applyHiddenColumns(table, state.hidden || []);
            applyTableGrouping(table);
            updateSortIndicators(table, state.sort);
            paginateTable(table);
            renderColumnChooser(table, table.closest(".panel").querySelector(".column-chooser-menu"));
        });
    });
}

function enableColumnResize(table) {
    getHeaderCells(table).forEach((headerCell) => {
        if (headerCell.dataset.resizeBound === "1" || headerCell.hasAttribute("data-no-resize")) {
            return;
        }
        headerCell.dataset.resizeBound = "1";
        headerCell.style.position = headerCell.style.position || "relative";

        const handle = document.createElement("span");
        handle.className = "table-column-resize-handle";
        handle.setAttribute("aria-hidden", "true");
        headerCell.appendChild(handle);

        handle.addEventListener("mousedown", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const startX = event.clientX;
            const startWidth = headerCell.getBoundingClientRect().width;
            const columnKey = headerCell.dataset.columnKey;

            const onMouseMove = (moveEvent) => {
                const nextWidth = Math.max(60, Math.round(startWidth + (moveEvent.clientX - startX)));
                applyColumnWidth(table, columnKey, nextWidth);
            };

            const onMouseUp = (upEvent) => {
                const nextWidth = Math.max(60, Math.round(startWidth + (upEvent.clientX - startX)));
                const state = getTableState(table);
                state.widths = state.widths || {};
                state.widths[columnKey] = nextWidth;
                setTableState(table, state);
                applyColumnWidth(table, columnKey, nextWidth);
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
            };

            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        });
    });
}

function initializeEnhancedTable(table) {
    if (table.dataset.enhanced === "1") {
        return;
    }
    table.dataset.enhanced = "1";
    if (!table.dataset.tableKey) {
        const section = table.closest("[id]");
        table.dataset.tableKey = section?.id || `table-${Math.random().toString(36).slice(2, 8)}`;
    }

    setupColumnMetadata(table);
    buildColumnChooser(table);
    enableColumnSorting(table);
    enableColumnReorder(table);
    enableColumnResize(table);

    const state = getTableState(table);
    const defaultOrder = getColumnKeys(table);
    if (!state.order || !state.order.length) {
        state.order = defaultOrder;
        setTableState(table, state);
    }

    applyColumnOrder(table, state.order);
    applyHiddenColumns(table, state.hidden || []);
    applyColumnWidths(table, state.widths || {});
    if (state.sort?.key) {
        sortTable(table, state.sort.key, state.sort.direction || "asc");
    }
    updateSortIndicators(table, state.sort);
    renderColumnFilters(table);
    applyHiddenColumns(table, state.hidden || []);
    applyTableGrouping(table);
    applyTableFilters(table);
    paginateTable(table);

    const chooserMenu = table.closest(".panel").querySelector(".column-chooser-menu");
    if (chooserMenu) {
        renderColumnChooser(table, chooserMenu);
    }
}

function initializeUi(root = document) {
    markRequiredFields(root);
    enhanceFilterForms(root);
    initializeReturnForms(root);
    initializeProductForms(root);
    initializeBulkProductActions(root);
    root.querySelectorAll("table[data-enhanced-table]").forEach((table) => initializeEnhancedTable(table));
    ensureTableExportButtons(root);
    document.dispatchEvent(new CustomEvent("lafemme:ui-updated", { detail: { root } }));
}

async function loadModalContent(url, title) {
    openModal(title, '<div class="modal-loading">İçerik yükleniyor...</div>');
    const modalUrl = new URL(url, window.location.origin);
    modalUrl.searchParams.set("modal", "1");

    showBusy("Form yükleniyor...");
    try {
        const response = await fetch(modalUrl, {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-Modal-Request": "1"
            }
        });
        const html = await response.text();
        if (!response.ok) {
            throw new Error("Modal içeriği yüklenemedi.");
        }
        openModal(title, html);
    } catch (error) {
        openModal(title, `<p class="form-error">${error.message}</p>`);
    } finally {
        hideBusy();
    }
}

async function refreshTarget(selector, fallbackUrl = null) {
    if (!selector) {
        return;
    }

    const target = document.querySelector(selector);
    if (!target) {
        window.location.reload();
        return;
    }

    const partialUrl = target.dataset.partialUrl || fallbackUrl;
    if (!partialUrl) {
        window.location.reload();
        return;
    }

    try {
        const response = await fetch(partialUrl, {
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });
        const html = await response.text();
        if (!response.ok) {
            throw new Error("Liste güncellenemedi.");
        }
        target.outerHTML = html;
        initializeUi(document);
    } catch (error) {
        showToast(error.message, "error");
        window.location.reload();
    }
}

async function submitAjaxForm(form) {
    const method = (form.getAttribute("method") || "get").toUpperCase();
    const action = form.getAttribute("action") || window.location.href;
    const formRefreshTarget = form.dataset.refreshTarget;
    const refreshUrl = form.dataset.refreshUrl || null;
    const isModalForm = Boolean(form.closest("#globalModal"));

    showBusy("İşlem kaydediliyor...");
    try {
        if (method === "GET") {
            const url = new URL(action, window.location.origin);
            const formData = new FormData(form);
            url.search = new URLSearchParams(formData).toString();
            if (isModalForm) {
                url.searchParams.set("modal", "1");
            }

            const response = await fetch(url, {
                headers: isModalForm
                    ? {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-Modal-Request": "1"
                    }
                    : {
                        "X-Requested-With": "XMLHttpRequest"
                    }
            });
            const html = await response.text();
            if (!response.ok) {
                throw new Error("Form yüklenemedi.");
            }
            globalModalBody.innerHTML = html;
            initializeUi(globalModalBody);
            return;
        }

        const formData = new FormData(form);
        const response = await fetch(action, {
            method,
            headers: isModalForm
                ? {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Modal-Request": "1"
                }
                : {
                    "X-Requested-With": "XMLHttpRequest"
                },
            body: formData
        });

        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            const data = await response.json();
            if (!response.ok || !data.success) {
                if (data.html) {
                    globalModalBody.innerHTML = data.html;
                    initializeUi(globalModalBody);
                    if (data.message) {
                        showToast(data.message, "error");
                    }
                    return;
                }
                throw new Error(data.message || "İşlem başarısız.");
            }

            const nextRefreshTarget = data.refresh_target || formRefreshTarget;
            const nextRefreshUrl = data.refresh_url || refreshUrl;
            const printUrl = data.print_url || null;

            if (data.keep_open) {
                if (data.html) {
                    globalModalBody.innerHTML = data.html;
                    initializeUi(globalModalBody);
                }
                showToast(data.message || "İşlem tamamlandı.", "success");
                if (nextRefreshTarget) {
                    await window.refreshTarget(nextRefreshTarget, nextRefreshUrl);
                }
                if (printUrl) {
                    window.open(printUrl, "_blank", "noopener");
                }
            } else {
                closeModal();
                showToast(data.message || "İşlem tamamlandı.", "success");
                if (nextRefreshTarget) {
                    await window.refreshTarget(nextRefreshTarget, nextRefreshUrl);
                    if (printUrl) {
                        window.open(printUrl, "_blank", "noopener");
                    }
                } else if (data.redirect_url) {
                    if (printUrl) {
                        window.open(printUrl, "_blank", "noopener");
                    }
                    if (data.persist_message_after_redirect && data.message) {
                        storePendingToast(data.message, "success");
                    }
                    window.location.href = data.redirect_url;
                } else if (printUrl) {
                    window.open(printUrl, "_blank", "noopener");
                } else {
                    window.location.reload();
                }
            }
            return;
        }

        const html = await response.text();
        globalModalBody.innerHTML = html;
        initializeUi(globalModalBody);
    } finally {
        hideBusy();
    }
}

function bindDocumentEvents() {
    document.querySelectorAll("[data-close-confirm]").forEach((element) => {
        if (element.dataset.confirmBound === "1") {
            return;
        }
        element.dataset.confirmBound = "1";
        element.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            closeConfirmModal();
        });
    });

    document.addEventListener("click", async (event) => {
        const exportTrigger = event.target.closest("[data-export-table]");
        if (exportTrigger) {
            event.preventDefault();
            const table = document.querySelector(exportTrigger.dataset.exportTable);
            if (table) {
                exportTableToExcel(table);
            } else {
                showToast("Aktarılacak tablo bulunamadı.", "error");
            }
            return;
        }

        const selectedProductListAction = event.target.closest("[data-product-list-action]");
        if (selectedProductListAction) {
            const section = selectedProductListAction.closest("#products-table-section");
            const selectedIds = getSelectedProductIds(section);
            if (selectedIds.length > 0) {
                event.preventDefault();
                await executeBulkProductAction(selectedProductListAction, selectedProductListAction.dataset.productListAction);
                return;
            }
        }

        const modalTrigger = event.target.closest("[data-modal-url]");
        if (modalTrigger) {
            event.preventDefault();
            await loadModalContent(
                modalTrigger.dataset.modalUrl || modalTrigger.getAttribute("href"),
                modalTrigger.dataset.modalTitle || modalTrigger.textContent.trim()
            );
            return;
        }

        const closeTrigger = event.target.closest("[data-close-modal]");
        if (closeTrigger) {
            event.preventDefault();
            if (globalModal?.classList.contains("is-open")) {
                closeModal();
            } else if (closeTrigger.dataset.closeHref) {
                window.location.href = closeTrigger.dataset.closeHref;
            } else {
                window.history.back();
            }
            return;
        }

        const closeConfirmTrigger = event.target.closest("[data-close-confirm]");
        if (closeConfirmTrigger) {
            event.preventDefault();
            closeConfirmModal();
            return;
        }

        const bulkActionTrigger = event.target.closest(".bulk-action-trigger");
        if (bulkActionTrigger) {
            event.preventDefault();
            await executeBulkProductAction(bulkActionTrigger);
            return;
        }

        const bulkActionExecute = event.target.closest(".bulk-action-execute");
        if (bulkActionExecute) {
            event.preventDefault();
            await executeBulkProductAction(bulkActionExecute);
            return;
        }

        const productListAction = event.target.closest("[data-product-list-action]");
        if (productListAction) {
            const section = productListAction.closest("#products-table-section");
            const selectedIds = getSelectedProductIds(section);
            if (selectedIds.length > 0) {
                event.preventDefault();
                await executeBulkProductAction(productListAction, productListAction.dataset.productListAction);
                return;
            }
        }

        const confirmTrigger = event.target.closest("[data-confirm-url]");
        if (confirmTrigger) {
            event.preventDefault();
            const recordCode = (confirmTrigger.dataset.confirmRecordCode || "").trim();
            const recordLabel = (confirmTrigger.dataset.confirmRecordLabel || "").trim();
            openConfirmModal(
                {
                    title: confirmTrigger.dataset.confirmTitle || "Kaydı sil",
                    message: confirmTrigger.dataset.confirmMessage,
                    detailsHtml: recordCode || recordLabel
                        ? buildConfirmRecordsHtml([{ code: recordCode, name: recordLabel }])
                        : ""
                },
                async () => {
                    showBusy("İşlem uygulanıyor...");
                    try {
                        const response = await fetch(confirmTrigger.dataset.confirmUrl, {
                            method: confirmTrigger.dataset.confirmMethod || "POST",
                            headers: {
                                "X-Requested-With": "XMLHttpRequest"
                            }
                        });
                        const data = await response.json();
                        if (!response.ok || !data.success) {
                            throw new Error(data.message || "Silme işlemi başarısız.");
                        }
                        closeConfirmModal();
                        showToast(data.message || "Kayıt silindi.", "success");
                        const selector = data.refresh_target || confirmTrigger.dataset.refreshTarget;
                        if (selector) {
                            await window.refreshTarget(selector, data.refresh_url || confirmTrigger.dataset.refreshUrl || null);
                        } else {
                            window.location.reload();
                        }
                    } catch (error) {
                        closeConfirmModal();
                        showToast(error.message, "error");
                    } finally {
                        hideBusy();
                    }
                }
            );
            return;
        }

        const remoteTrigger = event.target.closest("[data-remote-action]");
        if (remoteTrigger) {
            event.preventDefault();
            showBusy("İşlem uygulanıyor...");
            try {
                const response = await fetch(remoteTrigger.dataset.remoteUrl, {
                    method: remoteTrigger.dataset.remoteMethod || "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.message || "İşlem tamamlanamadı.");
                }
                showToast(data.message || "İşlem tamamlandı.", "success");
                const selector = data.refresh_target || remoteTrigger.dataset.refreshTarget;
                if (selector) {
                    await window.refreshTarget(selector, data.refresh_url || remoteTrigger.dataset.refreshUrl || null);
                }
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                hideBusy();
            }
            return;
        }

        const stockButton = event.target.closest(".js-stock-save");
        if (stockButton) {
            const wrapper = stockButton.closest(".inline-stock-editor");
            const input = wrapper?.querySelector("input");
            const endpoint = wrapper?.dataset.stockEndpoint;
            if (!input || !endpoint) {
                return;
            }

            showBusy("Stok güncelleniyor...");
            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ stock_quantity: Number(input.value) })
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.message || "Stok güncelleme başarısız.");
                }
                const row = stockButton.closest("tr");
                const section = stockButton.closest("#products-table-section");
                if (section?.dataset.stockPaletteEnabled === "1") {
                    const lowThreshold = Number(row?.dataset.lowThreshold || section?.dataset.lowThreshold || 5);
                    const criticalThreshold = Number(row?.dataset.criticalThreshold || section?.dataset.criticalThreshold || (lowThreshold * 2));
                    row?.classList.remove("stock-status-low", "stock-status-critical", "stock-status-healthy");
                    if (data.stock_quantity <= lowThreshold) {
                        row?.classList.add("stock-status-low");
                    } else if (data.stock_quantity <= criticalThreshold) {
                        row?.classList.add("stock-status-critical");
                    } else {
                        row?.classList.add("stock-status-healthy");
                    }
                }
                const table = row?.closest("table[data-enhanced-table]");
                if (table) {
                    updateProductsTableSummary(table);
                }
                showToast(data.message, "success");
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                hideBusy();
            }
        }
    });

    document.addEventListener("submit", async (event) => {
        const confirmForm = event.target.closest("form[data-confirm-form]");
        if (confirmForm) {
            event.preventDefault();
            const recordCode = (confirmForm.dataset.confirmRecordCode || "").trim();
            const recordLabel = (confirmForm.dataset.confirmRecordLabel || "").trim();
            openConfirmModal(
                {
                    title: confirmForm.dataset.confirmTitle || "Kaydı sil",
                    message: confirmForm.dataset.confirmMessage,
                    detailsHtml: recordCode || recordLabel
                        ? buildConfirmRecordsHtml([{ code: recordCode, name: recordLabel }])
                        : ""
                },
                async () => {
                    showBusy("İşlem uygulanıyor...");
                    try {
                        const response = await fetch(confirmForm.getAttribute("action"), {
                            method: confirmForm.dataset.confirmMethod || confirmForm.getAttribute("method") || "POST",
                            headers: {
                                "X-Requested-With": "XMLHttpRequest"
                            },
                            body: new FormData(confirmForm)
                        });
                        const data = await response.json();
                        if (!response.ok || !data.success) {
                            throw new Error(data.message || "Silme işlemi başarısız.");
                        }
                        closeConfirmModal();
                        showToast(data.message || "Kayıt silindi.", "success");
                        const selector = data.refresh_target || confirmForm.dataset.refreshTarget;
                        if (selector) {
                            await window.refreshTarget(selector, data.refresh_url || confirmForm.dataset.refreshUrl || null);
                        } else {
                            window.location.reload();
                        }
                    } catch (error) {
                        closeConfirmModal();
                        showToast(error.message, "error");
                    } finally {
                        hideBusy();
                    }
                }
            );
            return;
        }

        const form = event.target.closest("form[data-ajax-form]");
        if (!form) {
            return;
        }
        event.preventDefault();
        try {
            await submitAjaxForm(form);
        } catch (error) {
            hideBusy();
            showToast(error.message, "error");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeAllTableFilterMenus();
            closeModal();
            closeConfirmModal();
        }
    });

    window.addEventListener("resize", () => closeAllTableFilterMenus());
}

confirmModalSubmit?.addEventListener("click", async () => {
    if (!confirmAction) {
        closeConfirmModal();
        return;
    }
    try {
        await confirmAction();
    } catch (error) {
        showToast(error.message || "İşlem tamamlanamadı.", "error");
    }
});

window.showToast = showToast;
window.openModal = openModal;
window.showBusy = showBusy;
window.hideBusy = hideBusy;
window.refreshTarget = refreshTarget;
window.openConfirmModal = openConfirmModal;
window.closeConfirmModal = closeConfirmModal;
window.handleCloseConfirmClick = handleCloseConfirmClick;

flushPendingToast();
initializeUi(document);
bindDocumentEvents();
// Add the authenticated session's CSRF token to every same-origin write request.
(() => {
    const nativeFetch = window.fetch.bind(window);
    const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
    if (token) {
        document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
            if (form.querySelector('input[name="csrf_token"]')) return;
            const field = document.createElement("input");
            field.type = "hidden";
            field.name = "csrf_token";
            field.value = token;
            form.appendChild(field);
        });
    }
    window.fetch = (input, options = {}) => {
        const method = String(options.method || "GET").toUpperCase();
        if (!token || !["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
            return nativeFetch(input, options);
        }
        const target = new URL(typeof input === "string" ? input : input.url, window.location.href);
        if (target.origin !== window.location.origin) {
            return nativeFetch(input, options);
        }
        const headers = new Headers(options.headers || (input instanceof Request ? input.headers : undefined));
        headers.set("X-CSRF-Token", token);
        return nativeFetch(input, { ...options, headers });
    };
})();
