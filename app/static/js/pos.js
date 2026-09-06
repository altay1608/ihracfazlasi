(function () {
    const barcodeInput = document.getElementById("barcodeInput");
    const cartTableBody = document.querySelector("#cartTable tbody");
    const paymentMethod = document.getElementById("paymentMethod");
    const completeButton = document.getElementById("completeSaleBtn");
    const feedback = document.getElementById("posFeedback");
    const manualDiscountInput = document.getElementById("manualDiscountInput");
    const discountRateInput = document.getElementById("discountRateInput");
    const customerSearchInput = document.getElementById("customerSearchInput");
    const customerSearchResults = document.getElementById("customerSearchResults");
    const recentCustomers = document.getElementById("recentCustomers");
    const refreshRecentCustomers = document.getElementById("refreshRecentCustomers");
    const customerNameInput = document.getElementById("customerName");
    const customerMobileInput = document.getElementById("customerMobile");
    const customerEmailInput = document.getElementById("customerEmail");
    const customerProvinceSelect = document.getElementById("customerProvince");
    const customerDistrictSelect = document.getElementById("customerDistrict");
    const customerAddressInput = document.getElementById("customerAddress");
    const customerTaxOfficeInput = document.getElementById("customerTaxOffice");
    const customerTaxNumberInput = document.getElementById("customerTaxNumber");
    const customerNoteInput = document.getElementById("customerNote");
    const cityMap = window.posConfig?.cityMap || {};
    const lineEditsLocked = Boolean(window.posConfig?.lineEditsLocked);
    const provinceList = Object.keys(cityMap).sort((a, b) => a.localeCompare(b, "tr"));
    const vatRate = Number(window.posConfig?.vatRate || 0.10);
    const cart = new Map();
    let searchTimer = null;

    if (paymentMethod) {
        const defaultCashOption = Array.from(paymentMethod.options).find((option) => {
            const value = String(option.value || "").trim().toLocaleLowerCase("tr");
            const text = String(option.textContent || "").trim().toLocaleLowerCase("tr");
            return value === "nakit" || text === "nakit";
        });
        if (defaultCashOption) {
            paymentMethod.value = defaultCashOption.value;
        }
    }

    function formatCurrency(value) {
        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: "TRY",
            minimumFractionDigits: 2
        }).format(Number(value || 0));
    }

    function formatPercent(value) {
        return `%${Number(value || 0).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function formatInputAmount(value) {
        return Number(value || 0).toLocaleString("tr-TR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function roundAmount(value) {
        return Math.round(Number(value || 0) * 100) / 100;
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

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function parseLocaleNumber(value) {
        if (value === null || value === undefined) {
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
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function showPosMessage(title, message) {
        if (window.openModal) {
            window.openModal(
                title,
                `
                    <div class="modal-copy-stack">
                        <p>${message}</p>
                        <div class="modal-inline-actions">
                            <button type="button" class="primary-button" data-close-modal>Tamam</button>
                        </div>
                    </div>
                `
            );
            return;
        }
        feedback.textContent = message;
    }

    function syncDistrictFieldState(province) {
        if (!customerDistrictSelect) {
            return;
        }
        const hasProvince = Boolean((province || "").trim());
        customerDistrictSelect.disabled = !hasProvince;
        customerDistrictSelect.title = hasProvince
            ? "Seçilen ile bağlı ilçeleri seçin."
            : "Önce il seçin, sonra ilçe listesi açılır.";
    }

    function populateProvinceOptions(selectedProvince = "") {
        if (!customerProvinceSelect) {
            return;
        }
        customerProvinceSelect.innerHTML = '<option value="">İl seçin</option>';
        provinceList.forEach((province) => {
            const option = document.createElement("option");
            option.value = province;
            option.textContent = province;
            if (province === selectedProvince) {
                option.selected = true;
            }
            customerProvinceSelect.appendChild(option);
        });
        populateDistrictOptions(selectedProvince, "");
    }

    function populateDistrictOptions(province, selectedDistrict = "") {
        if (!customerDistrictSelect) {
            return;
        }
        const districts = province ? (cityMap[province] || []) : [];
        customerDistrictSelect.innerHTML = "";

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = province ? "İlçe seçin" : "Önce il seçin";
        customerDistrictSelect.appendChild(placeholder);

        districts.forEach((district) => {
            const option = document.createElement("option");
            option.value = district;
            option.textContent = district;
            if (district === selectedDistrict) {
                option.selected = true;
            }
            customerDistrictSelect.appendChild(option);
        });

        syncDistrictFieldState(province);
    }

    function getSelectedCityValue() {
        const province = customerProvinceSelect?.value?.trim() || "";
        const district = customerDistrictSelect?.value?.trim() || "";
        if (province && district) {
            return `${province} / ${district}`;
        }
        return province || "";
    }

    function setSelectedCityValue(rawValue) {
        const value = (rawValue || "").trim();
        if (!value) {
            if (customerProvinceSelect) {
                customerProvinceSelect.value = "";
            }
            populateDistrictOptions("");
            return;
        }

        const parts = value.split("/").map((part) => part.trim()).filter(Boolean);
        const province = parts[0] || "";
        const district = parts[1] || "";

        if (customerProvinceSelect) {
            customerProvinceSelect.value = province;
        }
        populateDistrictOptions(province, district);
    }

    function getCustomerPayload() {
        return {
            customer_name: customerNameInput?.value?.trim() || "",
            customer_phone: "",
            customer_mobile: customerMobileInput?.value?.trim() || "",
            customer_email: customerEmailInput?.value?.trim() || "",
            customer_city: getSelectedCityValue(),
            customer_address: customerAddressInput?.value?.trim() || "",
            customer_tax_office: customerTaxOfficeInput?.value?.trim() || "",
            customer_tax_number: customerTaxNumberInput?.value?.trim() || "",
            customer_note: customerNoteInput?.value?.trim() || ""
        };
    }

    function fillCustomerForm(customer) {
        if (!customer) {
            return;
        }
        if (customerNameInput) customerNameInput.value = customer.name || "";
        if (customerMobileInput) customerMobileInput.value = customer.mobile || customer.phone || "";
        if (customerEmailInput) customerEmailInput.value = customer.email || "";
        if (customerTaxOfficeInput) customerTaxOfficeInput.value = customer.tax_office || "";
        if (customerTaxNumberInput) customerTaxNumberInput.value = customer.tax_number || "";
        if (customerAddressInput) customerAddressInput.value = customer.address || "";
        if (customerNoteInput) customerNoteInput.value = customer.note || "";
        setSelectedCityValue(customer.city || "");
    }

    function resetCustomerInputs() {
        [
            customerNameInput,
            customerMobileInput,
            customerEmailInput,
            customerTaxOfficeInput,
            customerTaxNumberInput,
            customerAddressInput,
            customerNoteInput
        ].forEach((input) => {
            if (input) {
                input.value = "";
            }
        });
        setSelectedCityValue("");
    }

    function renderSearchResults(results) {
        if (!customerSearchResults) {
            return;
        }
        if (!results.length) {
            customerSearchResults.innerHTML = '<div class="customer-search-empty">Eşleşen kayıt bulunamadı.</div>';
            customerSearchResults.hidden = false;
            customerSearchResults.classList.remove("is-hidden");
            return;
        }

        customerSearchResults.innerHTML = results.map((item) => `
            <button type="button" class="customer-search-item" data-customer='${JSON.stringify(item).replace(/'/g, "&apos;")}'>
                <strong>${item.name || "İsimsiz Kayıt"}</strong>
                <span>${item.mobile || item.email || item.tax_number || item.city || "İletişim bilgisi yok"}</span>
            </button>
        `).join("");
        customerSearchResults.hidden = false;
        customerSearchResults.classList.remove("is-hidden");
    }

    function renderRecentCustomers(results) {
        if (!recentCustomers) {
            return;
        }
        if (!results.length) {
            recentCustomers.innerHTML = '<p class="muted">Henüz kayıtlı satış müşteri bilgisi yok.</p>';
            return;
        }

        recentCustomers.innerHTML = results.map((item) => `
            <button type="button" class="customer-recent-chip" data-customer='${JSON.stringify(item).replace(/'/g, "&apos;")}'>
                <strong>${item.name || "İsimsiz"}</strong>
                <span>${item.mobile || item.email || item.city || "Kayıt"}</span>
            </button>
        `).join("");
    }

    async function loadRecentCustomers() {
        if (!recentCustomers || !window.posConfig?.recentCustomersUrl) {
            return;
        }
        try {
            const response = await fetch(window.posConfig.recentCustomersUrl);
            const data = await response.json();
            renderRecentCustomers(data.results || []);
        } catch {
            recentCustomers.innerHTML = '<p class="muted">Son kullanılanlar yüklenemedi.</p>';
        }
    }

    async function searchCustomers(query) {
        if (!window.posConfig?.customerSearchUrl || !customerSearchResults) {
            return;
        }
        const url = new URL(window.posConfig.customerSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        try {
            const response = await fetch(url);
            const data = await response.json();
            renderSearchResults(data.results || []);
        } catch {
            customerSearchResults.innerHTML = '<div class="customer-search-empty">Arama sırasında hata oluştu.</div>';
            customerSearchResults.hidden = false;
            customerSearchResults.classList.remove("is-hidden");
        }
    }

    function getSummary() {
        let subtotal = 0;
        cart.forEach((item) => {
            subtotal += Number(item.unit_price) * Number(item.quantity);
        });

        subtotal = roundAmount(subtotal);
        const grossBeforeDiscount = roundCustomerPrice(subtotal * (1 + vatRate));
        const discountAmount = clamp(roundAmount(parseLocaleNumber(manualDiscountInput?.value || 0)), 0, grossBeforeDiscount);
        const discountRate = grossBeforeDiscount ? roundAmount((discountAmount / grossBeforeDiscount) * 100) : 0;
        const grandTotal = roundCustomerPrice(grossBeforeDiscount - discountAmount);
        const netSubtotal = roundAmount(grandTotal / (1 + vatRate));
        const vatAmount = roundAmount(grandTotal - netSubtotal);

        return { subtotal, grossBeforeDiscount, discountAmount, discountRate, vatAmount, grandTotal, netSubtotal };
    }

    function updateSummary() {
        const summary = getSummary();
        document.getElementById("subtotalAmount").textContent = formatCurrency(summary.subtotal);
        document.getElementById("vatAmount").textContent = formatCurrency(summary.vatAmount);
        document.getElementById("grandTotalAmount").textContent = formatCurrency(summary.grandTotal);
        if (discountRateInput) {
            discountRateInput.value = formatPercent(summary.discountRate);
        }
    }

    function mutateQuantity(productId, quantity) {
        if (lineEditsLocked) {
            return;
        }
        const item = cart.get(productId);
        if (!item) {
            return;
        }
        const maxQuantity = Number(item.max_quantity || 0);
        if (quantity <= 0) {
            cart.delete(productId);
        } else if (maxQuantity && quantity > maxQuantity) {
            showPosMessage("Stok Uyarısı", "Uygun stok miktarı yok, satış gerçekleştiremezsiniz.");
            renderCart();
        } else {
            item.quantity = quantity;
            if (Array.isArray(item.scanned_barcodes) && item.scanned_barcodes.length > quantity) {
                item.scanned_barcodes = item.scanned_barcodes.slice(0, quantity);
            }
            if (Array.isArray(item.scanned_barcode_ids) && item.scanned_barcode_ids.length > quantity) {
                item.scanned_barcode_ids = item.scanned_barcode_ids.slice(0, quantity);
            }
        }
        renderCart();
    }

    function renderCart() {
        cartTableBody.innerHTML = "";
        if (cart.size === 0) {
            cartTableBody.innerHTML = '<tr class="empty-cart-row"><td colspan="5" class="empty-state">Sepet boş. Barkod okutunca ürün burada görünecek.</td></tr>';
            updateSummary();
            return;
        }

        cart.forEach((item) => {
            const lineTotal = roundAmount(Number(item.unit_price) * Number(item.quantity));
            const scannedPairs = (item.scanned_barcodes || []).map((barcodeValue, index) => {
                const barcodeId = item.scanned_barcode_ids?.[index];
                if (!barcodeId) {
                    return `
                        <div class="muted">Çıkış Barkodu: ${barcodeValue}</div>
                    `;
                }
                return `
                    <div class="muted">Çıkış Barkodu: ${barcodeValue}</div>
                    <div class="muted">Kayıt No: ${barcodeId}</div>
                `;
            });
            const scannedMarkup = scannedPairs.length
                ? `<div class="cart-barcode-stack">${scannedPairs.join("")}</div>`
                : `<div class="muted">Çıkış Barkodu: Birim barkodu okutulmadı</div>`;
            const row = document.createElement("tr");
            const quantityEditor = lineEditsLocked
                ? `<strong>${item.quantity}</strong>`
                : `
                    <div class="inline-stock-editor">
                        <button type="button" class="ghost-button" data-action="decrease">-</button>
                        <input type="number" min="1" max="${item.max_quantity || item.quantity}" value="${item.quantity}" data-action="quantity" readonly aria-label="Okutulan birim barkodu adedi">
                    </div>
                `;
            const removeButton = lineEditsLocked
                ? ""
                : '<button type="button" class="ghost-button" data-action="remove">Sil</button>';
            row.innerHTML = `
                <td>
                    <strong>${item.name}</strong>
                    <div class="muted">${item.variant || ""}</div>
                    <div class="muted">Malzeme Kodu: ${item.product_code || "-"}</div>
                    ${scannedMarkup}
                </td>
                <td>${quantityEditor}</td>
                <td>${formatCurrency(item.unit_price)}</td>
                <td>${formatCurrency(lineTotal)}</td>
                <td>${removeButton}</td>
            `;

            row.querySelector('[data-action="decrease"]')?.addEventListener("click", () => mutateQuantity(item.id, item.quantity - 1));
            row.querySelector('[data-action="remove"]')?.addEventListener("click", () => {
                cart.delete(item.id);
                renderCart();
            });

            cartTableBody.appendChild(row);
        });

        updateSummary();
    }

    function addToCart(product) {
        if (lineEditsLocked) {
            return;
        }
        if (cart.has(product.id)) {
            const existing = cart.get(product.id);
            if (product.stock_quantity) {
                existing.max_quantity = Math.max(Number(existing.max_quantity || 0), Number(product.stock_quantity || 0) + Number(existing.quantity || 0));
            }
            if (product.barcode_id && existing.scanned_barcode_ids?.includes(product.barcode_id)) {
                showPosMessage("Barkod Uyarısı", "Bu birim barkod zaten sepette bulunuyor.");
                return;
            }
            if (existing.max_quantity && existing.quantity >= existing.max_quantity) {
                showPosMessage("Stok Uyarısı", "Uygun stok miktarı yok, satış gerçekleştiremezsiniz.");
                return;
            }
            existing.quantity += 1;
            if (product.barcode) {
                existing.scanned_barcodes.push(product.barcode);
            }
            if (product.barcode_id) {
                existing.scanned_barcode_ids.push(product.barcode_id);
            }
        } else {
            cart.set(product.id, {
                id: product.id,
                product_id: product.id,
                name: product.name,
                variant: product.variant,
                quantity: 1,
                unit_price: Number(product.sale_price),
                product_code: product.product_code || "",
                max_quantity: Number(product.stock_quantity || 0),
                scanned_barcodes: product.barcode ? [product.barcode] : [],
                scanned_barcode_ids: product.barcode_id ? [product.barcode_id] : []
            });
        }
        renderCart();
    }

    function loadInitialSaleState() {
        const initialCart = window.posConfig?.initialCart || [];
        initialCart.forEach((item) => {
            cart.set(Number(item.id), {
                id: Number(item.id),
                product_id: Number(item.product_id || item.id),
                name: item.name,
                variant: item.variant,
                quantity: Number(item.quantity || 1),
                unit_price: Number(item.unit_price || 0),
                product_code: item.product_code || "",
                max_quantity: Number(item.max_quantity || item.quantity || 1),
                scanned_barcodes: item.scanned_barcodes || [],
                scanned_barcode_ids: item.scanned_barcode_ids || []
            });
        });

        if (window.posConfig?.initialCustomer) {
            fillCustomerForm(window.posConfig.initialCustomer);
        }
        if (window.posConfig?.initialPaymentMethod && paymentMethod) {
            paymentMethod.value = window.posConfig.initialPaymentMethod;
        }
        if (window.posConfig?.saleEditMode && completeButton && !lineEditsLocked) {
            completeButton.textContent = "Siparişi Güncelle";
        }
        if (window.posConfig?.saleEditMode && manualDiscountInput) {
            manualDiscountInput.value = formatInputAmount(window.posConfig.initialDiscountAmount || 0);
        }
    }

    async function lookupProduct(barcode) {
        const endpoint = window.posConfig.barcodeLookupBase.replace("__BARCODE__", encodeURIComponent(barcode));
        const response = await fetch(endpoint);
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || "Ürün bulunamadı.");
        }
        return data.product;
    }

    barcodeInput?.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") {
            return;
        }
        event.preventDefault();
        const barcode = barcodeInput.value.trim();
        if (!barcode) {
            return;
        }
        try {
            const product = await lookupProduct(barcode);
            addToCart(product);
            feedback.textContent = `${product.name} sepete eklendi.`;
            barcodeInput.value = "";
        } catch (error) {
            feedback.textContent = error.message;
            showPosMessage("Stok Uyarısı", error.message);
        }
    });

    customerProvinceSelect?.addEventListener("change", () => {
        populateDistrictOptions(customerProvinceSelect.value, "");
    });

    manualDiscountInput?.addEventListener("focus", () => {
        if (!manualDiscountInput) {
            return;
        }
        const currentValue = parseLocaleNumber(manualDiscountInput.value);
        if (currentValue === 0) {
            manualDiscountInput.value = "";
            return;
        }
        manualDiscountInput.select();
    });

    manualDiscountInput?.addEventListener("input", () => {
        if (!manualDiscountInput) {
            return;
        }
        manualDiscountInput.value = manualDiscountInput.value.replace(/[^0-9,]/g, "");
        const commaIndex = manualDiscountInput.value.indexOf(",");
        if (commaIndex !== -1) {
            const before = manualDiscountInput.value.slice(0, commaIndex + 1);
            const after = manualDiscountInput.value.slice(commaIndex + 1).replace(/,/g, "");
            manualDiscountInput.value = before + after;
        }
        updateSummary();
    });

    manualDiscountInput?.addEventListener("blur", () => {
        const summary = getSummary();
        manualDiscountInput.value = formatInputAmount(summary.discountAmount);
        updateSummary();
    });

    customerSearchInput?.addEventListener("input", () => {
        const query = customerSearchInput.value.trim();
        if (searchTimer) {
            window.clearTimeout(searchTimer);
        }
        if (query.length < 2) {
            if (customerSearchResults) {
                customerSearchResults.hidden = true;
                customerSearchResults.classList.add("is-hidden");
                customerSearchResults.innerHTML = "";
            }
            return;
        }
        searchTimer = window.setTimeout(() => searchCustomers(query), 220);
    });

    refreshRecentCustomers?.addEventListener("click", () => {
        loadRecentCustomers();
    });

    customerSearchResults?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer]");
        if (!button) {
            return;
        }
        const customer = JSON.parse(button.dataset.customer);
        fillCustomerForm(customer);
        customerSearchResults.hidden = true;
        customerSearchResults.classList.add("is-hidden");
        customerSearchResults.innerHTML = "";
    });

    recentCustomers?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer]");
        if (!button) {
            return;
        }
        const customer = JSON.parse(button.dataset.customer);
        fillCustomerForm(customer);
    });

    document.addEventListener("click", (event) => {
        if (!customerSearchResults || !customerSearchInput) {
            return;
        }
        if (customerSearchResults.contains(event.target) || customerSearchInput.contains(event.target)) {
            return;
        }
        customerSearchResults.hidden = true;
        customerSearchResults.classList.add("is-hidden");
    });

    completeButton?.addEventListener("click", async () => {
        if (cart.size === 0) {
            feedback.textContent = "Önce sepete ürün ekleyin.";
            return;
        }

        const summary = getSummary();
        const items = Array.from(cart.values()).map((item) => ({
            product_id: item.product_id,
            quantity: Number(item.quantity),
            unit_price: Number(item.unit_price),
            discount_amount: 0,
            scanned_barcodes: item.scanned_barcodes || []
        }));

        window.showBusy?.("Satış tamamlanıyor...");
        try {
            const response = await fetch(window.posConfig.updateSaleUrl || window.posConfig.completeSaleUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    payment_method: paymentMethod.value,
                    items,
                    footer_discount_amount: 0,
                    target_final_total: summary.grandTotal,
                    customer: getCustomerPayload()
                })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || "Satış tamamlanamadı.");
            }
            cart.clear();
            if (manualDiscountInput) {
                manualDiscountInput.value = "0,00";
            }
            if (discountRateInput) {
                discountRateInput.value = "%0,00";
            }
            if (customerSearchInput) {
                customerSearchInput.value = "";
            }
            resetCustomerInputs();
            renderCart();
            feedback.textContent = data.message;
            loadRecentCustomers();
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            }
        } catch (error) {
            feedback.textContent = error.message;
            showPosMessage("Satış Uyarısı", error.message);
        } finally {
            window.hideBusy?.();
        }
    });

    populateProvinceOptions();
    loadInitialSaleState();
    barcodeInput?.focus();
    if (customerSearchResults) {
        customerSearchResults.hidden = true;
        customerSearchResults.classList.add("is-hidden");
        customerSearchResults.innerHTML = "";
    }
    renderCart();
    loadRecentCustomers();
})();
