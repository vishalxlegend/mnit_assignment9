// Live Server serves HTML on 5500; Python still runs the API on 5000.
const usingLiveServer = ["127.0.0.1", "localhost"].includes(window.location.hostname)
    && window.location.port === "5500";
const apiOrigin = usingLiveServer ? "http://127.0.0.1:5000" : window.location.origin;

const currency = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
});

async function fetchProductData(url) {
    const response = await fetch(new URL(url, apiOrigin));
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
        throw new Error("The product API did not return JSON. Start the Python server and open http://127.0.0.1:5000/products/index.html.");
    }
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Unable to load products.");
    }
    return data;
}

function fillProduct(element, product) {
    // textContent displays database text safely without interpreting it as HTML.
    element.querySelector(".product-name").textContent = product.name;
    element.querySelector(".product-description").textContent = product.description;
    element.querySelector(".price").textContent = currency.format(product.price_paise / 100);
    element.querySelector(".stock").textContent = product.stock > 0
        ? `${product.stock} available`
        : "Out of stock";
    element.querySelector(".product-image").src = product.image_url;
}

async function loadCatalog() {
    const search = new URLSearchParams(window.location.search).get("q") || "";
    document.querySelector("#search").value = search;
    const products = await fetchProductData(`/api/products?q=${encodeURIComponent(search)}`);
    const container = document.querySelector("#products");
    const template = document.querySelector("#product-card");

    for (const product of products) {
        const card = template.content.cloneNode(true);
        fillProduct(card, product);
        const link = card.querySelector(".details-link");
        link.href = `/products/details.html?id=${encodeURIComponent(product.id)}`;
        link.setAttribute("aria-label", `View details for ${product.name}`);
        container.append(card);
    }

    document.querySelector("#status").textContent = products.length
        ? `${products.length} vehicle${products.length === 1 ? "" : "s"} found.`
        : "No vehicles match your search.";
}

async function loadDetails() {
    const id = new URLSearchParams(window.location.search).get("id");
    if (!id || !/^[0-9]+$/.test(id) || !/[1-9]/.test(id)) {
        throw new Error("A positive product ID is required. Return to the catalog and select a vehicle.");
    }

    const product = await fetchProductData(`/api/products/${encodeURIComponent(id)}`);
    const detail = document.querySelector("#product-detail").content.cloneNode(true);
    fillProduct(detail, product);
    detail.querySelector(".product-id").textContent = product.id;
    document.querySelector("#product").append(detail);
    document.querySelector("#status").textContent = "";
    document.title = `${product.name} | Legendry Vehicles`;
}

async function loadPage() {
    try {
        if (document.body.dataset.page === "catalog") {
            await loadCatalog();
        } else if (document.body.dataset.page === "details") {
            await loadDetails();
        }
    } catch (error) {
        const status = document.querySelector("#status");
        status.textContent = error instanceof TypeError
            ? `Unable to connect to the product API at ${apiOrigin}. Start the Python server and reload.`
            : error.message;
        status.classList.add("error");
    }
}

loadPage();
