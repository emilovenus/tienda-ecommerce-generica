# Tienda E-commerce Genérica
Proyecto académico de comercio electrónico con arquitectura frontend/backend.

## Ejecución
Requisitos: Docker y Docker Compose.
```bash
cp .env.example .env
# cambia SECRET_KEY en .env
docker compose up -d --build
```
Abrir: http://localhost:8080
API: http://localhost:8080/api/health

## Funciones
Registro/login, sesiones por cookie, catálogo, búsqueda, categorías, inventario, carrito persistente, checkout, historial y estados de pedido. El endpoint de creación de productos requiere usuario con rol admin.

## Producción
Usar HTTPS, SECRET_KEY aleatoria, SESSION_COOKIE_SECURE=1, PostgreSQL para mayor escala, Cloudflare Tunnel delante de Nginx, backups, rate limiting, CSRF y un proveedor de pagos. No guardar tarjetas.
