(function () {
    const TABLE_STATE_PREFIX = "lafemme_table_state:";

    function getStateKey(table) {
        return `${TABLE_STATE_PREFIX}${table.dataset.tableKey}`;
    }

    function getState(table) {
        try {
            return JSON.parse(sessionStorage.getItem(getStateKey(table)) || "{}");
        } catch {
            return {};
        }
    }

    function setState(table, nextState) {
        sessionStorage.setItem(getStateKey(table), JSON.stringify(nextState));
    }

    function getHeaderRow(table) {
        return table.tHead?.rows?.[0] || null;
    }

    function getHeaderCells(table) {
        return Array.from(getHeaderRow(table)?.cells || []);
    }

    function getDataRows(table) {
        const header = getHeaderRow(table);
        return Array.from(table.tBodies[0]?.rows || []).filter((row) => row.cells.length === header.cells.length);
    }

    function getCellValue(cell) {
        if (!cell) {
            return "";
        }
        const input = cell.querySelector("input, select, textarea");
        if (input) {
            return String(input.value || "").trim();
        }
        return cell.textContent.replace(/\s+/g, " ").trim();
    }

    function ensureFilterRow(table) {
        if (table.tHead.rows.length > 1 && table.tHead.rows[1].dataset.filterRow === "1") {
            return table.tHead.rows[1];
        }

        const row = document.createElement("tr");
        row.className = "table-filter-row";
        row.dataset.filterRow = "1";

        getHeaderCells(table).forEach((headerCell, index) => {
            const filterCell = document.createElement("th");
            filterCell.dataset.columnIndex = String(index);
            if (headerCell.hasAttribute("data-no-filter")) {
                filterCell.className = "table-filter-cell table-filter-disabled";
                row.appendChild(filterCell);
                return;
            }

            const select = document.createElement("select");
            select.className = "table-filter-select";
            select.dataset.columnIndex = String(index);
            filterCell.className = "table-filter-cell";
            filterCell.appendChild(select);
            row.appendChild(filterCell);
        });

        table.tHead.appendChild(row);
        return row;
    }

    function collectColumnValues(table, columnIndex) {
        const values = new Set();
        getDataRows(table).forEach((row) => {
            const value = getCellValue(row.cells[columnIndex]);
            if (value) {
                values.add(value);
            }
        });
        return Array.from(values).sort((a, b) => a.localeCompare(b, "tr", { numeric: true, sensitivity: "base" }));
    }

    function renderFilters(table) {
        const state = getState(table);
        const filterRow = ensureFilterRow(table);

        Array.from(filterRow.cells).forEach((filterCell) => {
            const select = filterCell.querySelector("select");
            if (!select) {
                return;
            }

            const columnIndex = Number(select.dataset.columnIndex);
            const currentValue = state.filters?.[columnIndex] || "";
            const values = collectColumnValues(table, columnIndex);
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
                const nextState = getState(table);
                nextState.filters = nextState.filters || {};
                if (select.value) {
                    nextState.filters[columnIndex] = select.value;
                } else {
                    delete nextState.filters[columnIndex];
                }
                setState(table, nextState);
                applyFilters(table);
            });
        });
    }

    function applyFilters(table) {
        const state = getState(table);
        const filters = state.filters || {};

        getDataRows(table).forEach((row) => {
            const visible = Object.entries(filters).every(([index, filterValue]) => {
                if (!filterValue) {
                    return true;
                }
                return getCellValue(row.cells[Number(index)]) === filterValue;
            });
            row.classList.toggle("is-filtered-out", !visible);
        });
    }

    function ensureToolbarButtons(table) {
        const toolbar = table.closest(".panel")?.querySelector(".table-toolbar-group");
        if (!toolbar || toolbar.querySelector(".js-clear-column-filters")) {
            normalizeToolbarTexts(toolbar);
            return;
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "ghost-button js-clear-column-filters";
        button.textContent = "Filtreleri Temizle";
        button.addEventListener("click", () => {
            const state = getState(table);
            delete state.filters;
            setState(table, state);
            renderFilters(table);
            applyFilters(table);
        });

        const resetButton = toolbar.querySelector(".ghost-button:last-child");
        if (resetButton) {
            toolbar.insertBefore(button, resetButton);
        } else {
            toolbar.appendChild(button);
        }

        normalizeToolbarTexts(toolbar);
    }

    function normalizeToolbarTexts(toolbar) {
        if (!toolbar) {
            return;
        }

        const chooserToggle = toolbar.querySelector(".table-toolbar-toggle");
        if (chooserToggle) {
            chooserToggle.textContent = "Sütunlar";
        }

        const resetButton = Array.from(toolbar.querySelectorAll(".ghost-button")).find((button) => {
            return !button.classList.contains("table-toolbar-toggle") && !button.classList.contains("js-clear-column-filters");
        });
        if (resetButton) {
            resetButton.textContent = "Görünümü Sıfırla";
        }
    }

    function initTable(table) {
        if (table.dataset.filterEnhanced === "1") {
            renderFilters(table);
            applyFilters(table);
            ensureToolbarButtons(table);
            return;
        }

        table.dataset.filterEnhanced = "1";
        renderFilters(table);
        applyFilters(table);
        ensureToolbarButtons(table);
    }

    function init(root = document) {
        root.querySelectorAll("table[data-enhanced-table]").forEach((table) => initTable(table));
    }

    document.addEventListener("DOMContentLoaded", () => init(document));
    document.addEventListener("lafemme:ui-updated", (event) => init(event.detail?.root || document));
})();
