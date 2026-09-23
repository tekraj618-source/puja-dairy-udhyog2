
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("nav a").forEach(a => a.addEventListener("click", () => document.body.classList.remove("nav-open")));

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
        observer.unobserve(entry.target);
      }
    });
  }, {threshold:.08});

  document.querySelectorAll(".product-card,.rate-card,.steps>div,.values>div,.message-card,.stats>div").forEach((el,i) => {
    el.style.opacity = "0";
    el.style.transform = "translateY(18px)";
    el.style.transition = `opacity .55s ease ${Math.min(i*35,280)}ms, transform .55s ease ${Math.min(i*35,280)}ms`;
    observer.observe(el);
  });

  const form = document.getElementById("orderForm");
  if (!form) return;
  const qtys = [...document.querySelectorAll(".qty")];
  const summary = document.getElementById("summary");
  const grand = document.getElementById("grandTotal");
  const itemsInput = document.getElementById("items");
  const totalInput = document.getElementById("total");

  function update() {
    let total = 0, lines = [];
    qtys.forEach(q => {
      const n = Number(q.value || 0), price = Number(q.dataset.price || 0);
      if (n > 0) {
        const line = n * price;
        total += line;
        lines.push(`${q.dataset.name} x ${n} = Rs. ${line}`);
      }
    });
    summary.innerHTML = lines.length
      ? lines.map(x => `<div class="summary-line">${x}</div>`).join("")
      : '<p class="muted">Add products to see your summary.</p>';
    grand.textContent = `Rs. ${total.toFixed(0)}`;
    itemsInput.value = lines.join(" | ");
    totalInput.value = total;
  }
  qtys.forEach(q => q.addEventListener("input", update));
  form.addEventListener("submit", update);
});
