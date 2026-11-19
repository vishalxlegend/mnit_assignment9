# Screenshot evidence

These are actual application and Grafana browser captures, not mockups. Authentication and shopping screenshots were captured with a disposable database and fictitious demo account, without changing existing users' carts. Grafana captures show the recorded live monitoring demonstration. All images are included in this folder and do not depend on ignored runtime files.

## 1. Authentication required

Opening the cart while logged out redirects to login, retaining the intended destination.

![Login after protected-cart redirect](screenshots/01-login-redirect.png)

## 2. Registration

Registration collects name, username and password. Password hashing occurs on the backend; the password is not shown in this screenshot.

![Registration form](screenshots/02-registration.png)

## 3. Catalog quantity controls

Products already in the cart appear first. Quantities can be changed directly in the catalog.

![Catalog with cart quantities](screenshots/03-catalog-quantities.png)

## 4. Persistent shopping cart

The demo cart contains two City Hatchback Toys and three Budget Hatchback Toys, totaling ₹2,740. Quantity and removal controls save through the backend; the total updates automatically after a successful change.

![Shopping cart and calculated total](screenshots/04-shopping-cart.png)

## 5. Grafana after traffic

Real Prometheus samples show HTTP volume, latency, error rates and cart operations after interacting with the application and running the traffic demo.

![Grafana dashboard after traffic](screenshots/05-grafana-dashboard.png)

## 6. Grafana before traffic

This capture uses the retained historical window before the same demonstration. Compare its request and cart-operation activity with the preceding dashboard capture.

![Grafana before demonstration traffic](screenshots/06-grafana-before-traffic.png)

## 7. Failure monitoring

The failure panels show failed authentication and controlled application/database exceptions. Controlled failures generate telemetry without damaging application data.

![Grafana failure monitoring panels](screenshots/07-grafana-failures.png)

For a new demonstration, follow [VERIFICATION](VERIFICATION.md). For new screenshots, use the browser's screenshot facility after repeating these flows; avoid capturing filled passwords or the local credentials file.
