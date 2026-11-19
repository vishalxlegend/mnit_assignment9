const currency = new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 2,
});
let csrfToken;

function showStatus(message, isError = false) {
    const status = document.querySelector("#status");
    status.textContent = message;
    status.classList.toggle("error", isError);
}

async function api(url, options = {}) {
    const headers = { ...options.headers };
    if (options.body) headers["Content-Type"] = "application/json";
    if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken;
    const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
    if (response.status === 401) {
        window.location.replace(`/login?next=${encodeURIComponent(location.pathname + location.search)}`);
        throw new Error("Please log in to continue.");
    }
    if (!(response.headers.get("content-type") || "").includes("application/json")) {
        throw new Error("Open this app through the Python server at http://127.0.0.1:5000.");
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to complete the request.");
    return data;
}

function fillProduct(element, product) {
    element.querySelector(".product-name").textContent = product.name;
    element.querySelector(".product-description").textContent = product.description;
    element.querySelector(".price").textContent = currency.format(product.price_paise / 100);
    element.querySelector(".stock").textContent = product.stock > 0 ? `${product.stock} available` : "Out of stock";
    element.querySelector(".product-image").src = product.image_url;
    attachCartControls(element.querySelector(".cart-controls"), product);
}

async function loadCatalog() {
    const search = new URLSearchParams(location.search).get("q") || "";
    document.querySelector("#search").value = search;
    const products = await api(`/api/products?q=${encodeURIComponent(search)}`);
    const container = document.querySelector("#products");
    for (const product of products) {
        const card = document.querySelector("#product-card").content.cloneNode(true);
        card.querySelector(".card").dataset.productId = product.id;
        fillProduct(card, product);
        const link = card.querySelector(".details-link");
        link.href = `/products/details.html?id=${encodeURIComponent(product.id)}`;
        link.setAttribute("aria-label", `View details for ${product.name}`);
        container.append(card);
    }
    syncCartViews();
    showStatus(products.length ? `${products.length} toy vehicle${products.length === 1 ? "" : "s"} found.` : "No toy vehicles match your search.");
}

async function loadDetails() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id || !/^[0-9]+$/.test(id) || !/[1-9]/.test(id)) {
        throw new Error("A positive product ID is required. Return to the catalog and select a toy vehicle.");
    }
    const product = await api(`/api/products/${encodeURIComponent(id)}`);
    const detail = document.querySelector("#product-detail").content.cloneNode(true);
    fillProduct(detail, product);
    detail.querySelector(".product-id").textContent = product.id;
    document.querySelector("#product").append(detail);
    showStatus("");
    document.title = `${product.name} | Legendry Toy Cars`;
}

let cartState = { items: [], total_paise: 0 };
const cartControls = new Map();
let mutationQueue = Promise.resolve();

function cartItem(id) {
    return cartState.items.find(item => item.product_id === id);
}

// Serialize writes so a slow response cannot replace a newer total or quantity.
function mutateCart(url, options) {
    const task = mutationQueue.then(async () => {
        cartState = await api(url, options);
        syncCartViews();
    });
    mutationQueue = task.catch(() => {});
    return task;
}

function attachCartControls(container, product) {
    const id = product.id;
    container.innerHTML = `
        <button class="add-to-cart" type="button">Add to cart</button>
        <div class="in-cart-controls" hidden>
            <span class="in-cart-label">In your cart</span>
            <div class="quantity-controls">
                <button class="decrease" type="button">−</button>
                <input class="quantity-input" type="number" min="0" step="1" required>
                <button class="increase" type="button">+</button>
            </div>
            <button class="remove-item" type="button">Remove</button>
        </div>`;
    const add = container.querySelector('.add-to-cart');
    const group = container.querySelector('.in-cart-controls');
    const input = container.querySelector('input');
    const minus = container.querySelector('.decrease');
    const plus = container.querySelector('.increase');
    const remove = container.querySelector('.remove-item');
    input.setAttribute('aria-label', `Quantity for ${product.name}`);
    minus.setAttribute('aria-label', `Decrease quantity for ${product.name}`);
    plus.setAttribute('aria-label', `Increase quantity for ${product.name}`);
    let busy = false;
    let timer;
    function refresh() {
        const item = cartItem(id);
        const quantity = item?.quantity || 0;
        const limit = Math.min(99, item?.stock ?? product.stock);
        add.hidden = quantity > 0;
        group.hidden = quantity === 0;
        add.textContent = limit === 0 ? 'Out of stock' : 'Add to cart';
        add.disabled = busy || limit === 0;
        minus.disabled = busy;
        plus.disabled = busy || quantity >= limit;
        remove.disabled = busy;
        input.disabled = busy;
        input.max = limit;
        if (!busy && !timer) input.value = quantity;
        container.setAttribute('aria-busy', String(busy));
    }
    async function save(quantity, adding = false) {
        clearTimeout(timer);
        timer = undefined;
        if (busy) return;
        if (!Number.isInteger(quantity) || quantity < 0 || quantity > Math.min(99, product.stock)) {
            showStatus(`Choose a whole quantity from 0 to ${Math.min(99, product.stock)}.`, true);
            refresh();
            return;
        }
        if (!adding && quantity === (cartItem(id)?.quantity || 0)) return;
        busy = true;
        refresh();
        showStatus('Saving your cart…');
        try {
            await mutateCart(adding ? '/api/cart/items' : `/api/cart/items/${id}`, {
                method: adding ? 'POST' : quantity === 0 ? 'DELETE' : 'PATCH',
                ...(quantity === 0 ? {} : { body: JSON.stringify(adding ? { product_id: id, quantity: 1 } : { quantity }) }),
            });
            showStatus(quantity === 0 ? `${product.name} removed from your cart.` : `${product.name}: ${quantity} in your cart.`);
        } catch (error) {
            showStatus(error.message, true);
        } finally {
            busy = false;
            refresh();
        }
    }
    add.addEventListener('click', () => save(1, true));
    minus.addEventListener('click', () => save((cartItem(id)?.quantity || 0) - 1));
    plus.addEventListener('click', () => save((cartItem(id)?.quantity || 0) + 1));
    remove.addEventListener('click', () => save(0));
    input.addEventListener('input', () => {
        clearTimeout(timer);
        // Wait briefly for typing to finish; no Update button or blur is needed.
        timer = setTimeout(() => {
            timer = undefined;
            if (input.value === '') return;
            save(Number(input.value));
        }, 250);
    });
    input.addEventListener('change', () => {
        if (input.value === '') { clearTimeout(timer); timer = undefined; refresh(); }
        else save(Number(input.value));
    });
    cartControls.set(id, { refresh, dispose: () => clearTimeout(timer) });
    refresh();
}

