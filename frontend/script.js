/* =========================================================
   NOVASTORE — JAVASCRIPT
   ========================================================= */

const A = "/api";

let cart = JSON.parse(localStorage.getItem("cart") || "[]");

const $ = id => document.getElementById(id);

const money = n =>
    new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN"
    }).format(n);


/* =========================================================
   API
   ========================================================= */

async function api(url, options = {}) {

    const response = await fetch(A + url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    let data;

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new Error(data.error || "Ocurrió un error");
    }

    return data;
}


/* =========================================================
   UTILIDADES
   ========================================================= */

function save() {

    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );

    updateCartCount();
}


function updateCartCount() {

    const count = cart.reduce(
        (total, item) => total + item.quantity,
        0
    );

    if ($("count")) {
        $("count").textContent = count;
    }
}


function toast(message) {

    const element = $("toast");

    if (!element) return;

    element.textContent = message;

    element.classList.add("show");

    clearTimeout(window.toastTimer);

    window.toastTimer = setTimeout(() => {
        element.classList.remove("show");
    }, 2500);
}


/* =========================================================
   NAVEGACIÓN
   ========================================================= */

function show(id) {

    $("catalog").classList.add("hidden");
    $("orders").classList.add("hidden");

    const section = $(id);

    if (section) {
        section.classList.remove("hidden");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    if (id === "orders") {
        orders();
    }
}


function scrollToProducts() {

    $("catalog").classList.remove("hidden");
    $("orders").classList.add("hidden");

    setTimeout(() => {

        $("products-section").scrollIntoView({
            behavior: "smooth"
        });

    }, 50);
}


function scrollToCategories() {

    $("catalog").classList.remove("hidden");
    $("orders").classList.add("hidden");

    setTimeout(() => {

        $("categories-section").scrollIntoView({
            behavior: "smooth"
        });

    }, 50);
}


/* =========================================================
   CATEGORÍAS
   ========================================================= */

const categoryIcons = {
    "Tecnología": "",
    "Accesorios": "",
    "Ropa": "",
    "Hogar": "",
    "Gaming": "",
    "Belleza": ""
};


async function loadCats() {

    try {

        const data = await api("/categories");

        const categories = data.categories || [];

        $("cat").innerHTML =
            `<option value="">Todas las categorías</option>` +
            categories
                .map(category =>
                    `<option value="${escapeHTML(category)}">
                        ${escapeHTML(category)}
                    </option>`
                )
                .join("");

        renderCategoryCards(categories);

    } catch (error) {

        console.error(error);

    }
}


function renderCategoryCards(categories) {

    const container = $("categoryCards");

    if (!container) return;

    container.innerHTML = categories
        .map(category => {

            const icon =
                categoryIcons[category] || "";

            return `
                <article
                    class="category-card"
                    onclick="filterCategory('${escapeAttribute(category)}')"
                >

                    <div class="category-icon">
                        ${icon}
                    </div>

                    <strong>
                        ${escapeHTML(category)}
                    </strong>

                    <span>
                        Explorar productos
                    </span>

                </article>
            `;
        })
        .join("");
}


function filterCategory(category) {

    $("cat").value = category;

    scrollToProducts();

    load();
}


/* =========================================================
   PRODUCTOS
   ========================================================= */

async function load() {

    try {

        const search =
            $("search")?.value || "";

        const category =
            $("cat")?.value || "";

        const data = await api(
            "/products?search=" +
            encodeURIComponent(search) +
            "&category=" +
            encodeURIComponent(category)
        );

        renderProducts(data.products || []);

    } catch (error) {

        console.error(error);

        $("products").innerHTML = `
            <div class="empty-state">
                <div>⚠️</div>
                <h3>No se pudo cargar el catálogo</h3>
                <p>Comprueba que el servidor esté funcionando.</p>
            </div>
        `;
    }
}


function renderProducts(products) {

    const container = $("products");

    const empty = $("emptyProducts");

    if (!products.length) {

        container.innerHTML = "";

        if (empty) {
            empty.classList.remove("hidden");
        }

        return;
    }

    if (empty) {
        empty.classList.add("hidden");
    }

    container.innerHTML = products
        .map(product => {

            const stock = Number(product.stock);

            let stockText = `${stock} disponibles`;

            let stockClass = "";

            if (stock <= 5 && stock > 0) {
                stockText = `Solo ${stock} disponibles`;
                stockClass = "stock-low";
            }

            if (stock <= 0) {
                stockText = "Agotado";
            }

            return `
                <article class="product-card">

                    <div class="product-image-wrapper">

                        <img
                            class="product-image"
                            src="${safeImage(product.image)}"
                            alt="${escapeAttribute(product.name)}"
                            loading="lazy"
                            onerror="this.src='/images/placeholder.jpg'"
                        >

                        <span class="product-category">
                            ${escapeHTML(product.category)}
                        </span>

                    </div>

                    <div class="product-info">

                        <h3>
                            ${escapeHTML(product.name)}
                        </h3>

                        <p class="product-description">
                            ${escapeHTML(product.description || "Producto NovaStore")}
                        </p>

                        <div class="product-bottom">

                            <span class="product-price">
                                ${money(product.price)}
                            </span>

                            <span class="stock ${stockClass}">
                                ${stockText}
                            </span>

                        </div>

                        <button
                            class="product-add"
                            onclick="add(${product.id})"
                            ${stock <= 0 ? "disabled" : ""}
                        >
                            ${stock <= 0
                                ? "Agotado"
                                : "Agregar al carrito"
                            }
                        </button>

                    </div>

                </article>
            `;
        })
        .join("");
}


/* =========================================================
   CARRITO
   ========================================================= */

async function add(id) {

    try {

        const data = await api("/products");

        const product =
            data.products.find(
                item => item.id === id
            );

        if (!product) {
            toast("Producto no encontrado");
            return;
        }

        const existing =
            cart.find(
                item => item.product_id === id
            );

        const currentQuantity =
            existing ? existing.quantity : 0;

        if (currentQuantity >= product.stock) {

            toast("No hay más unidades disponibles");

            return;
        }

        if (existing) {
            existing.quantity++;
        } else {

            cart.push({
                product_id: id,
                quantity: 1
            });
        }

        save();

        toast(
            `${product.name} agregado al carrito`
        );

    } catch (error) {

        toast(error.message);

    }
}


async function cartView() {

    try {

        const data = await api("/products");

        let total = 0;

        let html = "";

        for (const item of cart) {

            const product =
                data.products.find(
                    p => p.id === item.product_id
                );

            if (!product) continue;

            const subtotal =
                product.price * item.quantity;

            total += subtotal;

            html += `
                <div class="cart-item">

                    <img
                        class="cart-item-image"
                        src="${safeImage(product.image)}"
                        alt="${escapeAttribute(product.name)}"
                    >

                    <div>

                        <div class="cart-item-name">
                            ${escapeHTML(product.name)}
                        </div>

                        <div class="cart-item-price">
                            ${money(product.price)} c/u
                        </div>

                        <div class="quantity-controls">

                            <button
                                onclick="changeQuantity(${product.id}, -1)"
                            >
                                −
                            </button>

                            <strong>
                                ${item.quantity}
                            </strong>

                            <button
                                onclick="changeQuantity(${product.id}, 1)"
                            >
                                +
                            </button>

                            <button
                                class="remove-cart"
                                onclick="removeFromCart(${product.id})"
                            >
                                Eliminar
                            </button>

                        </div>

                    </div>

                    <strong>
                        ${money(subtotal)}
                    </strong>

                </div>
            `;
        }

        if (!html) {

            html = `
                <div class="empty-state">

                    <div>🛒</div>

                    <h3>
                        Tu carrito está vacío
                    </h3>

                    <p>
                        Agrega algunos productos para comenzar.
                    </p>

                </div>
            `;
        }

        modal(`
            <h2>Tu carrito</h2>

            ${html}

            ${
                cart.length
                ? `
                    <div class="cart-summary">

                        <span>Total</span>

                        <span class="cart-total">
                            ${money(total)}
                        </span>

                    </div>

                    <button
                        class="modal-primary"
                        onclick="checkout()"
                    >
                        Finalizar compra
                    </button>
                `
                : ""
            }
        `);

    } catch (error) {

        toast(error.message);

    }
}


async function changeQuantity(id, amount) {

    const item =
        cart.find(
            product => product.product_id === id
        );

    if (!item) return;

    try {

        const data = await api("/products");

        const product =
            data.products.find(
                p => p.id === id
            );

        if (!product) return;

        const newQuantity =
            item.quantity + amount;

        if (newQuantity <= 0) {

            removeFromCart(id);

            return;
        }

        if (newQuantity > product.stock) {

            toast("No hay suficiente stock");

            return;
        }

        item.quantity = newQuantity;

        save();

        cartView();

    } catch (error) {

        toast(error.message);

    }
}


function removeFromCart(id) {

    cart =
        cart.filter(
            item => item.product_id !== id
        );

    save();

    cartView();

    toast("Producto eliminado");
}


/* =========================================================
   CHECKOUT
   ========================================================= */

async function checkout() {

    if (!cart.length) {

        toast("Tu carrito está vacío");

        return;
    }

    try {

        const data = await api(
            "/orders",
            {
                method: "POST",
                body: JSON.stringify({
                    items: cart
                })
            }
        );

        cart = [];

        save();

        closeM();

        toast(
            `Pedido #${data.order_id} creado correctamente`
        );

        setTimeout(() => {
            show("orders");
        }, 800);

    } catch (error) {

        toast(error.message);

    }
}


/* =========================================================
   PEDIDOS
   ========================================================= */

async function orders() {

    try {

        const data =
            await api("/orders");

        if (!data.orders.length) {

            $("ordersList").innerHTML = `
                <div class="empty-state">

                    <div>📦</div>

                    <h3>
                        Todavía no tienes pedidos
                    </h3>

                    <p>
                        Cuando realices una compra aparecerá aquí.
                    </p>

                </div>
            `;

            return;
        }

        $("ordersList").innerHTML =
            data.orders
                .map(order => {

                    const status =
                        translateStatus(order.status);

                    return `
                        <article class="order">

                            <div class="order-header">

                                <div>

                                    <strong>
                                        Pedido #${order.id}
                                    </strong>

                                    <div
                                        style="
                                            color:#667085;
                                            font-size:12px;
                                            margin-top:5px;
                                        "
                                    >
                                        ${formatDate(order.created_at)}
                                    </div>

                                </div>

                                <span class="order-status">
                                    ${status}
                                </span>

                            </div>

                            <div class="order-items">

                                ${order.items
                                    .map(item => `
                                        <div>
                                            ${item.quantity}
                                            ×
                                            ${escapeHTML(item.name)}
                                        </div>
                                    `)
                                    .join("")
                                }

                            </div>

                            <div
                                style="
                                    margin-top:15px;
                                    display:flex;
                                    justify-content:space-between;
                                "
                            >

                                <span>
                                    Total
                                </span>

                                <strong class="order-total">
                                    ${money(order.total)}
                                </strong>

                            </div>

                        </article>
                    `;
                })
                .join("");

    } catch (error) {

        $("ordersList").innerHTML = `
            <div class="empty-state">

                <div>🔐</div>

                <h3>
                    Inicia sesión
                </h3>

                <p>
                    Necesitas una cuenta para consultar tus pedidos.
                </p>

                <button
                    class="modal-primary"
                    onclick="auth()"
                    style="max-width:250px"
                >
                    Iniciar sesión
                </button>

            </div>
        `;
    }
}


/* =========================================================
   AUTENTICACIÓN
   ========================================================= */

function auth() {

    modal(`
        <h2>Mi cuenta</h2>

        <p
            style="
                color:#667085;
                font-size:13px;
                margin-top:-8px;
            "
        >
            Inicia sesión o crea una cuenta en NovaStore.
        </p>

        <div class="form-group">

            <label>
                Nombre
            </label>

            <input
                id="authName"
                placeholder="Tu nombre"
            >

        </div>

        <div class="form-group">

            <label>
                Correo electrónico
            </label>

            <input
                id="authEmail"
                type="email"
                placeholder="correo@ejemplo.com"
            >

        </div>

        <div class="form-group">

            <label>
                Contraseña
            </label>

            <input
                id="authPassword"
                type="password"
                placeholder="Mínimo 8 caracteres"
            >

        </div>

        <button
            class="modal-primary"
            onclick="reg()"
        >
            Crear cuenta
        </button>

        <button
            class="modal-secondary"
            onclick="log()"
        >
            Iniciar sesión
        </button>

    `);
}


async function reg() {

    const name =
        $("authName").value.trim();

    const email =
        $("authEmail").value.trim();

    const password =
        $("authPassword").value;

    try {

        const data =
            await api(
                "/auth/register",
                {
                    method: "POST",

                    body: JSON.stringify({
                        name,
                        email,
                        password
                    })
                }
            );

        closeM();

        toast(
            `Bienvenido/a ${data.user.name}`
        );

    } catch (error) {

        toast(error.message);

    }
}


async function log() {

    const email =
        $("authEmail").value.trim();

    const password =
        $("authPassword").value;

    try {

        const data =
            await api(
                "/auth/login",
                {
                    method: "POST",

                    body: JSON.stringify({
                        email,
                        password
                    })
                }
            );

        closeM();

        toast(
            `Bienvenido/a ${data.user.name}`
        );

    } catch (error) {

        toast(error.message);

    }
}


/* =========================================================
   MODALES
   ========================================================= */

function modal(content) {

    $("content").innerHTML = content;

    $("modal").classList.remove("hidden");
}


function closeM() {

    $("modal").classList.add("hidden");
}


function modalBackground(event) {

    if (event.target === $("modal")) {
        closeM();
    }
}


/* =========================================================
   UTILIDADES DE SEGURIDAD
   ========================================================= */

function escapeHTML(value) {

    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function escapeAttribute(value) {

    return escapeHTML(value)
        .replaceAll("`", "&#096;");
}


function safeImage(image) {

    if (!image) {
        return "/images/placeholder.jpg";
    }

    if (
        image.startsWith("/images/") ||
        image.startsWith("https://") ||
        image.startsWith("http://")
    ) {
        return image;
    }

    return "/images/placeholder.jpg";
}


function translateStatus(status) {

    const statuses = {
        pending: "Pendiente",
        paid: "Pagado",
        shipped: "Enviado",
        delivered: "Entregado",
        cancelled: "Cancelado"
    };

    return statuses[status] || status;
}


function formatDate(date) {

    if (!date) return "";

    try {

        return new Date(date).toLocaleDateString(
            "es-MX",
            {
                day: "2-digit",
                month: "long",
                year: "numeric"
            }
        );

    } catch {

        return date;
    }
}


/* =========================================================
   INICIALIZACIÓN
   ========================================================= */

save();

loadCats();

load();
