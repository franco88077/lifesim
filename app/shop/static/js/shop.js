/* Storefront filtering and quick cart logic. */
document.addEventListener("DOMContentLoaded", () => {
  const filterButtons = document.querySelectorAll(".filter-button");
  const items = document.querySelectorAll(".shop-item");
  const cartList = document.getElementById("cart-list");
  const cartTotal = document.getElementById("cart-total");
  const cart = [];

  const updateFilters = (filter) => {
    items.forEach((item) => {
      const matches = filter === "all" || item.dataset.type === filter;
      item.style.display = matches ? "grid" : "none";
    });
  };

  const renderCart = () => {
    if (!cart.length) {
      cartList.innerHTML = '<li class="empty">No items reserved yet.</li>';
      cartTotal.textContent = "$0";
      return;
    }

    let sum = 0;
    cartList.innerHTML = "";
    cart.forEach((item) => {
      sum += item.cost;
      const li = document.createElement("li");
      li.innerHTML = `<span>${item.name}</span><span>$${item.cost.toFixed(2)}</span>`;
      cartList.append(li);
    });
    cartTotal.textContent = `$${sum.toFixed(2)}`;
  };

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      filterButtons.forEach((btn) => {
        btn.classList.toggle("active", btn === button);
        btn.setAttribute("aria-pressed", btn === button ? "true" : "false");
      });
      updateFilters(button.dataset.filter);
    });
  });

  items.forEach((item) => {
    const button = item.querySelector(".add-to-cart");
    button.addEventListener("click", () => {
      cart.push({
        name: item.querySelector("h3").textContent,
        cost: Number(item.dataset.cost || 0),
      });
      renderCart();
    });
  });

  renderCart();
});