function syncCartViews() {
    for (const controls of cartControls.values()) controls.refresh();
    const total = document.querySelector('#catalog-cart-total');
    if (total) {
        const count = cartState.items.reduce((sum, item) => sum + item.quantity, 0);
        total.textContent = `My cart: ${count} item${count === 1 ? '' : 's'} · ${currency.format(cartState.total_paise / 100)}`;
        const container = document.querySelector('#products');
        const cards = [...container.children];
        const sorted = [...cards].sort((a, b) =>
            Number(!!cartItem(Number(b.dataset.productId))) - Number(!!cartItem(Number(a.dataset.productId)))
            || Number(a.dataset.productId) - Number(b.dataset.productId));
        if (cards.some((card, i) => card !== sorted[i])) {
            const focused = document.activeElement;
            sorted.forEach(card => container.append(card));
            if (focused?.isConnected) focused.focus({ preventScroll: true });
        }
        for (const card of cards) card.classList.toggle('in-cart', !!cartItem(Number(card.dataset.productId)));
    }
    if (document.body.dataset.page === 'cart') renderCart();
}

function renderCart() {
    const container = document.querySelector('#cart-items');
    for (const row of [...container.children]) {
        const id = Number(row.dataset.productId);
        if (!cartItem(id)) {
            cartControls.get(id)?.dispose();
            cartControls.delete(id);
            row.remove();
        }
    }
    for (const item of cartState.items) {
        let row = container.querySelector(`[data-product-id="${item.product_id}"]`);
        if (!row) {
            row = document.querySelector('#cart-item').content.firstElementChild.cloneNode(true);
            row.dataset.productId = item.product_id;
            row.querySelector('.product-name').textContent = item.name;
            row.querySelector('.product-image').src = item.image_url;
            attachCartControls(row.querySelector('.cart-controls'), { ...item, id: item.product_id });
            container.append(row);
        }
        row.querySelector('.unit-price').textContent = `${currency.format(item.price_paise / 100)} each`;
        row.querySelector('.subtotal').textContent = `Subtotal: ${currency.format(item.subtotal_paise / 100)}`;
    }
    document.querySelector('#cart-total').textContent = `Total: ${currency.format(cartState.total_paise / 100)}`;
    if (!cartState.items.length) showStatus('Your cart is empty. Browse the catalog to add toys.');
}

async function loadPage() {
    // Flask must serve the app so its backend can protect every page.
    if (["localhost", "127.0.0.1"].includes(location.hostname) && location.port === "5500") {
        location.replace(`http://127.0.0.1:5000${location.pathname}${location.search}`);
        return;
    }
    try {
        const session = await api("/api/session");
        csrfToken = session.csrf_token;
        document.querySelector("#account-name").textContent = `Hi, ${session.user.name}`;
        document.querySelector("#logout").addEventListener("click", async () => {
            try {
                await api("/api/logout", { method: "POST" });
                location.replace("/login");
            } catch (error) { showStatus(error.message, true); }
        });
        cartState = await api("/api/cart");
        if (document.body.dataset.page === "catalog") await loadCatalog();
        else if (document.body.dataset.page === "details") await loadDetails();
        else if (document.body.dataset.page === "cart") {
            showStatus("Quantities save automatically. Set a quantity to 0 to remove an item.");
            renderCart();
        }
    } catch (error) {
        showStatus(error instanceof TypeError ? "Unable to connect. Check that the Python server is running." : error.message, true);
    }
}

// Recheck authentication when a browser restores a page from its back/forward cache.
window.addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
loadPage();
