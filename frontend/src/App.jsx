// frontend/src/App.jsx
import React, { useState, useEffect, useRef } from "react";

export default function App() {
  // --- 1. STATE MANAGEMENT ---
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(false);
  const [orderResponse, setOrderResponse] = useState(null);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState("");
  const [coldStartNotice, setColdStartNotice] = useState(false);
  const [toast, setToast] = useState(null); // { type: 'success'|'error'|'info', message }
  const toastTimerRef = useRef(null);
  const coldStartTimerRef = useRef(null);

  // Authentication State
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [currentUserEmail, setCurrentUserEmail] = useState(
    localStorage.getItem("email") || "",
  );
  const [isRegistering, setIsRegistering] = useState(false); // Toggle Login vs Register UI
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");

  // State for querying old orders
  const [queryOrderId, setQueryOrderId] = useState("");
  const [queriedOrder, setQueriedOrder] = useState(null);
  const [queryError, setQueryError] = useState("");

  // Auth-scoped order history ("My Orders")
  const [myOrders, setMyOrders] = useState([]);
  const [myOrdersLoading, setMyOrdersLoading] = useState(false);
  const [myOrdersError, setMyOrdersError] = useState("");

  const PRODUCT_API =
    import.meta.env.VITE_PRODUCT_API_URL ||
    "https://product-service-y2y8.onrender.com/products";
  const ORDER_API =
    import.meta.env.VITE_ORDER_API_URL ||
    "https://order-service-3i4u.onrender.com/orders";

  const showToast = (message, type = "info") => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ message, type });
    toastTimerRef.current = setTimeout(() => setToast(null), 4200);
  };

  // --- 2. FETCH PRODUCT CATALOG + MY ORDERS ON LOAD ---
  useEffect(() => {
    if (token) {
      fetchProducts();
      fetchMyOrders();
    }
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      if (coldStartTimerRef.current) clearTimeout(coldStartTimerRef.current);
    };
  }, [token]);

  const fetchProducts = async () => {
    setProductsLoading(true);
    setProductsError("");
    setColdStartNotice(false);
    if (coldStartTimerRef.current) clearTimeout(coldStartTimerRef.current);
    // Free-tier Render services sleep; be honest after a short wait
    coldStartTimerRef.current = setTimeout(() => {
      setColdStartNotice(true);
    }, 2500);

    try {
      const res = await fetch(PRODUCT_API);
      if (res.ok) {
        const data = await res.json();
        setProducts(data);
        setProductsError("");
      } else {
        setProductsError(
          `Catalog unavailable (${res.status}). Try again shortly.`,
        );
        showToast("Could not load products from the Product Service.", "error");
      }
    } catch (err) {
      console.error("Failed to fetch products:", err);
      setProductsError(
        "Network error loading products. The free-tier service may still be waking up.",
      );
      showToast("Network error loading the product catalog.", "error");
    } finally {
      if (coldStartTimerRef.current) clearTimeout(coldStartTimerRef.current);
      setColdStartNotice(false);
      setProductsLoading(false);
    }
  };

  const fetchMyOrders = async () => {
    setMyOrdersLoading(true);
    setMyOrdersError("");
    try {
      const res = await fetch(`${ORDER_API}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMyOrders(data);
      } else {
        const raw = await res.text();
        let detail = raw;
        try {
          detail = JSON.parse(raw).detail || raw;
        } catch {
          /* body was not JSON */
        }
        setMyOrdersError(detail || "Failed to load your orders.");
        if (res.status === 401) handleLogout();
      }
    } catch (err) {
      setMyOrdersError(
        "Failed to load your orders. Verify the Order Service is running.",
      );
    } finally {
      setMyOrdersLoading(false);
    }
  };

  // --- 3. AUTHENTICATION OPERATIONS ---
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthSuccess("");
    setLoading(true);

    const endpoint = isRegistering ? "auth/register" : "auth/login";
    const payload = { email: authEmail, password: authPassword };

    try {
      const res = await fetch(`${ORDER_API}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (res.ok) {
        if (isRegistering) {
          setAuthSuccess("Registration successful! You can now log in.");
          setIsRegistering(false);
          setAuthPassword("");
        } else {
          // Login Success: Save JWT token and email to browser storage
          localStorage.setItem("token", data.access_token);
          localStorage.setItem("email", authEmail);
          setToken(data.access_token);
          setCurrentUserEmail(authEmail);

          // Clear inputs
          setAuthEmail("");
          setAuthPassword("");
        }
      } else {
        setAuthError(
          data.detail || "Authentication failed. Check your inputs.",
        );
      }
    } catch (err) {
      setAuthError(
        "Network error. Verify your Order Service is running on Render.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("email");
    setToken("");
    setCurrentUserEmail("");
    setCart([]);
    setProducts([]);
    setQueriedOrder(null);
    setMyOrders([]);
    setMyOrdersError("");
    setProductsError("");
    setColdStartNotice(false);
    setProductsLoading(false);
  };

  // --- 4. INTERACTIVE CART OPERATIONS ---
  const addToCart = (product) => {
    setCart((prevCart) => {
      const existing = prevCart.find((item) => item.id === product.id);
      if (existing) {
        if (existing.quantity >= product.stock) {
          showToast(
            `Cannot add more. Only ${product.stock} items left in stock.`,
            "error",
          );
          return prevCart;
        }
        return prevCart.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item,
        );
      }
      showToast(`${product.name} added to cart`, "success");
      return [...prevCart, { ...product, quantity: 1 }];
    });
  };

  const removeFromCart = (productId) => {
    setCart((prevCart) => prevCart.filter((item) => item.id !== productId));
  };

  const calculateTotal = () => {
    return cart
      .reduce((total, item) => total + item.price * item.quantity, 0)
      .toFixed(2);
  };

  // --- 5. SECURE CHECKOUT (WITH BEARER TOKEN) ---
  const handleCheckout = async (e) => {
    e.preventDefault();
    setLoading(true);

    const payload = {
      customer_email: currentUserEmail, // Handled automatically by token, but kept for schema alignment
      items: cart.map((item) => ({
        product_id: item.id,
        quantity: item.quantity,
      })),
    };

    try {
      const res = await fetch(`${ORDER_API}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`, // Injecting our secure JWT Bearer token
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setOrderResponse(data);
        setCart([]);
        fetchMyOrders();
        showToast(
          `Order #${data.order?.id ?? ""} created — complete payment in the new tab.`,
          "success",
        );
        window.open(data.payment_url, "_blank");
      } else {
        // Server errors return plain text rather than JSON, so read the body defensively
        const raw = await res.text();
        let detail = raw;
        try {
          detail = JSON.parse(raw).detail || raw;
        } catch {
          /* body was not JSON */
        }
        showToast(
          `Checkout failed (${res.status}): ${detail || "Unknown error"}`,
          "error",
        );
        if (res.status === 401) handleLogout();
      }
    } catch (err) {
      showToast(
        "Network error during checkout. Verify your services are running.",
        "error",
      );
    } finally {
      setLoading(false);
    }
  };

  // --- 6. LIVE ORDER TRACKER ---
  const handleQueryOrder = async (e) => {
    e.preventDefault();
    setQueryError("");
    setQueriedOrder(null);
    if (!queryOrderId) return;

    try {
      const res = await fetch(`${ORDER_API}/${queryOrderId}`);
      if (res.ok) {
        const data = await res.json();
        setQueriedOrder(data);
      } else {
        setQueryError(`Order ID ${queryOrderId} not found.`);
      }
    } catch (err) {
      setQueryError("Failed to fetch order. Verify your services are running.");
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      PENDING: "bg-amber-100 text-amber-800 border-amber-200",
      PAID: "bg-emerald-100 text-emerald-800 border-emerald-200",
      FAILED: "bg-rose-100 text-rose-800 border-rose-200",
    };
    return (
      <span
        className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${styles[status] || "bg-gray-100"}`}
      >
        {status}
      </span>
    );
  };

  // --- 7. RENDERING LOGIC (CONDITIONAL ROUTING) ---

  // If the user is NOT logged in, show the login/register card
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl p-8 shadow-sm space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white font-black text-xl mx-auto shadow-md shadow-indigo-100">
              S
            </div>
            <h2 className="text-2xl font-black text-slate-800 tracking-tight">
              {isRegistering ? "Create your Account" : "Sign in to SamStore"}
            </h2>
            <p className="text-sm text-slate-500">
              {isRegistering
                ? "Join our secure microservices demo"
                : "Enter credentials to access catalog"}
            </p>
          </div>

          {authError && (
            <div className="p-3 bg-rose-50 border border-rose-100 text-rose-700 text-sm rounded-xl font-semibold">
              {authError}
            </div>
          )}

          {authSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm rounded-xl font-semibold">
              {authSuccess}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="name@email.com"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                required
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-sm transition-all shadow-md shadow-indigo-100"
            >
              {loading
                ? "Processing..."
                : isRegistering
                  ? "Register Account"
                  : "Sign In"}
            </button>
          </form>

          <div className="text-center pt-2">
            <button
              onClick={() => {
                setIsRegistering(!isRegistering);
                setAuthError("");
                setAuthSuccess("");
              }}
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              {isRegistering
                ? "Already have an account? Sign In"
                : "Don't have an account? Register Now"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If the user IS logged in, render the main storefront dashboard
  return (
    <div className="min-h-screen bg-slate-50">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-xl shadow-lg border text-sm font-semibold ${
            toast.type === "error"
              ? "bg-rose-50 border-rose-200 text-rose-800"
              : toast.type === "success"
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : "bg-slate-50 border-slate-200 text-slate-800"
          }`}
          role="status"
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-md shadow-indigo-100">
              S
            </div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">
              SamStore
            </h1>
          </div>

          {/* User Status and Logout */}
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-slate-400">
                Authenticated as
              </p>
              <p className="text-sm font-bold text-slate-700">
                {currentUserEmail}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Product Grid */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-slate-800 tracking-tight">
              Available Products
            </h2>
            {(productsLoading || productsError) && (
              <button
                type="button"
                onClick={fetchProducts}
                disabled={productsLoading}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:opacity-60 text-slate-700 text-xs font-bold rounded-lg transition-all"
              >
                {productsLoading ? "Loading..." : "Retry catalog"}
              </button>
            )}
          </div>

          {coldStartNotice && productsLoading && (
            <div className="p-4 bg-amber-50 border border-amber-100 text-amber-900 text-sm rounded-xl">
              Waking free-tier Product Service on Render — first requests can
              take up to a minute after idle. Catalog will appear when it
              responds.
            </div>
          )}

          {productsError && !productsLoading && (
            <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 text-sm rounded-xl font-semibold">
              {productsError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {productsLoading && products.length === 0
              ? [1, 2, 3, 4].map((n) => (
                  <div
                    key={`skeleton-${n}`}
                    className="bg-white border border-slate-200 rounded-2xl overflow-hidden animate-pulse"
                  >
                    <div className="aspect-[4/3] bg-slate-200" />
                    <div className="p-5 space-y-3">
                      <div className="h-3 w-20 bg-slate-200 rounded" />
                      <div className="h-5 w-3/4 bg-slate-200 rounded" />
                      <div className="h-3 w-full bg-slate-100 rounded" />
                      <div className="h-3 w-2/3 bg-slate-100 rounded" />
                      <div className="pt-4 flex justify-between">
                        <div className="h-6 w-16 bg-slate-200 rounded" />
                        <div className="h-9 w-28 bg-slate-200 rounded-xl" />
                      </div>
                    </div>
                  </div>
                ))
              : products.map((product) => (
                  <div
                    key={product.id}
                    className="bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-lg transition-all duration-300 flex flex-col overflow-hidden group"
                  >
                    <div className="aspect-[4/3] bg-slate-100 overflow-hidden">
                      {product.image_url ? (
                        <img
                          src={product.image_url}
                          alt={product.name}
                          loading="lazy"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-4xl font-black text-slate-300">
                          {product.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                    </div>
                    <div className="p-5 flex flex-col flex-1 justify-between">
                      <div>
                        <div className="flex justify-between items-start mb-3">
                          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg">
                            ID: {product.id}
                          </span>
                          <span
                            className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${product.stock > 0 ? "bg-indigo-50 text-indigo-700" : "bg-red-50 text-red-700"}`}
                          >
                            {product.stock > 0
                              ? `${product.stock} In Stock`
                              : "Out of Stock"}
                          </span>
                        </div>
                        <h3 className="font-bold text-slate-800 text-lg mb-1 group-hover:text-indigo-600 transition-colors">
                          {product.name}
                        </h3>
                        <p className="text-slate-500 text-sm mb-4 leading-relaxed">
                          {product.description}
                        </p>
                      </div>
                      <div className="flex justify-between items-center pt-4 border-t border-slate-100">
                        <span className="text-xl font-black text-slate-900">
                          ${product.price}
                        </span>
                        <button
                          onClick={() => addToCart(product)}
                          disabled={product.stock <= 0}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white text-sm font-semibold rounded-xl transition-all shadow-md shadow-indigo-100"
                        >
                          Add to Cart
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
          </div>

          {!productsLoading && !productsError && products.length === 0 && (
            <p className="text-sm text-slate-400">
              No products returned yet. Use Retry catalog if the service just
              woke up.
            </p>
          )}
        </div>

        {/* Right Column: Checkout & Cart */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-800 mb-4 tracking-tight">
              Shopping Cart
            </h2>

            {cart.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <p className="text-sm">Your cart is empty.</p>
                <p className="text-xs mt-1">
                  Select products from the catalog to get started.
                </p>
              </div>
            ) : (
              <form onSubmit={handleCheckout} className="space-y-6">
                <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                  {cart.map((item) => (
                    <div
                      key={item.id}
                      className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {item.image_url && (
                          <img
                            src={item.image_url}
                            alt=""
                            className="w-10 h-10 rounded-lg object-cover border border-slate-200 shrink-0"
                          />
                        )}
                        <div className="min-w-0">
                          <h4 className="font-semibold text-slate-800 text-sm truncate">
                            {item.name}
                          </h4>
                          <span className="text-xs text-slate-500">
                            ${item.price} × {item.quantity}
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFromCart(item.id)}
                        className="text-xs font-semibold text-rose-500 hover:text-rose-700 px-2.5 py-1 hover:bg-rose-50 rounded-lg transition-all"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t border-slate-100 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold text-slate-500">
                      Order Total
                    </span>
                    <span className="text-2xl font-black text-slate-900">
                      ${calculateTotal()}
                    </span>
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white font-bold rounded-xl text-sm transition-all shadow-md shadow-indigo-100"
                  >
                    {loading
                      ? "Processing Secure Payment..."
                      : "Proceed to Secure Payment"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </main>

      {/* My Orders + Live Order Status Tracker */}
      <footer className="bg-white border-t border-slate-200 mt-12 py-12">
        <div className="max-w-7xl mx-auto px-6 space-y-10">
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-slate-800">My Orders</h3>
                <p className="text-sm text-slate-500">
                  JWT-scoped history for {currentUserEmail}. Refresh after
                  payment to see PENDING → PAID.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchMyOrders}
                disabled={myOrdersLoading}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 disabled:opacity-60 text-slate-700 text-xs font-bold rounded-xl transition-all"
              >
                {myOrdersLoading ? "Refreshing..." : "Refresh Orders"}
              </button>
            </div>

            {myOrdersError && (
              <p className="text-sm text-rose-500 font-semibold">
                {myOrdersError}
              </p>
            )}

            {myOrdersLoading && myOrders.length === 0 ? (
              <p className="text-sm text-slate-400">Loading your orders...</p>
            ) : myOrders.length === 0 ? (
              <p className="text-sm text-slate-400">
                No orders yet. Complete a checkout to see history here.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {myOrders.map((order) => (
                  <div
                    key={order.id}
                    className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3"
                  >
                    <div className="flex justify-between items-center gap-3">
                      <span className="text-sm font-bold text-slate-800">
                        Order #{order.id}
                      </span>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                      <div>
                        Total:{" "}
                        <span className="font-semibold text-slate-700">
                          ${order.total_amount}
                        </span>
                      </div>
                      <div>
                        Items:{" "}
                        <span className="font-semibold text-slate-700">
                          {order.items?.length || 0}
                        </span>
                      </div>
                      <div className="col-span-2">
                        Ref:{" "}
                        <span className="font-mono text-slate-600">
                          {order.tx_ref}
                        </span>
                      </div>
                      {order.created_at && (
                        <div className="col-span-2">
                          Placed:{" "}
                          <span className="font-semibold text-slate-700">
                            {new Date(order.created_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-slate-800">
                Verify Eventual Consistency
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                When you click "Checkout", our Order Service saves your order as{" "}
                <span className="font-semibold text-amber-600">PENDING</span>{" "}
                and opens your payment link in a new tab. Once you click
                "Success" on the mock payment page, our webhook triggers
                RabbitMQ to reduce stock. Use this tool to track the transaction
                state transition in real-time.
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-4">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider">
                Live Order Status Tracker
              </h4>
              <form onSubmit={handleQueryOrder} className="flex gap-2">
                <input
                  type="number"
                  placeholder="Enter Order ID (e.g. 4)"
                  value={queryOrderId}
                  onChange={(e) => setQueryOrderId(e.target.value)}
                  className="flex-1 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-xl transition-all"
                >
                  Track Order
                </button>
              </form>

              {queryError && (
                <p className="text-sm text-rose-500 font-semibold">
                  {queryError}
                </p>
              )}

              {queriedOrder && (
                <div className="bg-white border border-slate-100 rounded-xl p-4 space-y-3 shadow-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold text-slate-800">
                      Order ID: {queriedOrder.id}
                    </span>
                    {getStatusBadge(queriedOrder.status)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                    <div>
                      User ID:{" "}
                      <span className="font-semibold text-slate-700">
                        {queriedOrder.user_id}
                      </span>
                    </div>
                    <div>
                      Total Amount:{" "}
                      <span className="font-semibold text-slate-700">
                        ${queriedOrder.total_amount}
                      </span>
                    </div>
                    <div className="col-span-2">
                      Ref:{" "}
                      <span className="font-mono text-slate-600">
                        {queriedOrder.tx_ref}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
